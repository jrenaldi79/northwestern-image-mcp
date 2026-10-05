import asyncio
import re
import socket
import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

from openrouter_image_mcp import auth, keystore
from openrouter_image_mcp.auth import (
    LoginManager,
    LoginState,
    build_auth_url,
    challenge_for,
    make_pkce,
)
from openrouter_image_mcp.client import OpenRouterClient
from openrouter_image_mcp.config import load_settings
from openrouter_image_mcp.errors import ProviderError

BASE = "https://openrouter.ai/api/v1"
NEW_KEY = "sk-or-test"
OLD_KEY = "sk-or-old-key"
WAIT_S = 5.0


class Browser:
    """Stub for webbrowser.open: records URLs, never opens anything."""

    def __init__(self):
        self.urls: list[str] = []

    def __call__(self, url: str) -> bool:
        self.urls.append(url)
        return True


@pytest.fixture
def router():
    r = respx.MockRouter(assert_all_called=False)
    r.post(f"{BASE}/auth/keys").respond(200, json={"key": NEW_KEY})
    r.get(f"{BASE}/key").respond(200, json={"data": {}})
    return r


@pytest.fixture
async def client(router):
    transport = httpx.MockTransport(router.async_handler)
    async with OpenRouterClient(timeout_s=10, transport=transport) as c:
        yield c


@pytest.fixture
def browser():
    return Browser()


@pytest.fixture
def make_manager(client, browser, memory_keyring):
    managers: list[LoginManager] = []

    def make(timeout_s: float = 30, workspace_id: str = "21082e84-ae02-4639-ad40-c7251b98ab10") -> LoginManager:
        settings = load_settings({"OPENROUTER_IMAGE_WORKSPACE_ID": workspace_id})
        m = LoginManager(client, settings, open_browser=browser, timeout_s=timeout_s)
        managers.append(m)
        return m

    yield make
    for m in managers:
        m.cancel()


def params(url: str) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


def callback_base(url: str) -> str:
    return params(url)["callback_url"]


async def get(url: str, **query) -> httpx.Response:
    async with httpx.AsyncClient(timeout=WAIT_S) as http:
        return await http.get(url, params=query)


async def wait_for(manager: LoginManager) -> LoginState:
    return await asyncio.wait_for(manager.wait(), WAIT_S)


def port_closed(port: int) -> bool:
    """True when nothing accepts connections on 127.0.0.1:port.

    Probes by connecting rather than binding: a refused connection means no
    listener. Binding is unreliable on Linux after a real round trip (lingering
    TIME_WAIT sockets), whereas TIME_WAIT sockets never accept connections.
    The listener may close asynchronously, so retry for up to ~2 s before
    deciding it is still open. A live listener gets a minimal GET /probe (404,
    keeps listening) so the probe never stalls its request loop. Synchronous
    (blocking sleeps) by design.
    """
    deadline = time.monotonic() + 2.0
    while True:
        try:
            probe = socket.create_connection(("127.0.0.1", port), timeout=0.5)
        except OSError:  # refused (or unreachable): nothing is listening
            return True
        with probe:
            # A bare connect would occupy the single-threaded server until its
            # socket timeout; a complete request gets a 404 and it keeps listening.
            try:
                probe.sendall(b"GET /probe HTTP/1.0\r\n\r\n")
                probe.recv(1024)
            except OSError:
                pass
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)


# ------------------------------------------------------------------- PKCE / URL


def test_rfc7636_vector():
    # RFC 7636 Appendix B. (The plan brief had a garbled verifier string.)
    assert (
        challenge_for("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk")
        == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    )


def test_make_pkce_lengths():
    verifier, challenge = make_pkce()
    assert 43 <= len(verifier) <= 128
    assert re.fullmatch(r"[A-Za-z0-9\-._~]+", verifier)
    assert challenge == challenge_for(verifier)
    assert make_pkce()[0] != verifier


def test_auth_url_params():
    url = build_auth_url(5123, "chal", "st8", "", "openrouter-image-mcp (HOST)")
    assert url.startswith("https://openrouter.ai/auth?")
    p = params(url)
    assert p["callback_url"] == "http://127.0.0.1:5123/callback"
    assert p["code_challenge"] == "chal"
    assert p["code_challenge_method"] == "S256"
    assert p["state"] == "st8"
    assert p["key_label"] == "openrouter-image-mcp (HOST)"
    assert "required_workspace_id" not in p
    assert "+" not in url  # spaces encoded as %20, not form-style '+'

    p = params(build_auth_url(5123, "chal", "st8", "ws-123", "label"))
    assert p["required_workspace_id"] == "ws-123"


# ------------------------------------------------------------------ login flow


async def test_status_idle_when_no_key(make_manager):
    m = make_manager()
    s = m.status()
    assert s == {
        "state": "idle",
        "message": "Not signed in to OpenRouter. Call `auth_login` to sign in.",
        "url": None,
    }
    assert await wait_for(m) == LoginState.IDLE


async def test_full_flow_success(make_manager, browser, router):
    m = make_manager()
    result = await m.start()

    assert result["state"] == "pending"
    assert browser.urls == [result["url"]]
    assert result["message"] == (
        "Finish signing in to OpenRouter in your browser. "
        f"If it didn't open, visit: {result['url']}"
    )
    p = params(result["url"])
    assert p["key_label"] == f"Northwestern AI Images Class of 2027 ({socket.gethostname()})"
    assert re.fullmatch(r"http://127\.0\.0\.1:\d+/callback", p["callback_url"])
    assert m.status()["state"] == "pending"
    assert m.status()["url"] == result["url"]

    resp = await get(p["callback_url"], code="abc", state=p["state"])
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Signed in to OpenRouter — you can close this tab and return to Claude." in resp.text

    assert await wait_for(m) == LoginState.SIGNED_IN
    assert keystore.get_key() == NEW_KEY
    assert m.status() == {"state": "signed_in", "message": "Signed in to OpenRouter.", "url": None}

    sent = router.routes[0].calls.last.request
    body = httpx.Response(200, content=sent.content).json()
    assert body["code"] == "abc"
    assert challenge_for(body["code_verifier"]) == p["code_challenge"]
    assert router.routes[1].calls.last.request.headers["Authorization"] == f"Bearer {NEW_KEY}"


async def test_listener_closed_after_success(make_manager):
    m = make_manager()
    result = await m.start()
    url = callback_base(result["url"])
    port = urlparse(url).port
    assert not port_closed(port)
    await get(url, code="abc", state=params(result["url"])["state"])
    assert await wait_for(m) == LoginState.SIGNED_IN
    assert port_closed(port)


async def test_state_mismatch_rejected(make_manager):
    m = make_manager()
    result = await m.start()
    url = callback_base(result["url"])

    assert (await get(url, code="abc", state="wrong")).status_code == 400
    assert (await get(url, code="abc")).status_code == 400
    assert m.status()["state"] == "pending"

    # Still listening: the genuine callback succeeds afterwards.
    resp = await get(url, code="abc", state=params(result["url"])["state"])
    assert resp.status_code == 200
    assert await wait_for(m) == LoginState.SIGNED_IN


async def test_other_paths_404_and_keep_listening(make_manager):
    m = make_manager()
    result = await m.start()
    url = callback_base(result["url"])
    favicon = url.replace("/callback", "/favicon.ico")

    assert (await get(favicon)).status_code == 404
    assert m.status()["state"] == "pending"
    resp = await get(url, code="abc", state=params(result["url"])["state"])
    assert resp.status_code == 200
    assert await wait_for(m) == LoginState.SIGNED_IN


async def test_error_callback_sets_failed(make_manager, router):
    m = make_manager()
    result = await m.start()
    url = callback_base(result["url"])
    port = urlparse(url).port

    resp = await get(url, error="access_denied", state=params(result["url"])["state"])
    assert resp.status_code == 200
    assert "cancelled" in resp.text

    assert await wait_for(m) == LoginState.FAILED
    assert m.status()["message"] == (
        "Sign-in failed: authorization was denied in the browser. "
        "Call `auth_login` to try again."
    )
    assert not router.routes[0].called
    assert keystore.get_key() is None
    assert port_closed(port)


async def test_timeout_expires(make_manager):
    m = make_manager(timeout_s=0.2)
    result = await m.start()
    port = urlparse(callback_base(result["url"])).port

    assert await wait_for(m) == LoginState.EXPIRED
    s = m.status()
    assert s["state"] == "expired"
    assert s["message"] == (
        "Sign-in timed out after 5 minutes with no response from the browser. "
        "If OpenRouter showed an error about the workspace, ask your admin for an "
        "invite to the organization. Call `auth_login` to try again."
    )
    assert "invite" in s["message"]
    assert port_closed(port)


async def test_already_signed_in_noop(make_manager, browser):
    keystore.set_key(OLD_KEY)
    m = make_manager()
    assert m.status()["state"] == "signed_in"

    result = await m.start()
    assert "already signed in" in result["message"].lower()
    assert result == {
        "state": "signed_in",
        "url": None,
        "message": "Already signed in to OpenRouter. "
        "Use switch_account=true to sign in with a different account.",
    }
    assert browser.urls == []


async def test_switch_keeps_old_key_until_success(make_manager, browser):
    keystore.set_key(OLD_KEY)
    m = make_manager()
    result = await m.start(switch_account=True)

    assert result["state"] == "pending"
    assert len(browser.urls) == 1
    assert keystore.get_key() == OLD_KEY

    await get(callback_base(result["url"]), code="abc", state=params(result["url"])["state"])
    assert await wait_for(m) == LoginState.SIGNED_IN
    assert keystore.get_key() == NEW_KEY


async def test_second_start_while_pending_returns_same_url(make_manager, browser, monkeypatch):
    created = []
    original = auth._CallbackServer

    class Counting(original):
        def __init__(self, *args, **kwargs):
            created.append(self)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(auth, "_CallbackServer", Counting)

    m = make_manager()
    first = await m.start()
    second = await m.start()
    third = await m.start(switch_account=True)

    assert first["url"] == second["url"] == third["url"]
    assert second["state"] == "pending"
    assert len(browser.urls) == 1
    assert len(created) == 1


async def test_restart_after_terminal_state(make_manager, browser):
    m = make_manager(timeout_s=0.1)
    first = await m.start()
    assert await wait_for(m) == LoginState.EXPIRED

    second = await m.start()
    assert second["state"] == "pending"
    assert second["url"] != first["url"]
    assert len(browser.urls) == 2


async def test_exchange_failure_sets_failed(make_manager, router):
    router.routes[0].respond(401, json={"error": {"message": "bad code"}})
    m = make_manager()
    result = await m.start()
    port = urlparse(callback_base(result["url"])).port

    resp = await get(callback_base(result["url"]), code="abc", state=params(result["url"])["state"])
    assert resp.status_code == 200

    assert await wait_for(m) == LoginState.FAILED
    message = m.status()["message"]
    assert message.startswith("Sign-in failed: ")
    assert message.endswith(". Call `auth_login` to try again.")
    assert message.count("auth_login") == 1
    assert keystore.get_key() is None
    assert port_closed(port)


async def test_rejected_new_key_sets_failed(make_manager, router):
    router.routes[1].respond(401, json={"error": {"message": "nope"}})
    m = make_manager()
    result = await m.start()
    await get(callback_base(result["url"]), code="abc", state=params(result["url"])["state"])

    assert await wait_for(m) == LoginState.FAILED
    assert m.status()["message"] == (
        "Sign-in failed: the new key was rejected. Call `auth_login` to try again."
    )


async def test_key_info_other_error_still_signed_in(make_manager, router):
    router.routes[1].respond(400, json={"error": {"message": "odd"}})
    m = make_manager()
    result = await m.start()
    await get(callback_base(result["url"]), code="abc", state=params(result["url"])["state"])

    assert await wait_for(m) == LoginState.SIGNED_IN
    assert keystore.get_key() == NEW_KEY


FIXED_EXCHANGE_FAILURE = (
    "Sign-in failed: OpenRouter couldn't complete the sign-in; try again shortly. "
    "Call `auth_login` to try again."
)


async def test_exchange_error_uses_fixed_reason(make_manager, router):
    router.routes[0].respond(400, json={"error": {"message": "leaked sk-or-v1-secret"}})
    m = make_manager()
    result = await m.start()
    await get(callback_base(result["url"]), code="abc", state=params(result["url"])["state"])

    assert await wait_for(m) == LoginState.FAILED
    assert m.status()["message"] == FIXED_EXCHANGE_FAILURE
    assert "sk-or-v1-secret" not in m.status()["message"]


async def test_exchange_server_error_hides_client_text(make_manager, client, monkeypatch):
    async def boom(code, verifier):
        raise ProviderError("OpenRouter/provider error (HTTP 502): x. The generation failed")

    monkeypatch.setattr(client, "exchange_code", boom)
    m = make_manager()
    result = await m.start()
    await get(callback_base(result["url"]), code="abc", state=params(result["url"])["state"])

    assert await wait_for(m) == LoginState.FAILED
    assert m.status()["message"] == FIXED_EXCHANGE_FAILURE
    assert "generation" not in m.status()["message"]


async def test_stalled_exchange_fails(make_manager, client, monkeypatch):
    monkeypatch.setattr(auth, "_FINISH_TIMEOUT_S", 0.2)

    async def stall(code, verifier):
        await asyncio.sleep(30)

    monkeypatch.setattr(client, "exchange_code", stall)
    m = make_manager()
    result = await m.start()
    port = urlparse(callback_base(result["url"])).port
    await get(callback_base(result["url"]), code="abc", state=params(result["url"])["state"])

    assert await wait_for(m) == LoginState.FAILED
    assert m.status()["message"] == (
        "Sign-in failed: OpenRouter didn't respond while finishing sign-in. "
        "Call `auth_login` to try again."
    )
    assert keystore.get_key() is None
    assert port_closed(port)


async def test_stalled_verification_still_signed_in(make_manager, client, monkeypatch):
    monkeypatch.setattr(auth, "_FINISH_TIMEOUT_S", 0.2)

    async def stall():
        await asyncio.sleep(30)

    monkeypatch.setattr(client, "key_info", stall)
    m = make_manager()
    result = await m.start()
    await get(callback_base(result["url"]), code="abc", state=params(result["url"])["state"])

    # The key is already stored, so a hung check doesn't undo the sign-in.
    assert await wait_for(m) == LoginState.SIGNED_IN
    assert keystore.get_key() == NEW_KEY


async def test_already_signed_in_clears_stale_failure(make_manager, browser):
    keystore.set_key(OLD_KEY)
    m = make_manager(timeout_s=0.1)
    await m.start(switch_account=True)
    assert await wait_for(m) == LoginState.EXPIRED
    assert m.status()["state"] == "expired"

    result = await m.start()
    assert result["message"].startswith("Already signed in")
    assert m.status() == {"state": "signed_in", "message": "Signed in to OpenRouter.", "url": None}
    assert keystore.get_key() == OLD_KEY
    assert len(browser.urls) == 1


async def test_browser_failure_still_pending(client, memory_keyring):
    def broken(url):
        raise RuntimeError("no browser")

    m = LoginManager(client, load_settings({"OPENROUTER_IMAGE_COHORT": "2027"}), open_browser=broken, timeout_s=30)
    try:
        result = await m.start()
        assert result["state"] == "pending"
        assert result["url"] in result["message"]
    finally:
        m.cancel()


async def test_reset_pending_then_late_callback_ignored(make_manager, router):
    m = make_manager()
    result = await m.start()
    url, state = callback_base(result["url"]), params(result["url"])["state"]

    m.reset()

    assert m.status()["state"] == "idle"
    try:
        await get(url, code="abc", state=state)
    except httpx.TransportError:
        pass  # listener already closed
    await asyncio.sleep(0.2)
    assert not router.routes[0].called
    assert keystore.get_key() is None
    assert m.status()["state"] == "idle"


async def test_reset_clears_failed_state(make_manager):
    m = make_manager(timeout_s=0.05)
    await m.start()
    assert await wait_for(m) == LoginState.EXPIRED
    m.reset()
    assert m.status()["state"] == "idle"

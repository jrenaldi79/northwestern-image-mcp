import json
import shutil
import sys
import types
from pathlib import Path
from typing import ClassVar

import keyring
import keyring.backend
import keyring.errors
import pytest

from openrouter_image_mcp import auth, cli, keystore
from openrouter_image_mcp.auth import LoginState
from openrouter_image_mcp.errors import OpenRouterError

REF_URL = "git+https://github.com/skelly-77/openrouter-image-mcp@v0.2.0"
HOME = Path(r"C:\Users\user")


def test_default_is_serve(monkeypatch):
    calls = []
    fake = types.ModuleType("openrouter_image_mcp.server")
    fake.run = lambda: calls.append("run")
    monkeypatch.setitem(sys.modules, "openrouter_image_mcp.server", fake)
    monkeypatch.setattr(cli, "configure_logging", lambda: calls.append("log"))
    assert cli.main([]) == 0
    assert calls == ["log", "run"]


def test_desktop_config_shape():
    out = json.loads(cli.render_config("desktop", r"C:\u\uvx.exe", HOME))
    entry = out["mcpServers"]["openrouter-image"]
    assert entry["command"] == r"C:\u\uvx.exe"
    assert entry["args"] == ["--from", REF_URL, "openrouter-image-mcp"]
    assert entry["env"] == {
        "UV_PYTHON_INSTALL_DIR": r"C:\Users\user\.uv\python",
        "UV_CACHE_DIR": r"C:\Users\user\.uv\cache",
        "UV_TOOL_DIR": r"C:\Users\user\.uv\tools",
    }


def test_desktop_config_honors_ref():
    out = json.loads(cli.render_config("desktop", "uvx", HOME, ref="v9.9.9"))
    args = out["mcpServers"]["openrouter-image"]["args"]
    assert args[1].endswith("@v9.9.9")


def test_code_config_is_mcp_json():
    out = json.loads(cli.render_config("code", r"C:\u\uvx.exe", HOME))
    entry = out["mcpServers"]["openrouter-image"]
    assert entry["command"] == "uvx"
    assert entry["args"] == ["--from", REF_URL, "openrouter-image-mcp"]
    assert "env" not in entry


def test_copilot_config_is_the_standard_entry():
    out = cli.render_config("copilot", "uvx", HOME)
    assert json.loads(out) == json.loads(cli.render_config("code", "uvx", HOME))


def test_print_config_copilot_note_on_stderr(monkeypatch, capsys):
    monkeypatch.setattr(cli, "find_uvx", lambda: None)
    assert cli.main(["print-config", "--client", "copilot"]) == 0
    captured = capsys.readouterr()
    entry = json.loads(captured.out)["mcpServers"]["openrouter-image"]  # stdout is pure JSON
    assert entry["command"] == "uvx"
    assert "Unverified: Copilot Code's MCP config format has not been confirmed" in captured.err


def test_find_uvx_prefers_path(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: r"C:\bin\uvx.exe")
    assert cli.find_uvx() == r"C:\bin\uvx.exe"


def test_find_uvx_falls_back_to_winget_glob(monkeypatch, tmp_path):
    exe = tmp_path / "Microsoft" / "WinGet" / "Packages" / "astral-sh.uv_abc" / "uvx.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert cli.find_uvx() == str(exe)


def test_find_uvx_none_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert cli.find_uvx() is None


def test_print_config_desktop(monkeypatch, capsys):
    monkeypatch.setattr(cli, "find_uvx", lambda: r"C:\u\uvx.exe")
    assert cli.main(["print-config", "--client", "desktop", "--ref", "v1.2.3"]) == 0
    entry = json.loads(capsys.readouterr().out)["mcpServers"]["openrouter-image"]
    assert entry["command"] == r"C:\u\uvx.exe"
    assert entry["args"][1].endswith("@v1.2.3")


def test_print_config_defaults_to_desktop(monkeypatch, capsys):
    monkeypatch.setattr(cli, "find_uvx", lambda: "uvx")
    assert cli.main(["print-config"]) == 0
    assert "env" in json.loads(capsys.readouterr().out)["mcpServers"]["openrouter-image"]


def test_print_config_desktop_without_uvx_errors(monkeypatch, capsys):
    monkeypatch.setattr(cli, "find_uvx", lambda: None)
    assert cli.main(["print-config", "--client", "desktop"]) == 1
    assert "winget install astral-sh.uv" in capsys.readouterr().err


def test_print_config_code_without_uvx_still_works(monkeypatch, capsys):
    monkeypatch.setattr(cli, "find_uvx", lambda: None)
    assert cli.main(["print-config", "--client", "code"]) == 0
    assert json.loads(capsys.readouterr().out)["mcpServers"]["openrouter-image"]["command"] == "uvx"


def test_status_signed_out_exit_code_1(memory_keyring, capsys):
    assert cli.main(["status"]) == 1
    assert "Not signed in. Run `openrouter-image-mcp login`." in capsys.readouterr().out


class FakeClient:
    info: ClassVar[dict] = {}
    error: Exception | None = None

    def __init__(self, timeout_s):
        pass

    async def key_info(self):
        if self.error:
            raise self.error
        return self.info

    async def aclose(self):
        pass


def test_status_signed_in_prints_usage(memory_keyring, monkeypatch, capsys):
    keystore.set_key("sk-or-test")
    FakeClient.error = None
    FakeClient.info = {"label": "my key", "usage_daily": 1.234, "usage_monthly": 5.6}
    monkeypatch.setattr(cli, "OpenRouterClient", FakeClient)
    assert cli.main(["status"]) == 0
    out = capsys.readouterr().out
    assert "my key" in out
    assert "Usage today: $1.23 / month: $5.60" in out
    assert "sk-or-test" not in out


def test_status_openrouter_error_exit_1(memory_keyring, monkeypatch, capsys):
    keystore.set_key("sk-or-test")
    FakeClient.error = OpenRouterError("boom happened")
    monkeypatch.setattr(cli, "OpenRouterClient", FakeClient)
    assert cli.main(["status"]) == 1
    assert "boom happened" in capsys.readouterr().out


def test_logout_deletes_key(memory_keyring, capsys):
    keystore.set_key("sk-or-test")
    assert cli.main(["logout"]) == 0
    assert keystore.get_key() is None
    out = capsys.readouterr().out
    assert "Signed out. To revoke the key on OpenRouter, delete it at https://openrouter.ai/settings/keys" in out


class FakeLogin:
    instances: ClassVar[list] = []
    final = LoginState.SIGNED_IN

    def __init__(self, client, settings, **kwargs):
        self.switch = None
        FakeLogin.instances.append(self)

    async def start(self, switch_account=False):
        self.switch = switch_account
        return {"state": "pending", "url": "https://openrouter.ai/auth?x=1", "message": "Open https://openrouter.ai/auth?x=1"}

    def status(self):
        return {"state": self.final.value, "message": "status message", "url": None}

    async def wait(self):
        return self.final


@pytest.fixture
def fake_login(monkeypatch):
    FakeLogin.instances = []
    FakeLogin.final = LoginState.SIGNED_IN
    monkeypatch.setattr(cli, "LoginManager", FakeLogin)
    monkeypatch.setattr(cli, "OpenRouterClient", FakeClient)


def test_login_success(fake_login, capsys):
    assert cli.main(["login"]) == 0
    assert "https://openrouter.ai/auth?x=1" in capsys.readouterr().out
    assert FakeLogin.instances[0].switch is False


def test_login_switch_and_failure(fake_login, capsys):
    FakeLogin.final = LoginState.FAILED
    assert cli.main(["login", "--switch"]) == 1
    assert FakeLogin.instances[0].switch is True
    assert "status message" in capsys.readouterr().out


class BrokenKeyring(keyring.backend.KeyringBackend):
    priority = 1

    def get_password(self, service, username):
        raise keyring.errors.KeyringError("locked")

    def set_password(self, service, username, password):
        raise keyring.errors.KeyringError("locked")

    def delete_password(self, service, username):
        raise keyring.errors.KeyringError("locked")


def test_keyring_error_is_explained(memory_keyring, capsys):
    keyring.set_keyring(BrokenKeyring())  # memory_keyring fixture restores afterwards
    assert cli.main(["status"]) == 1
    err = capsys.readouterr().err
    assert "Couldn't access the OS credential store: locked" in err


def test_listener_bind_error_is_explained(memory_keyring, monkeypatch, capsys):
    def no_bind(*args, **kwargs):
        raise OSError("[WinError 10013] access forbidden")

    monkeypatch.setattr(auth, "_CallbackServer", no_bind)
    monkeypatch.setattr(cli, "OpenRouterClient", FakeClient)
    assert cli.main(["login"]) == 1
    err = capsys.readouterr().err
    assert "Couldn't start the local sign-in listener" in err
    assert "10013" in err


def test_status_label_is_redacted(memory_keyring, monkeypatch, capsys):
    keystore.set_key("sk-or-test")
    FakeClient.error = None
    FakeClient.info = {"label": "sk-or-v1-abc...xyz", "usage_daily": 0, "usage_monthly": 0}
    monkeypatch.setattr(cli, "OpenRouterClient", FakeClient)
    assert cli.main(["status"]) == 0
    out = capsys.readouterr().out
    assert "sk-or-v1-abc" not in out
    assert "Signed in: sk-or-***" in out


def test_login_ctrl_c_cancels(fake_login, monkeypatch, capsys):
    cancelled = []

    async def interrupted(self):
        raise KeyboardInterrupt

    monkeypatch.setattr(FakeLogin, "wait", interrupted)
    monkeypatch.setattr(FakeLogin, "cancel", lambda self: cancelled.append(self), raising=False)
    assert cli.main(["login"]) == 130
    assert cancelled == FakeLogin.instances
    assert capsys.readouterr().out.rstrip().endswith("Sign-in cancelled.")

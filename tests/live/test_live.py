"""Opt-in live tests against the real OpenRouter API.

Deselected by default (`addopts = "-m 'not live'"`); run with `pytest -m live`
after `openrouter-image-mcp login`. They spend real (small) amounts of money,
use synthetic images only, and write only under pytest's tmp_path.
"""

from dataclasses import replace

import keyring
import keyring.backend
import pytest
from helpers import make_grid, save
from PIL import Image

from openrouter_image_mcp import keystore
from openrouter_image_mcp.catalog import Catalog, ModelCapabilities, price_key
from openrouter_image_mcp.client import OpenRouterClient
from openrouter_image_mcp.config import load_settings
from openrouter_image_mcp.service import ImageService

pytestmark = pytest.mark.live

_NOT_SIGNED_IN = "run `openrouter-image-mcp login` first"


_NON_OS_BACKENDS = frozenset(
    {"keyring.backends.fail", "keyring.backends.null", "keyring.backends.chainer"}
)


def _viable_priority(backend) -> float | None:
    """The backend's priority, or None if it is not viable (property raises or is <= 0)."""
    try:
        priority = backend.priority
    except Exception:  # noqa: BLE001 - a broken backend just means "not viable"
        return None
    return priority if priority > 0 else None


def _real_os_backend():
    """Highest-priority real OS keyring backend, or None if there is none."""
    best, best_priority = None, 0.0
    for backend in keyring.backend.get_all_keyring():
        module = type(backend).__module__
        if not module.startswith("keyring.backends.") or module in _NON_OS_BACKENDS:
            continue
        priority = _viable_priority(backend)
        if priority is not None and priority > best_priority:
            best, best_priority = backend, priority
    return best


@pytest.fixture(autouse=True)
def _real_os_keyring():
    """Use the real OS keyring for each live test, then restore the previous backend.

    Collection imports test modules that define KeyringBackend test doubles, and keyring
    auto-registers every subclass, so the default chainer would include a Plaintext one and
    keystore would (rightly) refuse it. Runs only for live tests, so a default run never
    touches the real keyring.
    """
    backend = _real_os_backend()
    if backend is None:
        pytest.skip(_NOT_SIGNED_IN)
    previous = keyring.get_keyring()
    keyring.set_keyring(backend)
    try:
        yield
    finally:
        keyring.set_keyring(previous)


@pytest.fixture(autouse=True)
def _require_key(_real_os_keyring):
    """Skip (rather than fail) when nobody is signed in. Checked per test, not at import,
    so a default run never touches the real keyring."""
    try:
        key = keystore.get_key()
    except keystore.InsecureKeyringError:
        pytest.skip(_NOT_SIGNED_IN)
    if key is None:
        pytest.skip(_NOT_SIGNED_IN)


@pytest.fixture
def settings(tmp_path):
    return replace(load_settings(), output_dir=tmp_path)


@pytest.fixture
async def client(settings):
    async with OpenRouterClient(timeout_s=settings.timeout_s) as c:
        yield c


@pytest.fixture
def catalog(client):
    return Catalog(client)


@pytest.fixture
def svc(client, catalog, settings):
    return ImageService(client, catalog, settings)


def _cheapest(models: list[ModelCapabilities], *, need_edit: bool = False) -> ModelCapabilities:
    """Cheapest priced images-route model, preferring ones that support quality="low"."""
    usable = [
        m
        for m in models
        if m.route != "chat"
        and price_key(m) != float("inf")
        and (not need_edit or (m.accepts_images and m.aspect_ratios is not None))
    ]
    if not usable:
        pytest.skip("no suitable priced image model in the live catalog")
    low = [m for m in usable if "low" in (m.qualities or [])]
    return min(low or usable, key=price_key)


def _quality(m: ModelCapabilities) -> str | None:
    return "low" if "low" in (m.qualities or []) else None


async def test_live_catalog(catalog):
    models = await catalog.all()
    assert any(m.route == "images" and m.accepts_images for m in models)


async def test_live_account(client):
    info = await client.key_info()
    assert "usage_daily" in info


async def test_live_generate_cheapest(svc, catalog):
    model = _cheapest(await catalog.all())
    result = await svc.generate(
        "a small red cube on a white table", model.id, n=1, quality=_quality(model)
    )
    assert len(result.images) == 1
    assert result.images[0].path.is_file()
    assert result.images[0].cost_usd is not None


async def test_live_edit_synthetic_wide(svc, catalog, tmp_path):
    model = _cheapest(await catalog.all(), need_edit=True)
    source = save(make_grid(1920, 828), tmp_path / "wide.jpg", "JPEG")
    result = await svc.edit(
        "make the top-left cell slightly brighter",
        model.id,
        [str(source)],
        n=1,
        quality=_quality(model),
    )
    assert len(result.images) == 1
    with Image.open(result.images[0].path) as out:
        assert out.size == (1920, 828)

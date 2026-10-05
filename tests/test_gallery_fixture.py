"""The Desktop acceptance fixture can be re-masked without any model call."""

import importlib.util
import json
from datetime import datetime
from pathlib import Path

from PIL import Image

from openrouter_image_mcp.config import COHORT_WORKSPACES, Settings
from openrouter_image_mcp.remask import remask


def test_gallery_fixture_is_free_and_keeps_existing_files(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "prepare_gallery_test.py"
    assert script.is_file(), "The free Desktop gallery test fixture is missing"
    spec = importlib.util.spec_from_file_location("prepare_gallery_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    first = module.prepare_fixture(tmp_path)
    before = Path(first["image"]).read_bytes()
    second = module.prepare_fixture(tmp_path)
    assert first != second
    assert Path(first["image"]).read_bytes() == before
    settings = Settings(COHORT_WORKSPACES["2027"], tmp_path, 2048, 30, 0.03)
    result = remask(first["image"], first["mask_path"], 0, None, settings, datetime.now().astimezone())
    assert json.loads(result.sidecar.read_text(encoding="utf-8"))["cost_usd"] == 0
    with Image.open(result.path) as image:
        assert image.size == (640, 360)
        assert image.getpixel((100, 100)) != image.getpixel((500, 100))

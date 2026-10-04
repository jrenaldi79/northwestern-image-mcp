import json
from datetime import UTC, datetime
from io import BytesIO

import pytest
from helpers import make_grid
from PIL import Image

from openrouter_image_mcp import outputs
from openrouter_image_mcp.outputs import (
    choose_dir,
    encode_image,
    model_short,
    output_path,
    prompt_slug,
    write_bytes_atomic,
    write_sidecar,
)

NOW = datetime(2026, 10, 3, 22, 15, 0, tzinfo=UTC)
STEM = "Sample_Render_v5"
MODEL = "openai/gpt-image-2.5-sunburst"
NAME = "Sample_Render_v5__gpt-image-2.5-sunburst_20261003-221500_1"


def test_name_format(tmp_path):
    p = output_path(tmp_path, STEM, MODEL, 1, ".png", NOW)
    assert p.parent == tmp_path
    assert p.name == NAME + ".png"
    assert not p.exists()


def test_collision_suffix(tmp_path):
    (tmp_path / (NAME + ".png")).write_bytes(b"x")
    p2 = output_path(tmp_path, STEM, MODEL, 1, ".png", NOW)
    assert p2.name == NAME + "-2.png"
    p2.write_bytes(b"x")
    assert output_path(tmp_path, STEM, MODEL, 1, ".png", NOW).name == NAME + "-3.png"


def test_model_short():
    assert model_short("openai/gpt-image-2.5-sunburst") == "gpt-image-2.5-sunburst"
    assert model_short("plain") == "plain"


def test_prompt_slug():
    assert (
        prompt_slug("A Red Panda, astronaut! floating in deep space today")
        == "a-red-panda-astronaut-floating-in"
    )


def test_prompt_slug_empty_and_truncated():
    assert prompt_slug("") == "image"
    assert prompt_slug("  !!! ??? ") == "image"
    slug = prompt_slug(" ".join(["abcdefghijkl"] * 6))
    assert len(slug) <= 60
    assert not slug.endswith("-")
    # Truncation lands just after a "-": the trailing dash is stripped again.
    assert prompt_slug("a" * 59 + " bbbb") == "a" * 59


def test_atomic_write_leaves_no_tmp(tmp_path):
    p = tmp_path / "out.png"
    write_bytes_atomic(p, b"hello")
    assert p.read_bytes() == b"hello"
    assert [f.name for f in tmp_path.iterdir()] == ["out.png"]


def test_atomic_write_overwrites(tmp_path):
    p = tmp_path / "out.png"
    write_bytes_atomic(p, b"one")
    write_bytes_atomic(p, b"two")
    assert p.read_bytes() == b"two"
    assert [f.name for f in tmp_path.iterdir()] == ["out.png"]


def test_sidecar_contents(tmp_path):
    img = tmp_path / "pic.png"
    img.write_bytes(b"x")
    meta = {"prompt": "café à Zürich — 東京", "model": MODEL, "schema_version": 99,
            "server_version": "bogus"}
    sc = write_sidecar(img, meta)
    assert sc == tmp_path / "pic.json"
    raw = sc.read_text(encoding="utf-8")
    assert "東京" in raw  # ensure_ascii=False
    assert raw.startswith("{\n  ")  # indent=2
    data = json.loads(raw)
    assert data["schema_version"] == 1
    assert data["server_version"] == "0.1.0"
    assert data["prompt"] == "café à Zürich — 東京"
    assert "sk-or-" not in raw
    assert "schema_version" in meta and meta["schema_version"] == 99  # input not mutated


def test_sidecar_next_to_dotted_name(tmp_path):
    img = tmp_path / (NAME + ".png")
    assert write_sidecar(img, {}).name == NAME + ".json"


def test_choose_dir_preferred_created(tmp_path):
    pref = tmp_path / "new" / "out"
    d, note = choose_dir(pref, tmp_path / "fb")
    assert d == pref and note is None and pref.is_dir()
    assert list(pref.iterdir()) == []  # probe file removed


def test_choose_dir_none_uses_fallback(tmp_path):
    fb = tmp_path / "fb"
    d, note = choose_dir(None, fb)
    assert d == fb and fb.is_dir()
    assert note is None


def test_choose_dir_fallback_when_unwritable(tmp_path, monkeypatch):
    pref = tmp_path / "pref"
    fb = tmp_path / "fb"

    def boom(directory):
        if directory == pref:
            raise PermissionError("denied")

    monkeypatch.setattr(outputs, "_probe_writable", boom)
    d, note = choose_dir(pref, fb)
    assert d == fb
    assert note and str(pref) in note


def test_encode_png_default():
    data, ext = encode_image(make_grid(32, 24), None)
    assert ext == ".png"
    assert Image.open(BytesIO(data)).format == "PNG"


def test_encode_jpeg_flattens_alpha_on_white():
    img = Image.new("RGBA", (8, 8), (255, 0, 0, 0))  # fully transparent
    data, ext = encode_image(img, "jpeg")
    assert ext == ".jpg"
    out = Image.open(BytesIO(data))
    assert out.format == "JPEG"
    r, g, b = out.convert("RGB").getpixel((4, 4))
    assert min(r, g, b) >= 250


def test_encode_webp():
    data, ext = encode_image(make_grid(32, 24), "webp")
    assert ext == ".webp"
    assert Image.open(BytesIO(data)).format == "WEBP"


def test_encode_unknown_format():
    with pytest.raises(ValueError):
        encode_image(make_grid(8, 8), "gif")


def test_spaces_commas_unicode_dir(tmp_path):
    d = tmp_path / "Example Firm, INC" / "01 Personal" / "Café renders"
    chosen, note = choose_dir(d, tmp_path / "fb")
    assert chosen == d and note is None
    p = output_path(chosen, "vue été", MODEL, 2, ".png", NOW)
    data, ext = encode_image(make_grid(16, 12), "png")
    assert ext == ".png"
    write_bytes_atomic(p, data)
    sc = write_sidecar(p, {"prompt": "été"})
    assert p.exists() and sc.exists()
    assert sorted(f.name for f in d.iterdir()) == sorted([p.name, sc.name])


def test_output_path_sanitizes_model_and_stem(tmp_path):
    p = output_path(tmp_path, 'a<b>c:d"e/f\\g|h?i*j\x01k', "x/y:free", 1, ".png", NOW)
    assert p.parent == tmp_path
    assert p.name == "a-b-c-d-e-f-g-h-i-j-k__y-free_20261003-221500_1.png"
    p.write_bytes(b"x")  # a valid filename on every platform
    assert p.exists()


def test_output_path_skips_name_whose_sidecar_exists(tmp_path):
    (tmp_path / (NAME + ".json")).write_text("{}", encoding="utf-8")
    assert output_path(tmp_path, STEM, MODEL, 1, ".png", NOW).name == NAME + "-2.png"
    (tmp_path / (NAME + "-2.png")).write_bytes(b"x")
    assert output_path(tmp_path, STEM, MODEL, 1, ".png", NOW).name == NAME + "-3.png"

"""remask: re-blend a masked edit's unblended layer through a new mask, locally."""

import hashlib
import json
import shutil
from datetime import UTC, datetime
from io import BytesIO

import pytest
from helpers import make_grid, save, unc_paths
from PIL import Image

from openrouter_image_mcp.config import Settings
from openrouter_image_mcp.imaging import InputError
from openrouter_image_mcp.remask import RemaskResult, remask

NOW = datetime(2026, 10, 4, 1, 21, 53, tzinfo=UTC)
TS = "20261004-012153"
W, H = 400, 300
MODEL = "openai/gpt-image-2.5-sunburst"
BLUE = (0, 0, 255)
SOURCE_STEM = "in__gpt-image-2.5-sunburst_20261003-221500_1"


@pytest.fixture
def settings(tmp_path):
    return Settings(
        workspace_id="21082e84-ae02-4639-ad40-c7251b98ab10",
        output_dir=tmp_path / "out",
        max_input_edge=2048,
        timeout_s=30,
        ratio_tolerance=0.03,
    )


def write_source(directory, *, masked=True, with_layer_key=True):
    """A masked edit_image result as the service leaves it: input, layer, result, sidecar."""
    original = save(make_grid(W, H), directory / "in.png", "PNG")
    result = directory / f"{SOURCE_STEM}.png"
    layer = directory / f"{SOURCE_STEM}.unmasked.png"
    Image.new("RGB", (W, H), BLUE).save(layer, format="PNG")
    make_grid(W, H).save(result, format="PNG")  # stand-in for the old blend
    meta = {
        "tool": "edit_image",
        "created_at": "2026-10-03T22:15:00+00:00",
        "model": MODEL,
        "provider": "openai",
        "prompt": "add a person on the bench",
        "cost_usd": 0.21,
        "inputs": [
            {
                "path": original.as_posix(),
                "sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
                "size": [W, H],
            }
        ],
        "mask": {"path": (directory / "old-mask.png").as_posix(), "feather_px": 2}
        if masked
        else None,
        "unmasked_path": layer.as_posix() if masked else None,
        "fit": None,
        "schema_version": 1,
        "server_version": "0.2.0",
    }
    if not with_layer_key:
        del meta["unmasked_path"]
    result.with_suffix(".json").write_text(json.dumps(meta), encoding="utf-8")
    return original, result, layer, meta


def left_half_mask(path):
    mask = Image.new("L", (W, H), 0)
    mask.paste(255, (0, 0, W // 2, H))  # left half: take the unblended layer
    return save(mask, path, "PNG")


@pytest.fixture
def source(tmp_path):
    return write_source(tmp_path / "proj")


def files(directory):
    return sorted(p.name for p in directory.iterdir())


# ------------------------------------------------------------------ success


def test_remask_reblends_through_the_new_mask(source, settings, tmp_path):
    _, result, _, _ = source
    mask = left_half_mask(tmp_path / "new-mask.png")

    out = remask(str(result), str(mask), 0, None, settings, NOW)

    assert isinstance(out, RemaskResult)
    assert out.path.parent == result.parent
    assert out.path.name == f"{SOURCE_STEM}__remask_{TS}_1.png"
    assert out.sidecar == out.path.with_suffix(".json")
    with Image.open(out.path) as opened:
        assert opened.format == "PNG"
        img = opened.convert("RGB")
    assert img.size == (W, H)
    inside, outside = (0, 0, W // 2, H), (W // 2, 0, W, H)
    assert img.crop(inside).tobytes() == Image.new("RGB", (W // 2, H), BLUE).tobytes()
    assert img.crop(outside).tobytes() == make_grid(W, H).crop(outside).tobytes()
    assert Image.open(BytesIO(out.preview_jpeg)).format == "JPEG"
    assert out.notes == []


def test_remask_sidecar_records_provenance(source, settings, tmp_path):
    _, result, layer, meta = source
    mask = left_half_mask(tmp_path / "new-mask.png")

    out = remask(str(result), str(mask), 0, None, settings, NOW)

    side = json.loads(out.sidecar.read_text(encoding="utf-8"))
    assert side["tool"] == "remask_image"
    assert side["created_at"] == NOW.isoformat()
    assert side["source_result"] == result.as_posix()
    assert side["unmasked_path"] == layer.as_posix()
    assert side["inputs"] == meta["inputs"]
    assert side["mask"] == {"path": mask.as_posix(), "feather_px": 0}
    assert side["cost_usd"] == 0
    assert side["model"] == MODEL
    assert side["prompt"] == "add a person on the bench"
    assert side["schema_version"] == 1 and "server_version" in side


def test_remask_default_feather_is_recorded(source, settings, tmp_path):
    _, result, _, _ = source
    mask = left_half_mask(tmp_path / "new-mask.png")

    out = remask(str(result), str(mask), None, None, settings, NOW)

    side = json.loads(out.sidecar.read_text(encoding="utf-8"))
    assert side["mask"]["feather_px"] == max(1, round(0.005 * min(W, H)))


def test_remask_output_dir(source, settings, tmp_path):
    _, result, _, _ = source
    mask = left_half_mask(tmp_path / "new-mask.png")
    elsewhere = tmp_path / "elsewhere" / "nested"

    out = remask(str(result), str(mask), 0, str(elsewhere), settings, NOW)

    assert out.path.parent == elsewhere
    assert out.path.is_file() and out.sidecar.is_file()


def test_remask_never_overwrites(source, settings, tmp_path):
    _, result, _, _ = source
    mask = left_half_mask(tmp_path / "new-mask.png")

    first = remask(str(result), str(mask), 0, None, settings, NOW)
    second = remask(str(result), str(mask), 0, None, settings, NOW)

    assert first.path != second.path
    assert second.path.name == f"{SOURCE_STEM}__remask_{TS}_1-2.png"


def test_remask_of_a_remask(source, settings, tmp_path):
    _, result, layer, _ = source
    mask = left_half_mask(tmp_path / "new-mask.png")
    first = remask(str(result), str(mask), 0, None, settings, NOW)

    whole = save(Image.new("L", (W, H), 255), tmp_path / "all.png", "PNG")
    second = remask(str(first.path), str(whole), 0, None, settings, NOW)

    img = Image.open(second.path).convert("RGB")
    assert img.tobytes() == Image.new("RGB", (W, H), BLUE).tobytes()
    side = json.loads(second.sidecar.read_text(encoding="utf-8"))
    assert side["source_result"] == first.path.as_posix()
    assert side["unmasked_path"] == layer.as_posix()


def test_remask_falls_back_when_dir_unwritable(source, settings, tmp_path, monkeypatch):
    from openrouter_image_mcp import outputs

    _, result, _, _ = source
    mask = left_half_mask(tmp_path / "new-mask.png")
    real = outputs._probe_writable

    def probe(directory):
        if directory == result.parent:
            raise PermissionError("denied")
        real(directory)

    monkeypatch.setattr(outputs, "_probe_writable", probe)

    out = remask(str(result), str(mask), 0, None, settings, NOW)

    assert out.path.parent == settings.output_dir
    assert len(out.notes) == 1 and str(result.parent) in out.notes[0]


def test_moved_folder_uses_the_layer_next_to_the_result(source, settings, tmp_path):
    """Result, layer and sidecar moved together; the original input stayed put."""
    _, result, layer, _ = source
    moved = tmp_path / "moved"
    moved.mkdir()
    for p in (result, layer, result.with_suffix(".json")):
        shutil.move(p, moved / p.name)
    new_result, new_layer = moved / result.name, moved / layer.name
    mask = left_half_mask(tmp_path / "new-mask.png")

    out = remask(str(new_result), str(mask), 0, None, settings, NOW)

    assert out.path.parent == moved
    img = Image.open(out.path).convert("RGB")
    inside = (0, 0, W // 2, H)
    assert img.crop(inside).tobytes() == Image.new("RGB", (W // 2, H), BLUE).tobytes()
    assert len(out.notes) == 1
    assert str(layer) in out.notes[0] and str(new_layer) in out.notes[0]
    side = json.loads(out.sidecar.read_text(encoding="utf-8"))
    assert side["unmasked_path"] == new_layer.as_posix()


def test_moved_folder_never_guesses_the_original(source, settings, tmp_path):
    """The whole folder moved, original included: the recorded input is missing, so fail."""
    original, result, _, _ = source
    moved = tmp_path / "moved"
    shutil.move(result.parent, moved)
    assert (moved / original.name).is_file()  # a same-named file sits next to the result
    mask = left_half_mask(tmp_path / "new-mask.png")
    with pytest.raises(InputError, match="original input image .* is missing"):
        remask(str(moved / result.name), str(mask), 0, None, settings, NOW)


# --------------------------------------------------- untrusted sidecar paths

UNC = unc_paths("x.unmasked.png")  # incl. mixed `\/` and `/\` and `\\?\UNC\` spellings


def rewrite_sidecar(result, **changes):
    sidecar = result.with_suffix(".json")
    meta = json.loads(sidecar.read_text(encoding="utf-8"))
    for key, value in changes.items():
        if key == "input_path":
            meta["inputs"][0]["path"] = value
        else:
            meta[key] = value
    sidecar.write_text(json.dumps(meta), encoding="utf-8")


@pytest.mark.parametrize("value", [*UNC, "proj/x.unmasked.png", 5])
def test_sidecar_layer_path_must_be_absolute_and_local(source, settings, tmp_path, no_network_probe, value):
    _, result, _, _ = source
    rewrite_sidecar(result, unmasked_path=value)
    mask = left_half_mask(tmp_path / "new-mask.png")
    with pytest.raises(InputError, match="The sidecar records an invalid unblended-layer path"):
        remask(str(result), str(mask), 0, None, settings, NOW)
    assert no_network_probe == []


def test_sidecar_layer_path_must_end_in_unmasked_png(source, settings, tmp_path):
    original, result, _, _ = source
    rewrite_sidecar(result, unmasked_path=original.as_posix())  # exists, but not a layer
    mask = left_half_mask(tmp_path / "new-mask.png")
    with pytest.raises(InputError, match=r"The sidecar records an invalid unblended-layer path.*\.unmasked\.png"):
        remask(str(result), str(mask), 0, None, settings, NOW)


@pytest.mark.parametrize("value", [*[u.replace(".unmasked", "") for u in UNC], "in.png", 7])
def test_sidecar_input_path_must_be_absolute_and_local(source, settings, tmp_path, no_network_probe, value):
    _, result, _, _ = source
    rewrite_sidecar(result, input_path=value)
    mask = left_half_mask(tmp_path / "new-mask.png")
    with pytest.raises(InputError, match="The sidecar records an invalid original-input path"):
        remask(str(result), str(mask), 0, None, settings, NOW)
    assert no_network_probe == []


@pytest.mark.parametrize("value", ["old-mask.png", True, ["x"]])
def test_sidecar_mask_must_be_an_object(source, settings, tmp_path, value):
    _, result, _, _ = source
    rewrite_sidecar(result, mask=value)
    mask = left_half_mask(tmp_path / "new-mask.png")
    with pytest.raises(InputError, match="The sidecar records an invalid mask entry"):
        remask(str(result), str(mask), 0, None, settings, NOW)


@pytest.mark.parametrize("unc", unc_paths("file.png"))
@pytest.mark.parametrize("which", ["result", "mask", "output_dir"])
def test_caller_network_paths_rejected(source, settings, tmp_path, no_network_probe, unc, which):
    _, result, _, _ = source
    mask = left_half_mask(tmp_path / "new-mask.png")
    args = {"result": str(result), "mask": str(mask), "output_dir": None}
    args[which] = unc
    with pytest.raises(InputError, match="Network .*paths aren't supported"):
        remask(args["result"], args["mask"], 0, args["output_dir"], settings, NOW)
    assert no_network_probe == []


# ------------------------------------------------------------------- errors


def test_source_without_mask_rejected(tmp_path, settings):
    _, result, _, _ = write_source(tmp_path / "proj", masked=False)
    mask = left_half_mask(tmp_path / "new-mask.png")
    with pytest.raises(
        InputError,
        match="This image wasn't made with a mask, so there is no unblended layer to re-mask.",
    ):
        remask(str(result), str(mask), 0, None, settings, NOW)


def test_source_from_before_unmasked_layers_rejected(tmp_path, settings):
    _, result, _, _ = write_source(tmp_path / "proj", with_layer_key=False)
    mask = left_half_mask(tmp_path / "new-mask.png")
    with pytest.raises(InputError, match="0.2.0"):
        remask(str(result), str(mask), 0, None, settings, NOW)


def test_missing_layer_rejected(source, settings, tmp_path):
    _, result, layer, _ = source
    layer.unlink()
    mask = left_half_mask(tmp_path / "new-mask.png")
    with pytest.raises(InputError, match="The unblended layer .* is missing") as info:
        remask(str(result), str(mask), 0, None, settings, NOW)
    assert layer.name in str(info.value)


def test_changed_original_rejected(source, settings, tmp_path):
    original, result, _, _ = source
    save(make_grid(W, H, cols=3), original, "PNG")  # same size, different pixels
    mask = left_half_mask(tmp_path / "new-mask.png")
    with pytest.raises(InputError, match="The original input image has changed since this result was made"):
        remask(str(result), str(mask), 0, None, settings, NOW)


def test_missing_original_rejected(source, settings, tmp_path):
    original, result, _, _ = source
    original.unlink()
    mask = left_half_mask(tmp_path / "new-mask.png")
    with pytest.raises(InputError, match="original input image .* is missing"):
        remask(str(result), str(mask), 0, None, settings, NOW)


def test_bad_mask_rejected_before_any_output(source, settings, tmp_path):
    _, result, _, _ = source
    bad = tmp_path / "bad-mask.png"
    bad.write_bytes(b"this is not an image")
    before = files(result.parent)
    with pytest.raises(InputError, match="Cannot read mask"):
        remask(str(result), str(bad), 0, None, settings, NOW)
    assert files(result.parent) == before


def test_relative_paths_rejected(source, settings, tmp_path):
    _, result, _, _ = source
    mask = left_half_mask(tmp_path / "new-mask.png")
    with pytest.raises(InputError, match="absolute"):
        remask("proj/" + result.name, str(mask), 0, None, settings, NOW)
    with pytest.raises(InputError, match="absolute"):
        remask(str(result), "new-mask.png", 0, None, settings, NOW)
    with pytest.raises(InputError, match="absolute"):
        remask(str(result), str(mask), 0, "relative/out", settings, NOW)


def test_missing_sidecar_rejected(source, settings, tmp_path):
    _, result, _, _ = source
    result.with_suffix(".json").unlink()
    mask = left_half_mask(tmp_path / "new-mask.png")
    with pytest.raises(InputError, match="sidecar"):
        remask(str(result), str(mask), 0, None, settings, NOW)


def test_unreadable_sidecar_rejected(source, settings, tmp_path):
    _, result, _, _ = source
    result.with_suffix(".json").write_text("{not json", encoding="utf-8")
    mask = left_half_mask(tmp_path / "new-mask.png")
    with pytest.raises(InputError, match="sidecar"):
        remask(str(result), str(mask), 0, None, settings, NOW)


def test_layer_size_mismatch_rejected(source, settings, tmp_path):
    _, result, layer, _ = source
    Image.new("RGB", (W // 2, H // 2), BLUE).save(layer, format="PNG")
    mask = left_half_mask(tmp_path / "new-mask.png")
    with pytest.raises(InputError, match="size"):
        remask(str(result), str(mask), 0, None, settings, NOW)

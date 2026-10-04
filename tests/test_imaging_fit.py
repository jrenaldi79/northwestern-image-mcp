import statistics

import pytest
from helpers import make_grid, save
from PIL import Image, ImageChops, ImageStat

from openrouter_image_mcp.imaging import (
    RESOLUTION_TIERS,
    FitPlan,
    InputError,
    apply_fit,
    composite_mask,
    pad_to_ratio,
    plan_fit,
)

SAMPLE_RATIOS = ["1:1", "3:2", "2:3", "4:3", "3:4", "16:9", "9:16", "21:9", "auto"]


def test_resolution_tiers():
    assert RESOLUTION_TIERS == {"512": 512, "768": 768, "1K": 1024, "1.5K": 1536, "2K": 2048, "4K": 4096}


def test_plan_picks_21_9_for_sample_render():
    plan = plan_fit((1920, 828), SAMPLE_RATIOS, None, 0.03)
    assert plan == FitPlan("crop_back", "21:9", None, (1920, 828), None)


def test_plan_pads_when_outside_tolerance():
    plan = plan_fit((3000, 1000), ["1:1", "16:9"], None, 0.03)
    assert plan.strategy == "pad"
    assert plan.aspect_ratio == "16:9"
    assert plan.content_box is not None


def test_plan_no_ratio_support():
    plan = plan_fit((1920, 828), None, None, 0.03)
    assert plan.strategy == "none_supported"
    assert plan.aspect_ratio is None


def test_plan_resolution_smallest_covering():
    assert plan_fit((1920, 828), None, ["1K", "2K", "4K"], 0.03).resolution == "2K"
    assert plan_fit((5000, 2000), None, ["1K", "2K"], 0.03).resolution == "2K"


def test_auto_ignored_in_choice():
    plan = plan_fit((1920, 828), ["auto"], None, 0.03)
    assert plan.strategy == "none_supported"
    assert plan.aspect_ratio is None


def test_pad_content_box_matches_plan():
    size, ratio = (3000, 1000), "16:9"
    plan = plan_fit(size, ["1:1", ratio], None, 0.03)
    padded, box = pad_to_ratio(make_grid(*size), ratio)
    assert padded.size == (3000, round(3000 * 9 / 16))
    assert box == plan.content_box
    assert box[0] == 0 and box[2] == 1


def test_crop_back_exact_size():
    plan = plan_fit((1920, 828), SAMPLE_RATIOS, None, 0.03)
    out, report = apply_fit(Image.new("RGB", (2016, 864), (10, 20, 30)), plan)
    assert out.size == (1920, 828)
    assert report.final_size == (1920, 828)
    assert report.raw_size == (2016, 864)
    assert report.crop_box == (6, 0, 1926, 828)
    assert report.upscaled is False
    assert report.padded is False
    assert report.requested_ratio == "21:9"


def test_crop_back_upscales_small_output():
    plan = plan_fit((1920, 828), SAMPLE_RATIOS, None, 0.03)
    out, report = apply_fit(Image.new("RGB", (1344, 576)), plan)
    assert out.size == (1920, 828)
    assert report.upscaled is True


def test_none_supported_uses_crop_back_path():
    plan = plan_fit((1920, 828), None, None, 0.03)
    out, report = apply_fit(Image.new("RGB", (2016, 864)), plan)
    assert out.size == (1920, 828)
    assert report.crop_box == (6, 0, 1926, 828)


def test_model_strategy_returns_output_unchanged():
    plan = FitPlan("model", None, None, (1920, 828), None)
    src = Image.new("RGB", (1000, 500))
    out, report = apply_fit(src, plan)
    assert out is src
    assert report.final_size == (1000, 500)
    assert report.crop_box is None
    assert report.upscaled is False


def test_pad_roundtrip_grid():
    original = make_grid(3000, 1000)
    plan = plan_fit((3000, 1000), ["1:1", "16:9"], None, 0.03)
    padded, _ = pad_to_ratio(original, "16:9")
    generated = padded.resize((1792, 1008), Image.Resampling.LANCZOS)
    out, report = apply_fit(generated, plan)
    assert out.size == (3000, 1000)
    assert report.padded is True
    diff = ImageChops.difference(out, original)
    assert statistics.fmean(ImageStat.Stat(diff).mean) < 8


def test_pad_uses_mirrored_blur_not_flat():
    original = make_grid(3000, 1000)
    padded, box = pad_to_ratio(original, "16:9")
    top = padded.crop((0, 0, padded.width, round(box[1] * padded.height) - 1))
    assert top.height > 0
    stddev = ImageStat.Stat(top).stddev
    assert max(stddev) > 1


def test_pad_wide_band_exceeding_image_height():
    # 1:1 on 3000x1000 needs 1000px bands each side: reflection must tile.
    padded, box = pad_to_ratio(make_grid(3000, 1000), "1:1")
    assert padded.size == (3000, 3000)
    assert box == (0, pytest.approx(1 / 3), 1, pytest.approx(2 / 3))


def test_pad_tall_image_pads_sides():
    padded, box = pad_to_ratio(make_grid(1000, 3000), "16:9")
    assert padded.size == (round(3000 * 16 / 9), 3000)
    assert box[1] == 0 and box[3] == 1


def test_pad_bad_ratio_rejected():
    with pytest.raises(ValueError):
        pad_to_ratio(make_grid(100, 100), "wide")
    with pytest.raises(ValueError):
        pad_to_ratio(make_grid(100, 100), "auto")


def _half_mask(tmp_path, w, h):
    mask = Image.new("L", (w, h), 255)
    mask.paste(0, (0, 0, w // 2, h))
    return save(mask, tmp_path / "mask.png", "PNG")


def test_mask_black_region_identical(tmp_path):
    w, h = 1920, 828
    original = make_grid(w, h)
    output = Image.new("RGB", (w, h), (1, 2, 3))
    mask_path = _half_mask(tmp_path, w, h)
    result, used = composite_mask(output, original, str(mask_path), 4)
    assert used == 4
    left = (0, 0, w // 2 - 12, h)
    right = (w // 2 + 12, 0, w, h)
    assert ImageChops.difference(result.crop(left), original.crop(left)).getbbox() is None
    assert ImageChops.difference(result.crop(right), output.crop(right)).getbbox() is None


def test_mask_default_feather(tmp_path):
    w, h = 1920, 828
    mask_path = _half_mask(tmp_path, w, h)
    _, used = composite_mask(Image.new("RGB", (w, h)), make_grid(w, h), str(mask_path), None)
    assert used == 4


def test_mask_default_feather_portrait_uses_short_edge(tmp_path):
    w, h = 828, 1920
    mask_path = _half_mask(tmp_path, w, h)
    _, used = composite_mask(Image.new("RGB", (w, h)), make_grid(w, h), str(mask_path), None)
    assert used == 4


def test_mask_resized_to_target(tmp_path):
    mask_path = _half_mask(tmp_path, 100, 43)
    result, _ = composite_mask(Image.new("RGB", (1920, 828)), make_grid(1920, 828), str(mask_path), None)
    assert result.size == (1920, 828)


def test_mask_mixed_modes(tmp_path):
    mask_path = _half_mask(tmp_path, 64, 32)
    original = make_grid(64, 32)
    output = Image.new("RGBA", (64, 32), (0, 0, 0, 255))
    result, _ = composite_mask(output, original, str(mask_path), 1)
    assert result.mode == "RGBA"
    assert result.size == (64, 32)


def test_mask_bad_path_rejected():
    with pytest.raises(InputError):
        composite_mask(Image.new("RGB", (8, 8)), Image.new("RGB", (8, 8)), "relative/mask.png", None)

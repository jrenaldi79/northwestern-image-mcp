from pathlib import Path

import pytest

from openrouter_image_mcp.config import Settings, load_settings

IMAGE_TOOLS_WORKSPACE = "42861d2b-4736-477d-aaeb-0f300c31596f"


def test_defaults():
    s = load_settings({})
    assert isinstance(s, Settings)
    assert s.output_dir == Path.home() / "Pictures" / "OpenRouter Images"
    assert s.max_input_edge == 2048
    assert s.timeout_s == 600
    assert s.ratio_tolerance == 0.03
    assert s.workspace_id == IMAGE_TOOLS_WORKSPACE


def test_env_overrides():
    s = load_settings(
        {
            "OPENROUTER_IMAGE_WORKSPACE_ID": "ws-123",
            "OPENROUTER_IMAGE_OUTPUT_DIR": "~/somewhere/else",
            "OPENROUTER_IMAGE_MAX_INPUT_EDGE": "1024",
            "OPENROUTER_IMAGE_TIMEOUT_S": "30.5",
            "OPENROUTER_IMAGE_RATIO_TOLERANCE": "0.1",
        }
    )
    assert s.workspace_id == "ws-123"
    assert s.output_dir == Path.home() / "somewhere" / "else"
    assert s.max_input_edge == 1024
    assert s.timeout_s == 30.5
    assert s.ratio_tolerance == 0.1


def test_empty_workspace_env_means_personal():
    assert load_settings({"OPENROUTER_IMAGE_WORKSPACE_ID": ""}).workspace_id == ""


@pytest.mark.parametrize(
    "var",
    [
        "OPENROUTER_IMAGE_MAX_INPUT_EDGE",
        "OPENROUTER_IMAGE_TIMEOUT_S",
        "OPENROUTER_IMAGE_RATIO_TOLERANCE",
    ],
)
def test_bad_number_raises(var):
    with pytest.raises(ValueError, match=var):
        load_settings({var: "abc"})


def test_empty_output_dir_env_means_default():
    s = load_settings({"OPENROUTER_IMAGE_OUTPUT_DIR": ""})
    assert s.output_dir == Path.home() / "Pictures" / "OpenRouter Images"

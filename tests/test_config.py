from pathlib import Path

import pytest

from openrouter_image_mcp.config import Settings, load_settings

IMAGE_TOOLS_WORKSPACE = "21082e84-ae02-4639-ad40-c7251b98ab10"


def test_defaults():
    s = load_settings({"OPENROUTER_IMAGE_COHORT": "2027"})
    assert isinstance(s, Settings)
    assert s.output_dir == Path.home() / "Pictures" / "Northwestern AI" / "Class of 2027"
    assert s.max_input_edge == 2048
    assert s.timeout_s == 600
    assert s.advisor_timeout_s == 1800
    assert s.ratio_tolerance == 0.03
    assert s.workspace_id == IMAGE_TOOLS_WORKSPACE


def test_env_overrides():
    s = load_settings(
        {
            "OPENROUTER_IMAGE_WORKSPACE_ID": IMAGE_TOOLS_WORKSPACE,
            "OPENROUTER_IMAGE_OUTPUT_DIR": "~/somewhere/else",
            "OPENROUTER_IMAGE_MAX_INPUT_EDGE": "1024",
            "OPENROUTER_IMAGE_TIMEOUT_S": "30.5",
            "OPENROUTER_IMAGE_RATIO_TOLERANCE": "0.1",
        }
    )
    assert s.workspace_id == IMAGE_TOOLS_WORKSPACE
    assert s.output_dir == Path.home() / "somewhere" / "else"
    assert s.max_input_edge == 1024
    assert s.timeout_s == 30.5
    assert s.advisor_timeout_s == 1800
    assert s.ratio_tolerance == 0.1


def test_empty_workspace_env_is_rejected():
    with pytest.raises(ValueError, match="WORKSPACE_ID"):
        load_settings({"OPENROUTER_IMAGE_WORKSPACE_ID": ""})


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
        load_settings({"OPENROUTER_IMAGE_COHORT": "2027", var: "abc"})


def test_empty_output_dir_env_means_default():
    s = load_settings({"OPENROUTER_IMAGE_COHORT": "2027", "OPENROUTER_IMAGE_OUTPUT_DIR": ""})
    assert s.output_dir == Path.home() / "Pictures" / "Northwestern AI" / "Class of 2027"


def test_advisor_timeout_override_is_independent_of_images():
    s = load_settings({"OPENROUTER_IMAGE_COHORT": "2027",
                       "OPENROUTER_ADVISOR_TIMEOUT_S": "1200.5"})
    assert s.advisor_timeout_s == 1200.5
    assert s.timeout_s == 600


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "1800.1", "abc"])
def test_invalid_advisor_timeout_is_rejected(value):
    with pytest.raises(ValueError, match="OPENROUTER_ADVISOR_TIMEOUT_S"):
        load_settings({"OPENROUTER_IMAGE_COHORT": "2027",
                       "OPENROUTER_ADVISOR_TIMEOUT_S": value})

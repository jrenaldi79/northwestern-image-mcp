"""Checks on the companion skills shipped in skills/.

The server has no prompt presets; the skills carry the know-how. These tests
keep the skills loadable (valid frontmatter) and honest (they only name tools
the server actually exposes).
"""

import re
from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
EXPECTED_SKILLS = {"openrouter-image", "architectural-render-polish"}
TOOL_NAMES = {
    "account_status",
    "auth_login",
    "auth_logout",
    "list_image_models",
    "get_image_model",
    "generate_image",
    "edit_image",
    "remask_image",
}
TOOL_LIKE = re.compile(r"^(account|auth|list|get|generate|edit|remask)_[a-z_]+$")
FENCE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
INLINE_CODE = re.compile(r"`([^`\n]+)`")
CALL = re.compile(r"\b([a-z_][a-z0-9_]*)\s*\(")


def skill_files():
    return sorted(SKILLS_DIR.rglob("*.md"))


def skill_mds():
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def parse_frontmatter(text):
    """Return the frontmatter as a flat dict of single-line `key: value` pairs."""
    assert text.startswith("---\n"), "SKILL.md must start with '---' frontmatter"
    end = text.find("\n---\n", 4)
    assert end != -1, "frontmatter is not closed with '---'"
    fields = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            value = m.group(2).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            fields[m.group(1)] = value
    return fields


def tool_like_tokens(text):
    """Backticked tokens that look like tool names.

    A whole inline-code span counts (`edit_image`), as does the callee of a call
    written in code (`edit_image(prompt, ...)`), inline or in a fenced block.
    Parameter names such as `output_dir` never match the tool prefixes.
    """
    tokens = set()
    for block in FENCE.findall(text):
        tokens.update(CALL.findall(block))
    for span in INLINE_CODE.findall(FENCE.sub("", text)):
        span = span.strip()
        tokens.add(span)
        call = CALL.match(span)
        if call:
            tokens.add(call.group(1))
    return {t for t in tokens if TOOL_LIKE.match(t)}


def read(path):
    return path.read_text(encoding="utf-8")


def test_expected_skills_exist():
    assert {p.parent.name for p in skill_mds()} == EXPECTED_SKILLS
    assert (SKILLS_DIR / "architectural-render-polish" / "prompt-template.md").is_file()


@pytest.mark.parametrize("path", skill_mds(), ids=lambda p: p.parent.name)
def test_skill_frontmatter(path):
    fields = parse_frontmatter(read(path))
    assert fields.get("name") == path.parent.name
    description = fields.get("description", "")
    assert description, "description is required"
    assert len(description) < 1024
    assert description.startswith("Use when"), "description must state when to use"


def test_tool_token_detection():
    sample = (
        "Call `edit_image` with `output_dir` and `fit=\"preserve\"`; "
        "then `generate_images(prompt)` and `list_models`.\n"
        "```\nget_image_modle(model_id)\naccount_status()\n```\n"
    )
    assert tool_like_tokens(sample) == {
        "edit_image",
        "generate_images",
        "list_models",
        "get_image_modle",
        "account_status",
    }


@pytest.mark.parametrize(
    "path", skill_files(), ids=lambda p: p.relative_to(SKILLS_DIR).as_posix()
)
def test_skills_reference_real_tools(path):
    unknown = tool_like_tokens(read(path)) - TOOL_NAMES
    assert not unknown, f"unknown tool names in {path.name}: {sorted(unknown)}"


@pytest.mark.parametrize("path", skill_mds(), ids=lambda p: p.parent.name)
def test_skills_require_consent_for_client_imagery(path):
    assert "explicit OK" in read(path)


def test_masks_section_points_to_remask_image():
    text = read(SKILLS_DIR / "openrouter-image" / "SKILL.md")
    section = text.split("## Edits: paths, size and masks", 1)[1].split("\n## ", 1)[0]
    assert "`remask_image`" in section
    assert ".unmasked.png" in section


def test_model_rules_of_thumb_are_dated():
    text = read(SKILLS_DIR / "openrouter-image" / "SKILL.md")
    assert re.search(r"^#+ .*As of 2026-10", text, re.MULTILINE)


def test_prompt_template_structure():
    text = read(SKILLS_DIR / "architectural-render-polish" / "prompt-template.md")
    assert "KEEP EXACTLY" in text
    assert "IMPROVE ONLY PHOTOGRAPHIC REALISM" in text
    assert re.search(r"\{[a-z_]+\}", text), "template needs {placeholders}"
    assert "Sample_Render" not in text

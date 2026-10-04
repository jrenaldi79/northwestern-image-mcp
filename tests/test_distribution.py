"""Checks that the Claude Code plugin and marketplace match the rest of the repo.

Frontmatter and tool-name checks for the skills live in test_skills.py.
"""

import json
import re
from pathlib import Path

from openrouter_image_mcp import __version__
from openrouter_image_mcp.cli import DEFAULT_REF, render_config

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
PLUGIN = ROOT / "plugin"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
README = ROOT / "README.md"
TOOLS = {
    "account_status",
    "auth_login",
    "auth_logout",
    "list_image_models",
    "get_image_model",
    "generate_image",
    "edit_image",
    "remask_image",
}


def _tree(base: Path) -> dict[str, bytes]:
    return {
        p.relative_to(base).as_posix(): p.read_bytes()
        for p in sorted(base.rglob("*"))
        if p.is_file()
    }


def test_plugin_skills_in_sync():
    source = _tree(SKILLS)
    copied = _tree(PLUGIN / "skills")
    assert source, "skills/ is empty"
    assert set(copied) == set(source), (
        "plugin/skills differs from skills/; run: uv run python scripts/sync_plugin_skills.py"
    )
    for name, data in source.items():
        assert copied[name] == data, f"{name} differs; run scripts/sync_plugin_skills.py"


def test_plugin_mcp_json():
    actual = json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))
    expected = json.loads(render_config("code", "uvx", Path.home()))
    assert actual == expected


def test_marketplace_points_to_plugin():
    data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    entry = data["plugins"][0]
    assert entry["source"] == "./plugin"
    assert entry["name"] == "openrouter-image"


def test_versions_match():
    manifest = json.loads(
        (PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert manifest["version"] == __version__
    assert DEFAULT_REF == f"v{__version__}"


def test_readme_install_refs_match_release():
    text = README.read_text(encoding="utf-8")
    refs = re.findall(r"openrouter-image-mcp(?:@|/archive/refs/tags/)(v[0-9][0-9.]*[0-9])", text)
    assert refs, "README has no install refs"
    assert set(refs) == {DEFAULT_REF}


def test_readme_lists_every_tool():
    text = README.read_text(encoding="utf-8")
    assert set(re.findall(r"^\| `([a-z_]+)` \|", text, re.MULTILINE)) == TOOLS

"""Preservation checks for the local Desktop configuration installer."""

import json

import pytest

from scripts.install_claude_desktop import install


def test_install_preserves_settings_other_servers_and_original_bytes(tmp_path):
    path = tmp_path / "config.json"
    original = {
        "preferences": {"example": True},
        "mcpServers": {
            "other": {"command": "another-server", "args": ["serve"]},
            "northwestern-images": {"command": "old-local-single"},
            "northwestern-images-2027": {"command": "old-local"},
            "northwestern-images-2028": {"command": "old-local"},
        },
    }
    before = json.dumps(original).encode()
    path.write_bytes(before)
    backup = install(path, cohort="2028")
    assert backup.read_bytes() == before
    after = json.loads(path.read_text())
    assert after["preferences"] == original["preferences"]
    assert after["mcpServers"]["other"] == original["mcpServers"]["other"]
    assert set(after["mcpServers"]) == {
        "other",
        "openrouter-sidecar",
    }

    assert (
        after["mcpServers"]["openrouter-sidecar"]["env"]["OPENROUTER_IMAGE_COHORT"]
        == "2028"
    )


@pytest.mark.parametrize("invalid", [[], "", False])
def test_invalid_server_structure_does_not_overwrite_existing_file(tmp_path, invalid):
    path = tmp_path / "config.json"
    before = json.dumps({"mcpServers": invalid}).encode()
    path.write_bytes(before)
    with pytest.raises(TypeError, match="mcpServers"):
        install(path, cohort="2028")
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]

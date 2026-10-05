"""Back up and merge this checkout's single local Northwestern Claude Desktop entry."""

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from openrouter_image_mcp.cli import render_local_config
from openrouter_image_mcp.config import COHORT_WORKSPACES


def install(config_path: Path, *, cohort: str) -> Path | None:
    project = Path(__file__).resolve().parents[1]
    config = (
        json.loads(config_path.read_text(encoding="utf-8-sig"))
        if config_path.exists()
        else {}
    )
    if not isinstance(config, dict):
        raise TypeError("Claude Desktop configuration must be a JSON object.")
    servers = config.get("mcpServers")
    if servers is None:
        servers = {}
    if not isinstance(servers, dict):
        raise TypeError(
            "mcpServers must be a JSON object; original file was not modified."
        )
    entries = json.loads(
        render_local_config(project, Path(sys.executable), cohort=cohort)
    )["mcpServers"]
    # Replace only the two cohort entries created by the previous installer.
    for year in COHORT_WORKSPACES:
        servers.pop(f"northwestern-images-{year}", None)
    servers.update(entries)
    config["mcpServers"] = servers
    config_path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if config_path.exists():
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
        backup = config_path.with_name(
            f"{config_path.name}.northwestern-{timestamp}.bak"
        )
        shutil.copy2(config_path, backup)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=config_path.parent,
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(config, indent=2) + "\n")
        os.replace(temporary, config_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    if any(saved["mcpServers"].get(name) != entry for name, entry in entries.items()):
        raise RuntimeError(
            "Saved Claude Desktop entries did not match the local configuration."
        )
    return backup


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--cohort", required=True, choices=sorted(COHORT_WORKSPACES))
    args = parser.parse_args()
    backup = install(args.config, cohort=args.cohort)
    print(f"Configured: {args.config}")
    if backup is not None:
        print(f"Backup: {backup}")
    print(f"Entry: northwestern-images (Class of {args.cohort})")
    print("Fully quit and reopen Claude Desktop, then complete browser sign-in.")

"""Copy skills/ into plugin/skills/ byte-for-byte, removing stale files.

Run after editing anything under skills/:  uv run python scripts/sync_plugin_skills.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "skills"
DEST = ROOT / "plugin" / "skills"


def sync(src: Path = SRC, dest: Path = DEST) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    for path in sorted(src.rglob("*")):
        if path.is_file():
            target = dest / path.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)


if __name__ == "__main__":
    sync()
    count = sum(1 for p in DEST.rglob("*") if p.is_file())
    print(f"Synced {count} files to {DEST.relative_to(ROOT)}")

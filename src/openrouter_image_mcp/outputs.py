"""Output naming, atomic saves and sidecar metadata.

Pure module: standard library plus Pillow (only for `encode_image`), no network.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

from PIL import Image

from openrouter_image_mcp import __version__

SCHEMA_VERSION = 1
UNMASKED_SUFFIX = ".unmasked.png"
QUALITY = 95
_ALPHA_MODES = frozenset({"RGBA", "LA", "PA", "RGBa", "La"})
_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')


def model_short(model_id: str) -> str:
    """The part of a model id after the last '/'."""
    return model_id.rsplit("/", 1)[-1]


def prompt_slug(prompt: str) -> str:
    """Filesystem-safe slug from the first six words of a prompt ('image' if empty)."""
    words = prompt.lower().split()[:6]
    slug = re.sub(r"[^a-z0-9]+", "-", " ".join(words)).strip("-")
    slug = slug[:60].strip("-")
    return slug or "image"


def _probe_writable(directory: Path) -> None:
    """Create `directory` if needed and prove it is writable. Raises OSError."""
    directory.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".write-test-", dir=directory)
    os.close(fd)
    os.unlink(name)


def choose_dir(preferred: Path | None, fallback: Path) -> tuple[Path, str | None]:
    """Pick the output directory; fall back (with a note) if `preferred` isn't writable."""
    note = None
    if preferred is not None:
        try:
            _probe_writable(preferred)
            return preferred, None
        except OSError as exc:
            note = (
                f"Output folder {preferred} is not writable ({exc}); "
                f"saved to {fallback} instead."
            )
    try:
        _probe_writable(fallback)
    except OSError as exc:
        raise OSError(
            f"Couldn't write to the output folder {fallback} ({exc}). Pass output_dir, or set "
            "OPENROUTER_IMAGE_OUTPUT_DIR, to a folder you can write to."
        ) from exc
    return fallback, note


def _safe_component(text: str) -> str:
    """Replace characters Windows forbids in file names (and control characters) with '-'."""
    return _UNSAFE_CHARS.sub("-", text)


def unmasked_path(image_path: Path) -> Path:
    """Where a masked edit keeps its unblended layer: `<name>.unmasked.png`."""
    return image_path.with_suffix(UNMASKED_SUFFIX)


def _taken(path: Path) -> bool:
    return (
        path.exists()
        or path.with_suffix(".json").exists()
        or unmasked_path(path).exists()
    )


def output_path(
    directory: Path, stem: str, model_id: str, index: int, ext: str, now: datetime
) -> Path:
    """Pick a free `{stem}__{model}_{timestamp}_{index}{ext}` path (does not create it).

    A name is taken if the image, its `.json` sidecar or its `.unmasked.png` layer
    already exists.
    """
    model = _safe_component(model_short(model_id))
    base = f"{_safe_component(stem)}__{model}_{now.strftime('%Y%m%d-%H%M%S')}_{index}"
    path = directory / f"{base}{ext}"
    n = 2
    while _taken(path):
        path = directory / f"{base}-{n}{ext}"
        n += 1
    return path


def write_bytes_atomic(path: Path, data: bytes) -> None:
    """Write via a sibling .tmp file and `os.replace`, so readers never see a partial file."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def write_sidecar(image_path: Path, meta: dict) -> Path:
    """Write `meta` as pretty UTF-8 JSON next to the image, stamping the versions."""
    sidecar = image_path.with_suffix(".json")
    doc = {**meta, "schema_version": SCHEMA_VERSION, "server_version": __version__}
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    write_bytes_atomic(sidecar, text.encode("utf-8"))
    return sidecar


def encode_image(img: Image.Image, output_format: str | None) -> tuple[bytes, str]:
    """Encode `img`; returns (bytes, extension including the dot). Default is PNG."""
    fmt = (output_format or "png").lower()
    buf = BytesIO()
    if fmt == "png":
        img.save(buf, format="PNG")
        ext = ".png"
    elif fmt in ("jpeg", "jpg"):
        if img.mode in _ALPHA_MODES or "transparency" in img.info:
            rgba = img.convert("RGBA")
            flat = Image.new("RGB", rgba.size, (255, 255, 255))
            flat.paste(rgba, mask=rgba.getchannel("A"))
        else:
            flat = img.convert("RGB")
        flat.save(buf, format="JPEG", quality=QUALITY)
        ext = ".jpg"
    elif fmt == "webp":
        img.save(buf, format="WEBP", quality=QUALITY)
        ext = ".webp"
    else:
        raise ValueError(f"Unsupported output format: {output_format!r}")
    return buf.getvalue(), ext

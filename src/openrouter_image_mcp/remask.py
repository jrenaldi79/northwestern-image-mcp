"""Re-blend a masked edit through a new mask, locally and for free.

A masked `edit_image` keeps the model's fitted, pre-blend image as
`<result>.unmasked.png`. `remask` composites that layer over the original
input again through a different mask, without calling any model.

Pure module: Pillow plus the standard library, no network.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .config import Settings
from .imaging import (
    InputError,
    check_mask,
    composite_mask,
    make_preview,
    prepare_input,
    resolve_user_path,
    user_dir,
)
from .outputs import (
    choose_dir,
    encode_image,
    output_path,
    write_bytes_atomic,
    write_sidecar,
)

TOOL = "remask_image"
MODEL_LABEL = "remask"  # stands in for the model in `<stem>__remask_<ts>_1.png`

NO_MASK_MSG = "This image wasn't made with a mask, so there is no unblended layer to re-mask."
NO_LAYER_KEY_MSG = (
    "This result has no unblended layer: it was made before v0.2.0, which started saving "
    "one. Run edit_image again with mask_path to get a result that can be re-masked."
)
CHANGED_ORIGINAL_MSG = (
    "The original input image has changed since this result was made ({path}), so the "
    "unblended layer no longer lines up with it. Restore the original, or run edit_image again."
)


@dataclass
class RemaskResult:
    path: Path
    sidecar: Path
    preview_jpeg: bytes
    note: str | None  # e.g. the output folder wasn't writable and a fallback was used


def _read_sidecar(result: Path) -> dict:
    sidecar = result.with_suffix(".json")
    if not sidecar.is_file():
        raise InputError(
            f"No sidecar {sidecar} next to {result}; remask_image needs a result saved by "
            "edit_image with mask_path, together with its .json sidecar."
        )
    try:
        meta = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise InputError(f"Cannot read the sidecar {sidecar}: {e}") from e
    if not isinstance(meta, dict):
        raise InputError(f"The sidecar {sidecar} is not a JSON object.")
    return meta


def _source_input(meta: dict) -> tuple[Path, str]:
    """The original input's path and sha256, as recorded by the source result."""
    inputs = meta.get("inputs")
    first = inputs[0] if isinstance(inputs, list) and inputs else None
    if not (
        isinstance(first, dict)
        and isinstance(first.get("path"), str)
        and isinstance(first.get("sha256"), str)
    ):
        raise InputError("The sidecar doesn't record the original input image.")
    return Path(first["path"]), first["sha256"]


def _open_layer(path: Path) -> Image.Image:
    try:
        with Image.open(path) as opened:
            opened.load()
            return opened.copy()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError) as e:
        raise InputError(f"Cannot read the unblended layer {path} as an image: {e}") from e


def remask(
    result_path: str,
    mask_path: str,
    mask_feather_px: int | None,
    output_dir: str | None,
    settings: Settings,
    now: datetime,
) -> RemaskResult:
    """Blend `result_path`'s unblended layer over its original input through a new mask.

    Saves a new PNG (never overwriting) with a sidecar next to the source result,
    or in `output_dir`. Every path must be absolute or start with '~'.
    """
    result = resolve_user_path(result_path)
    out_dir = user_dir(output_dir)
    meta = _read_sidecar(result)
    if meta.get("mask") is None:
        raise InputError(NO_MASK_MSG)
    if meta.get("unmasked_path") is None:
        raise InputError(NO_LAYER_KEY_MSG)
    layer_path = Path(str(meta["unmasked_path"]))
    if not layer_path.is_file():
        raise InputError(f"The unblended layer {layer_path} is missing.")
    original_path, original_sha = _source_input(meta)
    if not original_path.is_file():
        raise InputError(
            f"The original input image {original_path} is missing; re-masking blends against it."
        )

    mask = check_mask(mask_path)  # a bad mask fails before any image work

    original = prepare_input(str(original_path), settings.max_input_edge)
    if original.sha256 != original_sha:
        raise InputError(CHANGED_ORIGINAL_MSG.format(path=original.path))
    layer = _open_layer(layer_path)
    if layer.size != original.original_size:
        w, h = layer.size
        ow, oh = original.original_size
        raise InputError(
            f"The unblended layer {layer_path} is {w}×{h} but the original input is "
            f"{ow}×{oh}; their size must match."
        )

    blended, feather = composite_mask(layer, original.original, str(mask), mask_feather_px)

    directory, note = choose_dir(out_dir or result.parent, settings.output_dir)
    path = output_path(
        directory, stem=result.stem, model_id=MODEL_LABEL, index=1, ext=".png", now=now
    )
    data, _ = encode_image(blended, None)
    write_bytes_atomic(path, data)
    stamp = now if now.tzinfo is not None else now.astimezone()
    sidecar = write_sidecar(path, {
        "tool": TOOL,
        "created_at": stamp.isoformat(timespec="seconds"),
        "model": meta.get("model"),
        "prompt": meta.get("prompt"),
        "source_result": result.as_posix(),
        "unmasked_path": layer_path.as_posix(),
        "inputs": meta.get("inputs"),
        "mask": {"path": mask.as_posix(), "feather_px": feather},
        "cost_usd": 0,
    })
    return RemaskResult(path, sidecar, make_preview(blended), note)

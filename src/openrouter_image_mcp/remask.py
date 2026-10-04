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
    is_network_path,
    make_preview,
    prepare_input,
    reject_network_path,
    resolve_user_path,
    user_dir,
)
from .outputs import (
    UNMASKED_SUFFIX,
    choose_dir,
    encode_image,
    output_path,
    unmasked_path,
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
    notes: list[str]  # e.g. a fallback output folder, or the layer found next to a moved result


def _sidecar_path(value: object, what: str, suffix: str | None = None) -> Path:
    """A path recorded in the sidecar: untrusted, so it must be a local absolute path."""
    problem = None
    if not isinstance(value, str) or not value:
        problem = "it is not a path"
    elif is_network_path(value):
        problem = "network (UNC) paths aren't allowed"
    elif not Path(value).is_absolute():
        problem = "it is not absolute"
    elif suffix is not None and not value.lower().endswith(suffix):
        problem = f"it doesn't end in {suffix}"
    if problem:
        raise InputError(f"The sidecar records an invalid {what} path {value!r}: {problem}.")
    return Path(value)


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
    if not (isinstance(first, dict) and "path" in first and isinstance(first.get("sha256"), str)):
        raise InputError("The sidecar doesn't record the original input image.")
    return _sidecar_path(first["path"], "original-input"), first["sha256"]


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
    or in `output_dir`. Every path must be absolute or start with '~', and network (UNC)
    paths are rejected. Paths read from the sidecar are untrusted: they must be local and
    absolute, and are checked before anything stats them. If the recorded layer is gone
    but `<result>.unmasked.png` sits next to the result (a moved folder), that is used,
    with a note; the original input is never guessed.
    """
    # The shared helpers refuse network (UNC) paths before touching them.
    result = resolve_user_path(result_path)
    reject_network_path(mask_path, "mask_path")  # fail early; check_mask runs later
    out_dir = user_dir(output_dir)
    meta = _read_sidecar(result)
    notes: list[str] = []
    if meta.get("mask") is None:
        raise InputError(NO_MASK_MSG)
    if not isinstance(meta["mask"], dict):
        raise InputError(f"The sidecar records an invalid mask entry: {meta['mask']!r}.")
    if meta.get("unmasked_path") is None:
        raise InputError(NO_LAYER_KEY_MSG)
    recorded = _sidecar_path(meta["unmasked_path"], "unblended-layer", UNMASKED_SUFFIX)
    original_path, original_sha = _source_input(meta)  # validated before any stat
    layer_path = recorded
    if not recorded.is_file():
        beside = unmasked_path(result)
        if not beside.is_file():
            raise InputError(f"The unblended layer {recorded} is missing.")
        # The result's folder was moved or renamed: its layer moved with it.
        layer_path = beside
        notes.append(
            f"The unblended layer wasn't at its recorded path {recorded}; used {beside} "
            "next to the result instead."
        )
    if not original_path.is_file():  # never guessed: it must be exactly where it was
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

    directory, dir_note = choose_dir(out_dir or result.parent, settings.output_dir)
    if dir_note:
        notes.append(dir_note)
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
    return RemaskResult(path, sidecar, make_preview(blended), notes)

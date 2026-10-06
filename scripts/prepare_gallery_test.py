"""Create a synthetic masked-edit fixture for a free Desktop gallery check.

No authentication, upload, or model call. Each run creates a separate folder.
"""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw


def prepare_fixture(parent: Path) -> dict[str, str]:
    parent.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="preview-", dir=parent)).resolve()
    original_path = directory / "original.png"
    result_path = directory / "gallery-test.png"
    layer_path = directory / "gallery-test.unmasked.png"
    mask_path = directory / "mask.png"
    original = Image.new("RGB", (640, 360), "#4e2a84")
    layer = Image.new("RGB", original.size, "#b6acd1")
    for image in (original, layer):
        ImageDraw.Draw(image).text((40, 40), "Northwestern gallery test", fill="white", font_size=28)
    mask = Image.new("L", original.size, 0)
    mask.paste(255, (0, 0, 320, 360))
    original.save(original_path)
    layer.save(layer_path)
    mask.save(mask_path)
    Image.composite(layer, original, mask).save(result_path)
    result_path.with_suffix(".json").write_text(json.dumps({
        "tool": "edit_image",
        "model": "synthetic-local-test",
        "prompt": "Synthetic fixture; no model was called",
        "cost_usd": 0,
        "inputs": [{"path": str(original_path), "sha256": hashlib.sha256(original_path.read_bytes()).hexdigest()}],
        "mask": {"path": str(mask_path), "feather_px": 0},
        "unmasked_path": str(layer_path),
    }, indent=2), encoding="utf-8")
    return {"image": str(result_path), "mask_path": str(mask_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / ".venv" / "gallery-tests")
    arguments = prepare_fixture(parser.parse_args().output_dir)
    print("In a new Claude Desktop chat, use openrouter-sidecar:")
    print("Call remask_image with exactly these arguments. It is free and offline.")
    print(json.dumps(arguments, indent=2))
    print("Check that the result shows an inline image gallery with a $0.00 cost.")


if __name__ == "__main__":
    main()

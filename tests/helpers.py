"""Synthetic image makers shared by the imaging tests."""

from pathlib import Path

from PIL import Image

# Twelve clearly distinct colours, one per grid cell (row-major).
PALETTE: list[tuple[int, int, int]] = [
    (230, 25, 75),
    (60, 180, 75),
    (255, 225, 25),
    (0, 130, 200),
    (245, 130, 48),
    (145, 30, 180),
    (70, 240, 240),
    (240, 50, 230),
    (210, 245, 60),
    (0, 128, 128),
    (128, 0, 0),
    (128, 128, 128),
]


def cell_color(col: int, row: int, cols: int = 4) -> tuple[int, int, int]:
    """Colour of grid cell (col, row) for a grid with `cols` columns."""
    return PALETTE[(row * cols + col) % len(PALETTE)]


def make_grid(w: int, h: int, cols: int = 4, rows: int = 3) -> Image.Image:
    """RGB image split into cols x rows cells, each a distinct colour.

    Cell (col, row) is filled with `cell_color(col, row, cols)`, so tests can
    check crop and pad alignment by sampling pixels.
    """
    img = Image.new("RGB", (w, h))
    for row in range(rows):
        for col in range(cols):
            box = (col * w // cols, row * h // rows, (col + 1) * w // cols, (row + 1) * h // rows)
            img.paste(cell_color(col, row, cols), box)
    return img


def save(img: Image.Image, path, fmt: str, exif_orientation: int | None = None) -> Path:
    """Save `img` to `path` as Pillow format `fmt`, optionally with EXIF Orientation."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    kwargs = {}
    if exif_orientation is not None:
        exif = Image.Exif()
        exif[0x0112] = exif_orientation
        exif[0x010F] = "TestCam"  # Make, so the block is non-trivial
        kwargs["exif"] = exif.tobytes()
    img.save(path, format=fmt, **kwargs)
    return path


def unc_paths(name: str) -> list[str]:
    """Network (UNC) spellings of `name` on a remote share, including mixed separators.

    Windows treats '/' and backslash alike, so all of these open SMB if anything stats them.
    """
    return [
        rf"\\evil-host\share\{name}",
        f"//evil-host/share/{name}",
        rf"\/evil-host/share/{name}",
        rf"/\evil-host\share\{name}",
        rf"\\?\UNC\evil-host\share\{name}",
    ]

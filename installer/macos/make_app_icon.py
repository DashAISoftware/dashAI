"""Render the macOS app icon (installer/dashAI.icns).

Run on macOS from the repository root (uses qlmanage and iconutil):

    uv run --no-sync python installer/macos/make_app_icon.py

The icon follows Apple's macOS grid: a flat white rounded square of 824x824
on a 1024x1024 canvas with the dashAI isotype centered.
A bare isotype on a transparent canvas gets wrapped by macOS 26 in a gray
rounded square, so the white shape has to be part of the icon itself.
"""

import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
ISOTYPE_SVG = ROOT / "DashAI/front/public/dashai-isotype.svg"
OUT = ROOT / "installer/dashAI.icns"

CANVAS = 1024
SHAPE = 824  # Apple grid: 100px margin on each side.
RADIUS = 185
ACCENT = (44, 122, 255)
ISOTYPE_HEIGHT = 520

# (file name, pixel size) pairs required by iconutil.
ICONSET = [
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
]


def rasterize_isotype(px_height: int) -> Image.Image:
    """Rasterize the isotype with qlmanage, trimmed and recolored."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["qlmanage", "-t", "-s", "3000", "-o", tmp, str(ISOTYPE_SVG)],
            check=True,
            capture_output=True,
        )
        raster = Image.open(Path(tmp) / f"{ISOTYPE_SVG.name}.png").convert("RGB")
    white = Image.new("RGB", raster.size, (255, 255, 255))
    raster = raster.crop(ImageChops.difference(raster, white).getbbox())
    alpha = ImageChops.invert(raster.convert("L")).point(lambda v: min(255, v * 3))
    solid = Image.new("RGBA", raster.size, ACCENT + (255,))
    solid.putalpha(alpha)
    ratio = px_height / solid.height
    return solid.resize((round(solid.width * ratio), px_height), Image.LANCZOS)


def render() -> Image.Image:
    icon = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    m = (CANVAS - SHAPE) // 2
    box = (m, m, m + SHAPE, m + SHAPE)

    # Flat white shape. No shadow or gradient: macOS 26 adds its own glass rim
    # and a baked-in shadow on top of it reads as a double bevel.
    ImageDraw.Draw(icon).rounded_rectangle(
        box, radius=RADIUS, fill=(255, 255, 255, 255)
    )

    # Isotype, centered.
    mark = rasterize_isotype(ISOTYPE_HEIGHT)
    icon.alpha_composite(
        mark, ((CANVAS - mark.width) // 2, (CANVAS - mark.height) // 2)
    )
    return icon


def main() -> None:
    master = render()
    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "dashAI.iconset"
        iconset.mkdir()
        for name, px in ICONSET:
            master.resize((px, px), Image.LANCZOS).save(iconset / name)
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(OUT)],
            check=True,
            capture_output=True,
        )
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

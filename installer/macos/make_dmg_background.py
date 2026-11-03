"""Render the background image of the macOS DMG installer window.

Run on macOS from the repository root (uses qlmanage to rasterize the logo):

    uv run --no-sync python installer/macos/make_dmg_background.py

Writes installer/macos/dmg-background.tiff, a multi-resolution TIFF (1x and
2x) that Finder picks the right size from on regular and Retina screens.

The look follows the hero section of the website (docs/src/css/custom.css):
two soft radial gradients and a faint rotated isotype watermark. The icon
positions below must match the --icon / --app-drop-link arguments passed to
create-dmg in sign_and_notarize.sh.
"""

import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
LOGO_SVG = ROOT / "DashAI/front/public/dashai-logo.svg"
ISOTYPE_SVG = ROOT / "DashAI/front/public/dashai-isotype.svg"

# Window content size in points (create-dmg --window-size).
WIDTH, HEIGHT = 720, 360
# Icon centers in points (create-dmg --icon / --app-drop-link).
APP_X, DROP_X, ICON_Y = 200, 520, 210
ICON_SIZE = 128

# Website tokens (docs/src/css/custom.css, light theme).
BG_BASE = (254, 254, 255)
ACCENT = (44, 122, 255)


def rasterize_svg(svg: Path, px_width: int, color: tuple) -> Image.Image:
    """Rasterize a one-color SVG with qlmanage, trimmed and recolored."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["qlmanage", "-t", "-s", "2400", "-o", tmp, str(svg)],
            check=True,
            capture_output=True,
        )
        raster = Image.open(Path(tmp) / f"{svg.name}.png").convert("RGB")
    # qlmanage renders on white: trim, then turn the white into transparency.
    white = Image.new("RGB", raster.size, (255, 255, 255))
    raster = raster.crop(ImageChops.difference(raster, white).getbbox())
    alpha = ImageChops.invert(raster.convert("L")).point(lambda v: min(255, v * 3))
    solid = Image.new("RGBA", raster.size, color[:3] + (255,))
    solid.putalpha(alpha)
    ratio = px_width / solid.width
    return solid.resize((px_width, round(solid.height * ratio)), Image.LANCZOS)


def radial_glow(size, center, radii, color, max_alpha) -> Image.Image:
    """CSS-like radial-gradient(rx ry at cx cy, color, transparent 60%)."""
    w, h = size
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.sqrt(
        ((xs - center[0]) / radii[0]) ** 2 + ((ys - center[1]) / radii[1]) ** 2
    )
    alpha = np.clip(1.0 - dist / 0.6, 0.0, 1.0) * max_alpha * 255
    layer = np.zeros((h, w, 4), dtype=np.uint8)
    layer[..., :3] = color
    layer[..., 3] = alpha.astype(np.uint8)
    return Image.fromarray(layer, "RGBA")


def render(scale: int) -> Image.Image:
    s = scale
    size = (WIDTH * s, HEIGHT * s)
    img = Image.new("RGBA", size, BG_BASE + (255,))

    # Hero gradients, scaled down from the website's 1440px-wide layout.
    img.alpha_composite(
        radial_glow(
            size, (0.82 * size[0], -0.12 * size[1]), (560 * s, 300 * s), ACCENT, 0.09
        )
    )
    img.alpha_composite(
        radial_glow(
            size, (-0.05 * size[0], 1.15 * size[1]), (420 * s, 240 * s), ACCENT, 0.07
        )
    )

    # Isotype watermark, top right, rotated -8deg at 5% opacity.
    mark = rasterize_svg(ISOTYPE_SVG, 230 * s, ACCENT)
    mark.putalpha(mark.getchannel("A").point(lambda v: v * 5 // 100))
    mark = mark.rotate(8, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(mark, (size[0] - mark.width + 50 * s, -60 * s))

    draw = ImageDraw.Draw(img)

    # Logo, centered at the top.
    logo = rasterize_svg(LOGO_SVG, 150 * s, ACCENT)
    img.alpha_composite(logo, ((size[0] - logo.width) // 2, 34 * s))

    # Arrow between the icons, at icon-center height.
    ax0 = APP_X + ICON_SIZE // 2 + 24
    ax1 = DROP_X - ICON_SIZE // 2 - 24
    y = ICON_Y
    draw.line((ax0 * s, y * s, (ax1 - 10) * s, y * s), fill=ACCENT, width=6 * s)
    draw.ellipse(((ax0 - 3) * s, (y - 3) * s, (ax0 + 3) * s, (y + 3) * s), fill=ACCENT)
    draw.polygon(
        [
            (ax1 * s, y * s),
            ((ax1 - 18) * s, (y - 13) * s),
            ((ax1 - 18) * s, (y + 13) * s),
        ],
        fill=ACCENT,
    )

    return img.convert("RGB")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        one_x = Path(tmp) / "bg.png"
        two_x = Path(tmp) / "bg@2x.png"
        render(1).save(one_x, dpi=(72, 72))
        render(2).save(two_x, dpi=(144, 144))
        out = OUT_DIR / "dmg-background.tiff"
        subprocess.run(
            ["tiffutil", "-cathidpicheck", str(one_x), str(two_x), "-out", str(out)],
            check=True,
            capture_output=True,
        )
    print(f"Wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

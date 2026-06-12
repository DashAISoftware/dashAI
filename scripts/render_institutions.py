"""Render the institutions block of README.rst from institutions.json.

The canonical institution and funding data lives in
``docs/static/institutions/institutions.json``. This script regenerates:

* ``images/logos.png``: a single banner image with every institution logo
  trimmed and scaled to a uniform cell size, and
* the README.rst section delimited by the markers::

      .. INSTITUTIONS-BLOCK:START
      .. INSTITUTIONS-BLOCK:END

Run it after editing the JSON file or any logo image:

.. code:: bash

    python scripts/render_institutions.py

Use ``--check`` (e.g. in CI) to fail without writing when README.rst or
images/logos.png is out of date.
"""

import argparse
import io
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops

REPO_ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = REPO_ROOT / "docs" / "static" / "institutions" / "institutions.json"
README_PATH = REPO_ROOT / "README.rst"
LOGOS_PNG_PATH = REPO_ROOT / "images" / "logos.png"

# Logo paths in the JSON are relative to the docs site root (docs/static/).
DOCS_STATIC = REPO_ROOT / "docs" / "static"

START_MARKER = ".. INSTITUTIONS-BLOCK:START"
END_MARKER = ".. INSTITUTIONS-BLOCK:END"

# Each logo is trimmed and scaled to fit one cell of the banner.
CELL_WIDTH = 280
CELL_HEIGHT = 120
CELL_GAP = 40
CANVAS_MARGIN = 20
BACKGROUND = (255, 255, 255)


def _logo_entries(data):
    """Return every entry that has a logo, in display order.

    Parameters
    ----------
    data : dict
        Parsed content of institutions.json.

    Returns
    -------
    list of dict
        Institution and acknowledgment entries whose ``logo`` is set.
    """
    return [
        inst
        for inst in data["institutions"] + data["acknowledgments"]["logos"]
        if inst.get("logo")
    ]


def _trim(img):
    """Crop the uniform white or transparent border around a logo.

    Parameters
    ----------
    img : PIL.Image.Image
        The logo image.

    Returns
    -------
    PIL.Image.Image
        The cropped logo in RGBA mode.
    """
    rgba = img.convert("RGBA")
    on_white = Image.new("RGB", rgba.size, BACKGROUND)
    on_white.paste(rgba, mask=rgba.getchannel("A"))
    diff = ImageChops.difference(on_white, Image.new("RGB", rgba.size, BACKGROUND))
    bbox = diff.getbbox()
    return rgba.crop(bbox) if bbox else rgba


def build_logos_png(data):
    """Compose the combined logo banner.

    Every logo is trimmed, scaled (preserving aspect ratio) to fit a
    CELL_WIDTH x CELL_HEIGHT cell, and centered in its cell on a white
    banner.

    Parameters
    ----------
    data : dict
        Parsed content of institutions.json.

    Returns
    -------
    bytes
        The banner encoded as PNG.
    """
    cells = []
    for inst in _logo_entries(data):
        with Image.open(DOCS_STATIC / inst["logo"]) as img:
            logo = _trim(img)
        scale = min(CELL_WIDTH / logo.width, CELL_HEIGHT / logo.height)
        size = (max(1, round(logo.width * scale)), max(1, round(logo.height * scale)))
        cells.append(logo.resize(size, Image.LANCZOS))

    width = 2 * CANVAS_MARGIN + len(cells) * CELL_WIDTH + (len(cells) - 1) * CELL_GAP
    height = 2 * CANVAS_MARGIN + CELL_HEIGHT
    canvas = Image.new("RGB", (width, height), BACKGROUND)
    x = CANVAS_MARGIN
    for cell in cells:
        canvas.paste(
            cell,
            (
                x + (CELL_WIDTH - cell.width) // 2,
                CANVAS_MARGIN + (CELL_HEIGHT - cell.height) // 2,
            ),
            cell,
        )
        x += CELL_WIDTH + CELL_GAP

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def render_block(data):
    """Render the institutions section as reStructuredText.

    Parameters
    ----------
    data : dict
        Parsed content of institutions.json, with ``institutions`` and
        ``acknowledgments`` keys.

    Returns
    -------
    str
        The generated RST block, including the start and end markers.
    """
    lines = [
        START_MARKER,
        "",
        ".. This block is auto-generated from "
        "docs/static/institutions/institutions.json.",
        "   Edit that file and run ``python scripts/render_institutions.py``. "
        "Do not edit by hand.",
        "",
        "This project is developed in collaboration with:",
        "",
    ]

    for inst in data["institutions"]:
        lines.append(f"* `{inst['name']} <{inst['url']}>`_ - {inst['role']}")
    lines.append("")

    lines.append(data["acknowledgments"]["text"])
    lines.append("")

    lines.extend(
        [
            ".. image:: images/logos.png",
            "   :alt: Logos of collaborating institutions",
            "",
            END_MARKER,
        ]
    )
    return "\n".join(lines)


def main():
    """Regenerate the institutions block in README.rst and images/logos.png.

    Returns
    -------
    int
        Process exit code: 0 on success or no changes needed, 1 when
        ``--check`` finds README.rst or images/logos.png out of date.

    Raises
    ------
    SystemExit
        If the markers are missing from README.rst.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if README.rst or images/logos.png is out of date "
        "instead of writing them",
    )
    args = parser.parse_args()

    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    readme = README_PATH.read_text(encoding="utf-8")

    start = readme.find(START_MARKER)
    end = readme.find(END_MARKER)
    if start == -1 or end == -1:
        sys.exit(f"Markers '{START_MARKER}' / '{END_MARKER}' not found in README.rst")

    block = render_block(data)
    updated = readme[:start] + block + readme[end + len(END_MARKER) :]
    readme_stale = updated != readme

    png = build_logos_png(data)
    png_stale = not LOGOS_PNG_PATH.exists() or LOGOS_PNG_PATH.read_bytes() != png

    if not readme_stale and not png_stale:
        print("README.rst and images/logos.png are up to date.")
        return 0
    if args.check:
        print(
            "README.rst or images/logos.png is out of date. "
            "Run: python scripts/render_institutions.py"
        )
        return 1

    if readme_stale:
        README_PATH.write_text(updated, encoding="utf-8")
        print("README.rst updated.")
    if png_stale:
        LOGOS_PNG_PATH.write_bytes(png)
        print("images/logos.png updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

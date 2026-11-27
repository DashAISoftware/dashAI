"""Render the institutions block of README.rst from institutions.json.

The canonical institution and funding data lives in
``docs/static/institutions/institutions.json``. This script regenerates:

* ``images/institutions/<id>.png``: one image per logo, trimmed and
  centered on a white cell of uniform size, so every logo can link to
  its institution and stays visible on GitHub's dark theme, and
* the README.rst section delimited by the markers::

      .. INSTITUTIONS-BLOCK:START
      .. INSTITUTIONS-BLOCK:END

Run it after editing the JSON file or any logo image:

.. code:: bash

    python scripts/render_institutions.py

Use ``--check`` (e.g. in CI) to fail without writing when README.rst is
out of date. The check does not cover the logo images, because PNG
bytes vary across platforms and Pillow versions.
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
LOGOS_DIR = REPO_ROOT / "images" / "institutions"

# Logo paths in the JSON are relative to the docs site root (docs/static/).
DOCS_STATIC = REPO_ROOT / "docs" / "static"

START_MARKER = ".. INSTITUTIONS-BLOCK:START"
END_MARKER = ".. INSTITUTIONS-BLOCK:END"

# Each logo is trimmed and scaled to fit a cell of this size, with padding.
# GitHub strips the ``style`` attribute that RST's ``:width:`` turns into,
# so the cell size is also the size at which the README shows each logo.
CELL_WIDTH = 200
CELL_HEIGHT = 86
CELL_PADDING = 10
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


def build_logo_png(inst):
    """Render one logo as a PNG cell.

    The logo is trimmed, scaled (preserving aspect ratio) to fit the cell
    minus its padding, and centered on an opaque white background, so
    dark logos stay visible on GitHub's dark theme.

    Parameters
    ----------
    inst : dict
        An institution or acknowledgment entry with a ``logo`` path.

    Returns
    -------
    bytes
        The cell encoded as PNG.
    """
    with Image.open(DOCS_STATIC / inst["logo"]) as img:
        logo = _trim(img)
    max_width = CELL_WIDTH - 2 * CELL_PADDING
    max_height = CELL_HEIGHT - 2 * CELL_PADDING
    scale = min(max_width / logo.width, max_height / logo.height)
    size = (max(1, round(logo.width * scale)), max(1, round(logo.height * scale)))
    logo = logo.resize(size, Image.LANCZOS)

    canvas = Image.new("RGB", (CELL_WIDTH, CELL_HEIGHT), BACKGROUND)
    canvas.paste(
        logo,
        ((CELL_WIDTH - logo.width) // 2, (CELL_HEIGHT - logo.height) // 2),
        logo,
    )
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def render_block(data):
    """Render the institutions section as reStructuredText.

    Each logo is an inline substitution with a ``:target:``, so GitHub
    shows the logos side by side and each one links to its institution.

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
        lines.append(f"* `{inst['name']} <{inst['url']}>`_ - {inst['role']['en']}")
    lines.append("")

    lines.append(data["acknowledgments"]["text"]["en"])
    lines.append("")

    entries = _logo_entries(data)
    lines.append(" ".join(f"|logo-{inst['id']}|" for inst in entries))
    lines.append("")
    for inst in entries:
        lines.extend(
            [
                f".. |logo-{inst['id']}| image:: images/institutions/{inst['id']}.png",
                f"   :target: {inst['url']}",
                f"   :alt: {inst.get('fullName') or inst['name']}",
                "",
            ]
        )

    lines.append(END_MARKER)
    return "\n".join(lines)


def write_logo_images(data):
    """Write one PNG per logo and remove images no longer listed.

    Parameters
    ----------
    data : dict
        Parsed content of institutions.json.
    """
    LOGOS_DIR.mkdir(parents=True, exist_ok=True)
    expected = set()
    for inst in _logo_entries(data):
        path = LOGOS_DIR / f"{inst['id']}.png"
        expected.add(path.name)
        png = build_logo_png(inst)
        if not path.exists() or path.read_bytes() != png:
            path.write_bytes(png)
            print(f"{path.relative_to(REPO_ROOT)} updated.")
    for path in LOGOS_DIR.glob("*.png"):
        if path.name not in expected:
            path.unlink()
            print(f"{path.relative_to(REPO_ROOT)} removed.")


def main():
    """Regenerate the institutions block in README.rst and the logo images.

    Returns
    -------
    int
        Process exit code: 0 on success or no changes needed, 1 when
        ``--check`` finds README.rst out of date.

    Raises
    ------
    SystemExit
        If the markers are missing from README.rst.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if README.rst is out of date instead of writing files",
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

    if args.check:
        if readme_stale:
            print(
                "README.rst is out of date. Run: python scripts/render_institutions.py"
            )
            return 1
        print("README.rst is up to date.")
        return 0

    if readme_stale:
        README_PATH.write_text(updated, encoding="utf-8")
        print("README.rst updated.")
    else:
        print("README.rst is up to date.")

    write_logo_images(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())

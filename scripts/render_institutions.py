"""Render the institutions block of README.rst from institutions.json.

The canonical institution and funding data lives in
``docs/static/institutions/institutions.json``. This script regenerates the
README.rst section delimited by the markers::

    .. INSTITUTIONS-BLOCK:START
    .. INSTITUTIONS-BLOCK:END

Run it after editing the JSON file:

.. code:: bash

    python scripts/render_institutions.py

Use ``--check`` (e.g. in CI) to fail without writing when README.rst is out
of date.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = REPO_ROOT / "docs" / "static" / "institutions" / "institutions.json"
README_PATH = REPO_ROOT / "README.rst"

START_MARKER = ".. INSTITUTIONS-BLOCK:START"
END_MARKER = ".. INSTITUTIONS-BLOCK:END"

# Logo paths in the JSON are relative to the docs site root (docs/static/).
LOGO_PREFIX = "docs/static/"

LOGO_HEIGHT = "60"
LOGO_HEIGHT_SMALL = "45"


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

    logo_entries = [
        inst
        for inst in data["institutions"] + data["acknowledgments"]["logos"]
        if inst.get("logo")
    ]
    for inst in logo_entries:
        height = LOGO_HEIGHT_SMALL if inst.get("small") else LOGO_HEIGHT
        lines.extend(
            [
                f".. |logo-{inst['id']}| image:: {LOGO_PREFIX}{inst['logo']}",
                f"   :height: {height}",
                f"   :target: {inst['url']}",
                f"   :alt: {inst.get('fullName') or inst['name']}",
                "",
            ]
        )

    refs = " ".join(f"|logo-{inst['id']}|" for inst in logo_entries)
    lines.extend([refs, "", END_MARKER])
    return "\n".join(lines)


def main():
    """Regenerate the institutions block in README.rst.

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
        help="exit 1 if README.rst is out of date instead of writing it",
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

    if updated == readme:
        print("README.rst is up to date.")
        return 0
    if args.check:
        print("README.rst is out of date. Run: python scripts/render_institutions.py")
        return 1

    README_PATH.write_text(updated, encoding="utf-8")
    print("README.rst updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

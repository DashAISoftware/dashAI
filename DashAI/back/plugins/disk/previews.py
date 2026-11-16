"""Reviewed copies in ``plugins/.previews/<token>/``, taken under lock."""

import json
import logging
import re
import secrets
import shutil
import time
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Iterator, NamedTuple

from DashAI.back.plugins.disk.trash import (
    hidden_folder,
    replace,
    retry_busy,
    write_json,
)
from DashAI.back.plugins.errors import CodedError
from DashAI.back.plugins.sources.base import Fetched

logger = logging.getLogger(__name__)

PREVIEWS_DIR = ".previews"
MAX_AGE_SECONDS = 60 * 60
MAX_PREVIEWS = 8  # a plugin and the ones it needs from the store, reviewed at once
TOKEN = r"^[A-Za-z0-9_-]{22}$"  # secrets.token_urlsafe(16)

_PLUGIN = "plugin"
_FILE = "preview.json"
_TAKEN = ".taken"  # suffix of a preview an install is using


class PreviewExpiredError(CodedError):
    """Gone: installed already, abandoned and removed, or never existed."""

    code = "preview_expired"


class Preview(NamedTuple):
    """What to install and where it came from."""

    source: str  # a PluginSource value
    location: str  # recorded in .source (a .zip's own name for an upload)
    fetched: Fetched


def _folder(root: Path, token: str) -> Path:
    # The token comes from the client and names a folder.
    if not re.fullmatch(TOKEN, token):
        raise PreviewExpiredError(f"Not a preview: {token!r}")
    return root / PREVIEWS_DIR / token


def _created(folder: Path) -> float:
    """When it was saved, or made if it has no ``preview.json`` yet."""
    try:
        return json.loads((folder / _FILE).read_text("utf-8"))["created_at"]
    except (OSError, ValueError, KeyError, TypeError):
        return folder.stat().st_mtime


def save(root: Path, preview: Preview) -> str:
    """Copy ``preview`` (the fetch removes its own folder) and return its token."""
    sweep(root, keep=MAX_PREVIEWS - 1)
    token = secrets.token_urlsafe(16)
    folder = hidden_folder(root / PREVIEWS_DIR) / token
    try:
        # As links, like storage.save, since one to a parent folder would loop.
        shutil.copytree(preview.fetched.path, folder / _PLUGIN, symlinks=True)
        details = preview.fetched._asdict()
        del details["path"]
        # Written last, so a preview exists only once complete.
        write_json(
            folder / _FILE,
            {
                "source": preview.source,
                "location": preview.location,
                "fetched": details,
                "created_at": time.time(),
            },
        )
    except BaseException:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    return token


@contextmanager
def claim(root: Path, token: str) -> Iterator[Preview]:
    """The preview, for one install: removed if it succeeds, put back if not."""
    folder = _folder(root, token)
    taken = folder.with_name(folder.name + _TAKEN)
    try:
        replace(folder, taken)
    except FileNotFoundError as error:
        raise PreviewExpiredError(f"No preview {token}: preview it again") from error
    try:
        data = json.loads((taken / _FILE).read_text("utf-8"))
        preview = Preview(
            data["source"],
            data["location"],
            Fetched(path=taken / _PLUGIN, **data["fetched"]),
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        shutil.rmtree(taken, ignore_errors=True)
        raise PreviewExpiredError(f"Unreadable preview {token}: {error}") from error
    try:
        yield preview
    except BaseException:
        try:
            replace(taken, folder)
        except OSError as error:  # a file still open, sweep removes it later
            logger.warning("Could not keep preview %s: %s", token, error)
        raise
    shutil.rmtree(taken, ignore_errors=True)


def discard(root: Path, token: str) -> None:
    """The user closed the dialog: not kept until it expires. Never fails."""
    try:
        folder = _folder(root, token)
    except PreviewExpiredError:
        return
    with suppress(OSError):  # gone already, or busy until sweep removes it
        retry_busy(lambda: shutil.rmtree(folder))


def sweep(root: Path, keep: int = MAX_PREVIEWS, taken: bool = False) -> None:
    """Drop previews past ``MAX_AGE_SECONDS`` or beyond ``keep``, and ``taken`` ones."""
    folder = root / PREVIEWS_DIR
    if not folder.is_dir():
        return
    previews = []
    for entry in folder.iterdir():
        if entry.name.endswith(_TAKEN):
            if taken:
                shutil.rmtree(entry, ignore_errors=True)
            continue
        try:
            previews.append((_created(entry), entry))
        except OSError:
            continue
    previews.sort(reverse=True)
    cutoff = time.time() - MAX_AGE_SECONDS
    for index, (created, entry) in enumerate(previews):
        if index >= keep or created < cutoff:
            shutil.rmtree(entry, ignore_errors=True)

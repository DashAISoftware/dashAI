import hashlib
import os
import shutil
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Iterator, Optional, Union

from DashAI.back.plugins.sources.base import (
    Fetched,
    SourceError,
    TrustLevel,
    TrustTier,
    check_size,
)

# Uploaded by hand. Nothing ties it to an author or a public repo.
LOCAL = TrustLevel("local", TrustTier.LOCAL)
# Unrecorded origin (no .source) or a level no source declares
UNKNOWN = TrustLevel("unknown", TrustTier.UNKNOWN)


class LocalSourceError(SourceError):
    """A local plugin folder or .zip could not be read."""


def _resolve_plugin_root(tmp: Path) -> Path:
    """``tmp`` or its only real subfolder holding the manifest (a zipped folder)."""
    if (tmp / "manifest.json").is_file():
        return tmp
    dirs = [
        child
        for child in tmp.iterdir()
        if child.is_dir() and not child.name.startswith((".", "__MACOSX"))
    ]
    if len(dirs) == 1 and (dirs[0] / "manifest.json").is_file():
        return dirs[0]
    return tmp


@contextmanager
def _extract_zip(zip_file: Union[Path, BinaryIO]) -> Iterator[Path]:
    """Extract to a temp dir (removed after); yield the plugin root."""
    tmp = Path(tempfile.mkdtemp(prefix="dashai-plugin-zip-"))
    try:
        try:
            with zipfile.ZipFile(zip_file) as archive:
                for member in archive.namelist():
                    normalized = os.path.normpath(member)
                    if normalized.startswith("..") or os.path.isabs(normalized):
                        raise LocalSourceError(
                            f"Unsafe path in zip: {member}", "unsafe_zip"
                        )
                check_size(
                    sum(info.file_size for info in archive.infolist()),
                    "The extracted zip",
                )
                archive.extractall(tmp)
        except zipfile.BadZipFile as error:
            raise LocalSourceError(
                f"Invalid zip file: {error}", "invalid_zip"
            ) from error
        yield _resolve_plugin_root(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _no_remote(location: str, *_args, **_kwargs) -> None:
    raise LocalSourceError(
        f"A local plugin has no remote origin: {location}", "invalid_location"
    )


def _fetched(path: Path, sha256: Optional[str]) -> Fetched:
    return Fetched(path, None, LOCAL.name, False, sha256, None)


class LocalSource:
    """A plugin from a local folder or ``.zip`` file."""

    can_update = False  # updated by uploading the new version
    trust_levels = (LOCAL, UNKNOWN)
    fetch_listed = key = latest_tag = web_url = readme_base = owner = official = (
        staticmethod(_no_remote)
    )

    @contextmanager
    def fetch(self, location: str, ref: Optional[str] = None) -> Iterator[Fetched]:
        path = Path(location)
        if path.is_dir():
            yield _fetched(path, None)
        elif path.is_file() and path.suffix.lower() == ".zip":
            sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
            with _extract_zip(path) as extracted:
                yield _fetched(extracted, sha256)
        else:
            raise LocalSourceError(
                f"Plugin folder or .zip not found: {location}", "file_not_found"
            )

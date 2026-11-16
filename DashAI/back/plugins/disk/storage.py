import json
import os
import shutil
import stat
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from beartype import beartype
from beartype.typing import List, NamedTuple, Optional, Union
from pydantic import TypeAdapter

from DashAI.back.plugins.disk.trash import Trash, replace, staging_folder
from DashAI.back.plugins.manifest.manifest import PLUGIN_ID
from DashAI.back.plugins.sources.local_source import UNKNOWN

_README_CHARS = 100_000


def plugins_root(local_path: os.PathLike) -> Path:
    """``<local_path>/plugins``, with installed plugins, dependencies and markers."""
    return Path(local_path).expanduser().absolute() / "plugins"


def read_readme(folder: Path) -> Optional[str]:
    """A plugin's ``README.md``, capped, or None if absent or unreadable."""
    path = folder / "README.md"
    try:
        found = path.stat()
        if stat.S_ISREG(found.st_mode):
            return _readme(str(path), found.st_ino, found.st_mtime_ns, found.st_size)
    except OSError:
        pass
    return None


@lru_cache(maxsize=4096)
def _readme(path: str, *stamp: int) -> str:
    with open(path, encoding="utf-8", errors="replace") as file:
        return file.read(_README_CHARS)


class Provenance(NamedTuple):
    """Contents of a plugin's ``.source`` marker."""

    source: str
    location: str
    ref: Optional[str] = None  # GitHub tag, None for local
    trust_level: str = UNKNOWN.name  # one of a source's levels (``sources``)
    verified: bool = False  # downloaded from a DashAISoftware repo
    sha256: Optional[str] = None  # of the installed file, None for a folder
    commit: Optional[str] = None  # None for local or an unattested asset
    asset: Optional[str] = None  # the GitHub release file's name
    workflow: Optional[str] = None  # what built it, from an accepted attestation
    signed_at: Optional[str] = None  # of an accepted attestation (ISO, UTC)
    issuer: Optional[str] = None  # who vouched, from an accepted attestation
    # ISO 8601 UTC. First install of this id (kept on updates) and this copy's.
    installed_at: Optional[str] = None
    updated_at: Optional[str] = None


# Strict, because .source sits next to the plugin's code where anyone may edit it.
_PROVENANCE = TypeAdapter(Provenance)


@lru_cache(maxsize=4096)
def _provenance(path: str, *stamp: int) -> Provenance:
    return _PROVENANCE.validate_json(Path(path).read_bytes(), strict=True)


class Blocked(NamedTuple):
    """A ``.blocked`` marker, the retirement date and whether the user allowed it."""

    date: str
    allowed: bool = False


_BLOCKED = TypeAdapter(Blocked)


@dataclass
class StoredPlugin:
    id: str
    path: Path


class PluginStorage:
    MANIFEST_FILENAME = "manifest.json"
    DISABLED_MARKER = ".disabled"
    SOURCE_MARKER = ".source"
    BLOCKED_MARKER = ".blocked"

    @beartype
    def __init__(self, base_path: Union[str, Path]):
        self.base_path = Path(base_path)

    @classmethod
    def at(cls, local_path: os.PathLike) -> "PluginStorage":
        """The plugins installed under ``local_path`` (``~/.DashAI``)."""
        return cls(plugins_root(local_path) / "installed")

    @beartype
    def plugin_dir(self, plugin_id: str) -> Path:
        if not PLUGIN_ID.fullmatch(plugin_id):
            raise ValueError(f"Invalid plugin id: {plugin_id}")
        return self.base_path / plugin_id

    @beartype
    def is_installed(self, plugin_id: str) -> bool:
        return (self.plugin_dir(plugin_id) / self.MANIFEST_FILENAME).is_file()

    @beartype
    def list_installed(self) -> List[str]:
        if not self.base_path.is_dir():
            return []
        return [
            entry.name
            for entry in self.base_path.iterdir()
            if PLUGIN_ID.fullmatch(entry.name)
            and (entry / self.MANIFEST_FILENAME).is_file()
        ]

    @property
    def root(self) -> Path:
        """``~/.DashAI/plugins``."""
        return self.base_path.parent

    @beartype
    def save(
        self,
        plugin_id: str,
        source_dir: Union[str, Path],
        provenance: Provenance,
        trash: Trash,
        disabled: bool = False,
        blocked: Optional[Blocked] = None,
    ) -> StoredPlugin:
        """Copy to staging, then swap in, trashing the old copy."""
        dest = self.plugin_dir(plugin_id)
        staging = staging_folder(self.root)
        try:
            staged = staging / plugin_id
            # The markers are dashAI's to write, never the author's.
            shutil.copytree(
                source_dir,
                staged,
                ignore=shutil.ignore_patterns(
                    self.SOURCE_MARKER, self.DISABLED_MARKER, self.BLOCKED_MARKER
                ),
                symlinks=True,  # as links, one to a parent folder would loop
            )
            (staged / self.SOURCE_MARKER).write_text(
                json.dumps(provenance._asdict()), encoding="utf-8"
            )
            if disabled:
                (staged / self.DISABLED_MARKER).touch()
            if blocked is not None:
                (staged / self.BLOCKED_MARKER).write_text(
                    json.dumps(blocked._asdict()), encoding="utf-8"
                )
            if dest.exists():
                trash.move(dest)
            trash.add(dest)  # after the move, so undoing never removes the old
            dest.parent.mkdir(parents=True, exist_ok=True)
            replace(staged, dest)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        return StoredPlugin(id=plugin_id, path=dest)

    @beartype
    def remove(self, plugin_id: str) -> None:
        dest = self.plugin_dir(plugin_id)
        if not (dest / self.MANIFEST_FILENAME).is_file():
            raise FileNotFoundError(f"Plugin not installed: {plugin_id}")
        trash = Trash(self.root)
        trash.move(dest)
        trash.commit()

    @beartype
    def read_source(self, plugin_id: str) -> Optional[Provenance]:
        """The ``.source`` marker or None, ``ValueError`` if malformed."""
        marker = self.plugin_dir(plugin_id) / self.SOURCE_MARKER
        try:
            found = marker.stat()
        except OSError:
            return None
        if not stat.S_ISREG(found.st_mode):
            return None
        return _provenance(str(marker), found.st_ino, found.st_mtime_ns, found.st_size)

    @beartype
    def is_enabled(self, plugin_id: str) -> bool:
        return not (self.plugin_dir(plugin_id) / self.DISABLED_MARKER).exists()

    @beartype
    def set_enabled(self, plugin_id: str, enabled: bool) -> None:
        marker = self.plugin_dir(plugin_id) / self.DISABLED_MARKER
        if enabled:
            marker.unlink(missing_ok=True)
        else:
            marker.touch()

    @beartype
    def read_blocked(self, plugin_id: str) -> Optional[Blocked]:
        """The ``.blocked`` marker or None, an unreadable one blocks."""
        marker = self.plugin_dir(plugin_id) / self.BLOCKED_MARKER
        if not marker.is_file():
            return None
        try:
            return _BLOCKED.validate_json(marker.read_bytes(), strict=True)
        except (OSError, ValueError):
            return Blocked(date="")

    @beartype
    def is_blocked(self, plugin_id: str) -> bool:
        blocked = self.read_blocked(plugin_id)
        return blocked is not None and not blocked.allowed

    @beartype
    def set_blocked(self, plugin_id: str, blocked: Optional[Blocked]) -> None:
        marker = self.plugin_dir(plugin_id) / self.BLOCKED_MARKER
        if blocked is None:
            marker.unlink(missing_ok=True)
        else:
            marker.write_text(json.dumps(blocked._asdict()), encoding="utf-8")

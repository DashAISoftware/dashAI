"""Move instead of delete (Windows can't delete a loaded .pyd), journaled."""

import json
import logging
import os
import shutil
import stat
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Tuple, TypeVar

import psutil
from pydantic import BaseModel

TRASH_DIR = ".trash"
STAGING_DIR = ".staging"
OPERATION_MARKER = ".operation"
# Touched when dependencies change, then the job queue restarts its worker.
WORKER_RESTART_MARKER = ".worker-restart"
_JOURNAL = "journal.json"
# With the pid it identifies this process, as pids get reused.
_STARTED = psutil.Process().create_time()
# Windows can't move a file another process holds open, briefly (worker, antivirus)
_RETRY_DELAYS = (0.05, 0.1, 0.2, 0.4, 0.8)

logger = logging.getLogger(__name__)
T = TypeVar("T")


def retry_busy(call: Callable[[], T]) -> T:
    """``call()``, retried while a file it touches is briefly busy (Windows)."""
    for delay in (*_RETRY_DELAYS, None):
        try:
            return call()
        except PermissionError:
            if delay is None:
                raise
            time.sleep(delay)


def replace(source: Path, target: Path) -> None:
    """``os.replace``, retried while the file is briefly busy."""
    retry_busy(lambda: os.replace(source, target))


def hide(path: Path) -> None:
    """Hide a dotted ``path`` on Windows too, then write it via ``write_json``."""
    if os.name != "nt":
        return
    import ctypes

    try:
        attributes = path.stat().st_file_attributes
    except OSError:
        return
    ctypes.windll.kernel32.SetFileAttributesW(
        str(path), attributes | stat.FILE_ATTRIBUTE_HIDDEN
    )


def hidden_folder(folder: Path) -> Path:
    """Create ``folder``, hidden."""
    folder.mkdir(parents=True, exist_ok=True)
    hide(folder)
    return folder


def write_json(path: Path, data) -> None:
    write_file(path, json.dumps(data).encode())


def write_file(path: Path, data: bytes) -> None:
    """Old or new content after a crash, a dotted name hidden on Windows too."""
    temporary = path.with_name(path.name + ".tmp")
    with open(temporary, "wb") as file:
        file.write(data)
        file.flush()
        os.fsync(file.fileno())
    replace(temporary, path)
    if path.name.startswith("."):
        hide(path)  # the replace gave it the temporary's attributes


class _Journal(BaseModel):
    """A journal as ``recover`` reads it."""

    pid: Optional[int] = None
    started: Optional[float] = None
    committed: bool = True  # none, so nothing to put back
    moved: List[Tuple[str, str]] = []
    added: List[str] = []


class Trash:
    """What one operation moved out of the way or added."""

    def __init__(self, root: Path, disposable: bool = False):
        self.root = Path(root)
        self.folder = self.root / TRASH_DIR / uuid.uuid4().hex
        self._moved: List[Tuple[Path, Path]] = []
        self.added: List[Path] = []
        self._committed = disposable

    def _write(self) -> None:
        hidden_folder(self.folder.parent)
        self.folder.mkdir(exist_ok=True)
        write_json(
            self.folder / _JOURNAL,
            {
                "pid": os.getpid(),
                "started": _STARTED,
                "committed": self._committed,
                "moved": [[str(o), str(t)] for o, t in self._moved],
                "added": [str(path) for path in self.added],
            },
        )

    def move(self, *paths: Path) -> None:
        """Move files or folders (under the plugins root) here; one journal write."""
        root = self.root.resolve()
        pairs = [
            (Path(p), self.folder / Path(p).resolve().relative_to(root)) for p in paths
        ]
        self._moved.extend(pairs)
        self._write()
        for path, target in pairs:
            target.parent.mkdir(parents=True, exist_ok=True)
            replace(path, target)

    def add(self, *paths: Path) -> None:
        """Journal files the operation is about to put in place."""
        self.added.extend(Path(path) for path in paths)
        self._write()

    def commit(self) -> None:
        """Keep the change: nothing is put back from now on."""
        self._committed = True
        self._write()
        self.empty()

    def restore(self) -> None:
        for original, trashed in reversed(self._moved):
            if trashed.exists():  # a failed move leaves the rest unmoved
                original.parent.mkdir(parents=True, exist_ok=True)
                replace(trashed, original)
        self._moved.clear()
        self.empty()

    def empty(self) -> None:
        shutil.rmtree(self.folder, ignore_errors=True)


def staging_folder(root: Path) -> Path:
    folder = hidden_folder(Path(root) / STAGING_DIR) / uuid.uuid4().hex
    folder.mkdir()
    return folder


def _remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)


def _remove_empty_parents(path: Path, root: Path) -> None:
    """Remove ``path``'s folders left empty, below the first level of ``root``."""
    root, parent = root.resolve(), path.parent.resolve()
    while parent.parent != root and root in parent.parents:
        try:
            parent.rmdir()
        except OSError:
            return
        parent = parent.parent


def _alive(record: dict) -> bool:
    """Whether the process that wrote ``record`` (pid + start time) still runs."""
    pid = record.get("pid")
    if not isinstance(pid, int):
        return False
    try:
        return psutil.Process(pid).create_time() == record.get("started")
    except psutil.Error:  # gone, or a process we may not inspect
        return False


def _running_elsewhere(journal: dict) -> bool:
    """Whether the dashAI that wrote ``journal`` is another, still running."""
    return journal.get("pid") != os.getpid() and _alive(journal)


class OperationBusyError(Exception):
    """Another dashAI is changing plugins."""


# How many times this process holds each marker (by path).
_held: Dict[str, int] = {}
_held_lock = threading.Lock()


def _operation_holder(root: Path) -> dict:
    try:
        holder = json.loads((Path(root) / OPERATION_MARKER).read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    return holder if isinstance(holder, dict) else {}


@contextmanager
def operation(root: Path) -> Iterator[None]:
    """Held while plugins change (jobs wait, another dashAI is refused), reentrant."""
    marker = Path(root) / OPERATION_MARKER
    key = str(marker.resolve())
    with _held_lock:
        if not _held.get(key):
            if _running_elsewhere(_operation_holder(root)):
                raise OperationBusyError(
                    "Another dashAI is changing plugins; try again when it finishes"
                )
            # Check-then-write races two simultaneous starts, O_EXCL would fix it
            marker.parent.mkdir(parents=True, exist_ok=True)
            write_json(marker, {"pid": os.getpid(), "started": _STARTED})
        _held[key] = _held.get(key, 0) + 1
    try:
        yield
    finally:
        with _held_lock:
            _held[key] -= 1
            if not _held[key]:
                # Kept empty as the queue may read it, empty means unheld
                write_json(marker, {})


def operation_running(root: Path) -> bool:
    """Whether a plugin operation (of any process) is in progress."""
    return _alive(_operation_holder(root))


def recover(root: Path) -> bool:
    """Undo uncommitted operations, empty trash and staging. True if none pended."""
    done = True
    for folder in sorted((Path(root) / TRASH_DIR).glob("*")):
        try:
            journal = _Journal.model_validate_json(
                (folder / _JOURNAL).read_bytes()
            ).model_dump()
        except (OSError, ValueError):  # none, or not one, so nothing to put back
            journal = _Journal().model_dump()
        if _running_elsewhere(journal):
            done = False
            continue
        try:
            if not journal["committed"]:
                for path in reversed(journal["added"]):
                    _remove(Path(path))
                    _remove_empty_parents(Path(path), Path(root))
                for original, trashed in reversed(journal["moved"]):
                    if Path(trashed).exists():
                        _remove(Path(original))
                        Path(original).parent.mkdir(parents=True, exist_ok=True)
                        replace(trashed, original)
        except OSError as error:  # still locked, kept for the next start
            logger.warning("Could not undo the operation in %s: %s", folder, error)
            done = False
            continue
        shutil.rmtree(folder, ignore_errors=True)
    for child in (Path(root) / STAGING_DIR).glob("*"):
        shutil.rmtree(child, ignore_errors=True)
    return done

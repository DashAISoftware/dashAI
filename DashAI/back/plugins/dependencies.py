"""Plugins' pip dependencies, per Python in ``plugins/py3.xx``, never dashAI's env."""

import importlib
import importlib.metadata
import json
import logging
import os
import shutil
import site
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path, PurePosixPath

import httpx
from beartype import beartype
from beartype.typing import Callable, Dict, Iterable, List, Optional, Set, Tuple
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version
from pydantic import BaseModel

from DashAI.back.plugins.disk.storage import plugins_root as local_plugins_root
from DashAI.back.plugins.disk.trash import Trash, replace, staging_folder, write_json
from DashAI.back.plugins.errors import CodedError
from DashAI.back.plugins.installer import (
    PIP_TIMEOUT_SECONDS,
    pip_command,
    pip_environment,
)
from DashAI.back.plugins.installer import PluginInstallError as PipInstallError

logger = logging.getLogger(__name__)

LEDGER_FILENAME = ".dashai-plugin-manifest-deps.json"


def dependencies_directory(plugins_root: Path) -> Path:
    """``<plugins_root>/py<major>.<minor>``, this Python's (not created)."""
    return plugins_root / f"py{sys.version_info.major}.{sys.version_info.minor}"


def other_python_directories(plugins_root: Path) -> List[Path]:
    """The dependency folders of the other Pythons sharing ``plugins_root``."""
    current = dependencies_directory(plugins_root)
    return [
        folder
        for folder in plugins_root.glob("py3.*")
        if folder != current and folder.is_dir()
    ]


def activate_dependencies(plugins_root: Path) -> Path:
    """Create this Python's folder, appended to ``sys.path`` so dashAI wins."""
    directory = dependencies_directory(plugins_root)
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        logger.exception("Could not create the plugins directory %s", directory)
        return directory

    if str(directory) not in sys.path:
        site.addsitedir(str(directory))
    importlib.invalidate_caches()  # finds what was installed since
    return directory


class Ledger(BaseModel):
    plugins: Dict[str, List[str]] = {}  # id -> the distributions it needs
    # Set while pruning, so an interrupted prune is retried at startup
    pending: List[str] = []


@dataclass
class Resolution:
    ok: bool
    explanation: str
    # Each with name, version and url
    distributions: List[Dict[str, str]] = field(default_factory=list)


class DependencyError(CodedError):
    """Dependencies could not be resolved or installed."""

    code = "dependency_install_failed"


def _requirements(specs: Iterable[str]) -> List[Requirement]:
    parsed = []
    for spec in specs:
        try:
            parsed.append(Requirement(spec))
        except InvalidRequirement:
            logger.warning("Ignoring invalid requirement %r", spec)
    return parsed


def _applies(requirement: Requirement) -> bool:
    """Its marker holds here, with no extra requested."""
    return requirement.marker is None or requirement.marker.evaluate({"extra": ""})


def constraint_lines(specs: Iterable[str]) -> List[str]:
    """``name + specifier (+ marker)``: pip rejects extras and URLs here."""
    lines = []
    for requirement in _requirements(specs):
        if requirement.url or not str(requirement.specifier):
            continue
        line = f"{canonicalize_name(requirement.name)}{requirement.specifier}"
        if requirement.marker is not None:
            line += f"; {requirement.marker}"
        lines.append(line)
    return lines


def unmet_requirements(
    specs: Iterable[str], plugins_dir: Path
) -> Tuple[List[str], List[str]]:
    """Unmet requirements as ``(missing, conflicts with what dashAI ships)``."""
    missing, conflicts, seen = [], [], set()
    try:
        stamp = (str(plugins_dir), plugins_dir.stat().st_mtime_ns)
    except OSError:
        stamp = (str(plugins_dir), None)
    stack = list(filter(_applies, _requirements(specs)))
    while stack:
        requirement = stack.pop()
        key = (canonicalize_name(requirement.name), frozenset(requirement.extras))
        if key in seen:
            continue
        seen.add(key)
        found = _distribution(key[0], stamp)
        if found is None:
            missing.append(f"{requirement} (not installed)")
            continue
        dist, version = found
        try:
            compatible = requirement.specifier.contains(
                Version(version), prereleases=True
            )
        except InvalidVersion:
            compatible = True
        if not compatible:
            ours = Path(dist.locate_file("")).resolve() == plugins_dir.resolve()
            (missing if ours else conflicts).append(f"{requirement} (found {version})")
            continue
        if requirement.extras:
            stack.extend(_extra_requirements(dist, requirement.extras))
    return missing, conflicts


@lru_cache(maxsize=4096)
def _distribution(
    name: str, stamp: Tuple[str, Optional[int]]
) -> Optional[Tuple[importlib.metadata.Distribution, str]]:
    try:
        found = importlib.metadata.distribution(name)
    except importlib.metadata.PackageNotFoundError:
        return None
    return found, found.version


def _extra_requirements(
    dist: importlib.metadata.Distribution, extras: Iterable[str]
) -> List[Requirement]:
    """What only ``extras`` add to ``dist`` (``datasets[mesh]``: trimesh)."""
    added = []
    for child in _requirements(dist.requires or []):
        marker = child.marker
        if marker is None or marker.evaluate({"extra": ""}):
            continue  # comes with the package itself
        if any(marker.evaluate({"extra": extra}) for extra in extras):
            child.marker = None
            added.append(child)
    return added


def _index_reachable() -> bool:
    """Whether pip's package index answers within 5 s."""
    if os.environ.get("PIP_NO_INDEX"):  # pip only reads local wheels (find-links)
        return True
    # An index set only in pip.conf is not read, so PyPI is probed then.
    url = os.environ.get("PIP_INDEX_URL") or "https://pypi.org/simple/"
    try:
        httpx.head(url, timeout=5, follow_redirects=True)
    except (httpx.HTTPError, httpx.InvalidURL):  # e.g. a mistyped PIP_INDEX_URL
        return False
    return True


def _find_distribution_directory(directory: Path, distribution: str) -> Optional[Path]:
    """``.dist-info`` of ``distribution`` (canonical name) in ``directory``."""
    for candidate in directory.glob("*.dist-info"):
        name = candidate.name[: -len(".dist-info")].rsplit("-", 1)[0]
        if canonicalize_name(name) == distribution:
            return candidate
    return None


def _prune_empty_directories(root: Path, leaf: Path) -> None:
    """Remove ``leaf``'s ``__pycache__`` and the empty folders up to ``root``."""
    cache = leaf / "__pycache__"
    if cache.is_dir():
        shutil.rmtree(cache, ignore_errors=True)

    candidate = leaf
    while candidate != root and root in candidate.parents:
        if not candidate.is_dir() or any(candidate.iterdir()):
            return
        candidate.rmdir()
        candidate = candidate.parent


def _resolve_record_entry(directory: Path, relative: str) -> Optional[Path]:
    """A ``RECORD`` entry under ``directory`` (``--target`` nests ``..``), or None."""
    parts = [
        part
        for part in PurePosixPath(relative.replace("\\", "/")).parts
        if part not in ("..", ".", "")
    ]
    if not parts:
        return None
    target = directory.joinpath(*parts).resolve()
    if directory.resolve() not in target.parents:
        return None
    return target


class PluginDependencies:
    @beartype
    def __init__(
        self,
        local_path: os.PathLike,
        runner=subprocess.run,
        index_reachable: Callable[[], bool] = _index_reachable,
    ):
        self._directory = activate_dependencies(local_plugins_root(local_path))
        self.runner = runner
        self.index_reachable = index_reachable
        self._lock_lines: Optional[List[str]] = None

    def directory(self) -> Path:
        """Created and on ``sys.path``."""
        return self._directory

    def _run_pip(self, arguments: List[str]) -> None:
        """Raise ``DependencyError`` with pip's output if it fails."""
        try:
            command = [*pip_command(), *arguments]
        except PipInstallError as error:
            raise DependencyError(str(error), error.code) from error
        try:
            result = self.runner(
                command,
                capture_output=True,
                text=True,
                # With the plugins dir on PYTHONPATH pip keeps what still fits.
                env=pip_environment(self.directory()),
                timeout=PIP_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as error:
            raise DependencyError(
                f"pip did not finish within {PIP_TIMEOUT_SECONDS // 60} minutes"
            ) from error
        if result.returncode != 0:
            output = (result.stdout or "") + "\n" + (result.stderr or "")
            raise DependencyError(output.strip())

    def _dashai_lock(self, directory: Path) -> List[str]:
        """``name==version`` of everything importable outside ``directory``."""
        if self._lock_lines is not None:
            return self._lock_lines
        try:
            plugins_dir = directory.resolve()
        except OSError:
            plugins_dir = directory

        search_path = []
        for entry in sys.path:
            if not entry:
                continue
            try:
                if Path(entry).resolve() == plugins_dir:
                    continue
            except OSError:
                pass
            search_path.append(entry)

        lines = []
        for dist in importlib.metadata.distributions(path=search_path):
            try:
                name = dist.metadata["Name"]
                version = dist.version
            except Exception:
                continue
            if not name or not version:
                continue
            lines.append(f"{canonicalize_name(name)}=={version}")
        self._lock_lines = lines
        return lines

    @contextmanager
    def _constraints(self, directory: Path, other_dependencies: List[str]):
        lines = self._dashai_lock(directory) + constraint_lines(other_dependencies)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as handle:
            handle.write("\n".join(lines))
            path = handle.name
        try:
            yield path
        finally:
            Path(path).unlink(missing_ok=True)

    def _dry_run(
        self, dependencies: List[str], constraint_file: str
    ) -> List[Dict[str, str]]:
        with tempfile.TemporaryDirectory() as workdir:
            report_path = Path(workdir) / "report.json"
            self._run_pip(
                [
                    "install",
                    "--dry-run",
                    "--quiet",
                    "--disable-pip-version-check",
                    "--constraint",
                    constraint_file,
                    "--report",
                    str(report_path),
                    "--",
                    *dependencies,
                ]
            )
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                raise DependencyError(
                    f"Could not read the pip resolution report: {error}"
                ) from error

        distributions = []
        for entry in report.get("install", []):
            metadata = entry.get("metadata") or {}
            url = (entry.get("download_info") or {}).get("url")
            if not metadata.get("name") or not url:
                continue
            distributions.append(
                {
                    "name": canonicalize_name(metadata["name"]),
                    "version": metadata.get("version", ""),
                    "url": url,
                }
            )
        return distributions

    @beartype
    def resolve(
        self, dependencies: List[str], other_dependencies: List[str] | None = None
    ) -> Resolution:
        """What installing would take; ``other_dependencies`` must stay satisfied."""
        if not dependencies:
            return Resolution(ok=True, explanation="")
        directory = self.directory()
        with self._constraints(directory, other_dependencies or []) as constraints:
            try:
                distributions = self._dry_run(dependencies, constraints)
            except DependencyError as error:
                return Resolution(ok=False, explanation=str(error))
        return Resolution(ok=True, explanation="", distributions=distributions)

    def installed(self) -> Dict[str, importlib.metadata.Distribution]:
        """Distributions in the plugins directory, by canonical name."""
        found = {}
        for dist in importlib.metadata.distributions(path=[str(self.directory())]):
            name = dist.metadata["Name"]
            if name:
                found[canonicalize_name(name)] = dist
        return found

    @beartype
    def closure(self, dependencies: List[str]) -> Set[str]:
        """What ``dependencies`` need from the plugins folder, beyond dashAI."""
        if not dependencies:
            return set()
        available = self.installed()
        provided = {
            line.split("==", 1)[0] for line in self._dashai_lock(self.directory())
        }
        needed: Set[str] = set()
        seen = set()
        stack = _requirements(dependencies)
        while stack:
            requirement = stack.pop()
            if not _applies(requirement):
                continue
            name = canonicalize_name(requirement.name)
            key = (name, frozenset(requirement.extras))
            if key in seen:
                continue
            seen.add(key)
            if name in provided:
                if requirement.extras:
                    dist = importlib.metadata.distribution(requirement.name)
                    stack.extend(_extra_requirements(dist, requirement.extras))
                continue
            if name not in available:
                continue
            needed.add(name)
            environments = [{"extra": extra} for extra in requirement.extras] or [
                {"extra": ""}
            ]
            for child in _requirements(available[name].requires or []):
                if child.marker is not None:
                    if not any(child.marker.evaluate(env) for env in environments):
                        continue
                    child.marker = None
                stack.append(child)
        return needed

    def top_level_modules(self, names: Iterable[str]) -> Set[str]:
        """Importable top-level names the given distributions provide."""
        directory = self.directory()
        modules = set()
        for name in names:
            dist_info = _find_distribution_directory(directory, canonicalize_name(name))
            record = dist_info / "RECORD" if dist_info is not None else None
            if record is None or not record.exists():
                continue
            for line in record.read_text(encoding="utf-8").splitlines():
                first = line.split(",", 1)[0].strip().replace("\\", "/").split("/")[0]
                if (
                    not first
                    or first.startswith(".")
                    or first.endswith((".dist-info", ".data"))
                ):
                    continue
                if first.endswith(".py"):
                    modules.add(first[: -len(".py")])
                elif "." not in first and first not in ("bin", "__pycache__"):
                    modules.add(first)
                elif first.endswith((".pyd", ".so")):
                    modules.add(first.split(".", 1)[0])
        return modules

    def transaction(self) -> "DependencyTransaction":
        return DependencyTransaction(self)

    def read_ledger(self) -> Ledger:
        path = self.directory() / LEDGER_FILENAME
        try:
            return Ledger.model_validate_json(path.read_bytes())
        except FileNotFoundError:
            return Ledger()
        except (OSError, ValueError) as error:  # also not a ledger
            logger.warning("Unreadable plugin dependency ledger %s: %s", path, error)
            return Ledger()

    def _write_ledger(self, ledger: Ledger) -> None:
        try:
            write_json(self.directory() / LEDGER_FILENAME, ledger.model_dump())
        except OSError as error:
            logger.warning("Could not write the plugin dependency ledger: %s", error)

    def record(
        self, owner: str, names: Iterable[str], pending: Iterable[str] = ()
    ) -> None:
        """What ``owner`` needs, and the orphans its change leaves to prune."""
        ledger = self.read_ledger()
        ledger.plugins[owner] = sorted(names)
        ledger.pending = sorted({*ledger.pending, *pending})
        self._write_ledger(ledger)

    def forget(self, owner: str, pending: Iterable[str] = ()) -> None:
        ledger = self.read_ledger()
        known = ledger.plugins.pop(owner, None) is not None
        if known or pending:
            ledger.pending = sorted({*ledger.pending, *pending})
            self._write_ledger(ledger)

    def settle(self, names: Iterable[str]) -> None:
        """A prune of ``names`` finished: none of them is pending any more."""
        ledger = self.read_ledger()
        if set(names) & set(ledger.pending):
            ledger.pending = sorted(set(ledger.pending) - set(names))
            self._write_ledger(ledger)

    def rebuild_ledger(
        self, dependencies_by_plugin: Dict[str, List[str]], pending: Iterable[str] = ()
    ) -> None:
        """From the manifests; what is pending stays, and ``pending`` joins it."""
        ledger = self.read_ledger()
        ledger.plugins = {
            owner: sorted(self.closure(dependencies))
            for owner, dependencies in dependencies_by_plugin.items()
        }
        ledger.pending = sorted({*ledger.pending, *pending})
        self._write_ledger(ledger)


def _refuse_overwriting_others(
    files: Dict[Path, Path],
    present: Dict[str, importlib.metadata.Distribution],
    names: Set[str],
) -> None:
    """Refuse a file at a path another distribution ships differently (.pyc aside)."""
    existing = {
        destination.resolve()
        for source, destination in files.items()
        if destination.suffix != ".pyc"
        and destination.exists()
        and destination.read_bytes() != source.read_bytes()
    }
    if not existing:
        return
    for name, distribution in present.items():
        if name in names:
            continue  # being replaced by its new version
        owned = {
            Path(distribution.locate_file(f)).resolve()
            for f in distribution.files or []
        }
        if owned & existing:
            raise DependencyError(
                f"{', '.join(sorted(names))} would overwrite files of {name}, "
                "which is installed for another plugin",
                "overwrites_other_package",
                packages=sorted(names),
                other=name,
            )


class DependencyTransaction:
    """Installs and removals that ``rollback`` undoes; ``commit`` empties the trash."""

    def __init__(self, dependencies: PluginDependencies):
        self._dependencies = dependencies
        self.directory = dependencies.directory()
        self.root = self.directory.parent
        self.trash = Trash(self.root)
        self.installed: List[str] = []
        self.removed: List[str] = []

    @property
    def changed(self) -> bool:
        return bool(self.installed or self.removed)

    def install(self, distributions: List[Dict[str, str]]) -> None:
        if not distributions:
            return
        staging = staging_folder(self.root)
        try:
            self._dependencies._run_pip(
                [
                    "install",
                    "--no-cache-dir",
                    "--disable-pip-version-check",
                    "--no-deps",
                    "--target",
                    str(staging),
                    "--",
                    *[distribution["url"] for distribution in distributions],
                ]
            )
            files = {
                source: self.directory / source.relative_to(staging)
                for source in sorted(p for p in staging.rglob("*") if p.is_file())
            }
            present = self._dependencies.installed()
            names = {distribution["name"] for distribution in distributions}
            _refuse_overwriting_others(files, present, names)
            for name in sorted(names & set(present)):
                self._remove_one(name)
            self.trash.move(*(d for d in files.values() if d.exists()))
            self.trash.add(*files.values())
            for source, destination in files.items():
                destination.parent.mkdir(parents=True, exist_ok=True)
                replace(source, destination)
            self.installed.extend(d["name"] for d in distributions)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
            importlib.invalidate_caches()

    def remove(self, names: Iterable[str]) -> None:
        for name in sorted(names):
            if self._remove_one(canonicalize_name(name)):
                self.removed.append(canonicalize_name(name))
        importlib.invalidate_caches()

    def _remove_one(self, name: str) -> bool:
        dist_info = _find_distribution_directory(self.directory, name)
        if dist_info is None:
            return False
        root = self.directory.resolve()
        dist_info_resolved = dist_info.resolve()
        files = set()
        record = dist_info / "RECORD"
        if record.exists():
            for line in record.read_text(encoding="utf-8").splitlines():
                relative = line.split(",", 1)[0].strip()
                target = (
                    _resolve_record_entry(self.directory, relative)
                    if relative
                    else None
                )
                if (
                    target is not None
                    and target.is_file()
                    and dist_info_resolved not in target.parents
                ):
                    files.add(target)
        # A file another distribution also ships stays
        files -= {
            Path(dist.locate_file(f)).resolve()
            for other, dist in self._dependencies.installed().items()
            if other != name
            for f in dist.files or []
        }
        self.trash.move(*sorted(files), dist_info)
        touched = {path.parent for path in files}
        for leaf in sorted(touched, key=lambda path: len(path.parts), reverse=True):
            _prune_empty_directories(root, leaf)
        return True

    def rollback(self) -> None:
        added = self.trash.added
        # Moved aside as the new files may be loaded and locked
        discard = Trash(self.root, disposable=True)
        discard.move(*(path for path in added if path.exists()))
        root = self.directory.resolve()
        for path in added:
            _prune_empty_directories(root, path.resolve().parent)
        self.trash.restore()
        discard.empty()
        importlib.invalidate_caches()

    def commit(self) -> None:
        self.trash.commit()

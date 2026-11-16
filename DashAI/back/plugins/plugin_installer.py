import contextlib
import functools
import logging
import subprocess
import sys
import threading
import time
from contextlib import AbstractContextManager, contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from beartype import beartype
from beartype.typing import (
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)
from packaging.version import Version

from DashAI.back.core.enums.plugin_source import PluginSource
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.plugins import bootstrap
from DashAI.back.plugins.dependencies import (
    DependencyError,
    PluginDependencies,
    other_python_directories,
)
from DashAI.back.plugins.disk import previews
from DashAI.back.plugins.disk.previews import Preview, PreviewExpiredError
from DashAI.back.plugins.disk.storage import (
    Blocked,
    PluginStorage,
    Provenance,
    read_readme,
)
from DashAI.back.plugins.disk.trash import (
    WORKER_RESTART_MARKER,
    OperationBusyError,
    Trash,
    hide,
    operation,
    recover,
)
from DashAI.back.plugins.errors import CodedError, PluginError
from DashAI.back.plugins.installer import PluginInstallError as PipInstallError
from DashAI.back.plugins.installer import python_executable
from DashAI.back.plugins.loader import PluginLoader, PluginLoadError
from DashAI.back.plugins.manifest.manifest import (
    ManifestError,
    PluginManifest,
    in_range,
)
from DashAI.back.plugins.manifest.validator import PluginValidator, ValidationResult
from DashAI.back.plugins.sources import default_sources, needs_ack, trust_level
from DashAI.back.plugins.sources.base import (
    PluginSourceHandler,
    RateLimitError,
    SourceError,
)
from DashAI.back.plugins.sources.local_source import UNKNOWN
from DashAI.back.plugins.store.store import (
    PluginStore,
    StoreEntry,
    StoreIndex,
    StoreRelease,
    listed_release,
    offered_release,
    origin_key,
    removed_entry,
    revoked_release,
    store_entry,
)

logger = logging.getLogger(__name__)

# The check imports dashAI, which is slow.
_LOAD_CHECK_TIMEOUT_SECONDS = 10 * 60

BUSY_MESSAGE = "A job is running. Try again when it finishes."

# Inside each py3.xx folder, touched by the dashAI running on that Python.
_LAST_USED = ".last-used"
# Another Python's folder unused this long is removed (dashAI moved on).
_OTHER_PYTHON_SECONDS = 30 * 24 * 60 * 60


@dataclass
class InstalledPlugin:
    id: str
    name: str
    version: str
    path: Path
    components: List[Type]
    ref: Optional[str] = None
    trust_level: str = UNKNOWN.name
    verified: bool = False
    sha256: Optional[str] = None
    commit: Optional[str] = None
    pending_restart: bool = False  # loads here only after reopening dashAI


class PluginInstallError(CodedError):
    """A plugin operation failed; nothing was changed."""

    code = "install_failed"


class PluginBusyError(PluginInstallError):
    """A job is running, or another dashAI is changing plugins (``other_dashai``)."""

    code = "job_running"


class PluginRateLimitError(PluginInstallError):
    """The source (GitHub) refuses more requests for now; nothing was changed."""

    code = "rate_limited"


def _check_listed(
    entry: StoreEntry, release: StoreRelease, manifest: PluginManifest, fetched
) -> None:
    """A listed release is the bytes and manifest the store's bot reviewed."""
    if fetched.sha256 != release.sha256:
        raise PluginInstallError(
            f"Got {fetched.sha256}, not the reviewed {release.sha256}",
            "digest_mismatch",
        )
    got = trust_level(fetched.trust_level).tier
    for field, expected, actual, differs in (
        ("id", entry.id, manifest.id, manifest.id != entry.id),
        (
            "version",
            release.version,
            manifest.version,
            manifest.version != release.version,
        ),
        (
            "trust_level",
            release.trust_level,
            fetched.trust_level,
            got.is_below(trust_level(release.trust_level).tier),
        ),
    ):
        if differs:
            raise PluginInstallError(
                f"The store reviewed {field} {expected}, this is {actual}",
                "store_mismatch",
                field=field,
                expected=expected,
                got=actual,
            )


def _install_errors(method):
    """Turn bad data or disk errors into a ``PluginInstallError``."""

    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except PluginInstallError:
            raise
        except PreviewExpiredError as error:
            raise PluginInstallError(str(error), error.code) from error
        except OperationBusyError as error:
            raise PluginBusyError(str(error), "other_dashai") from error
        except (OSError, ValueError, KeyError) as error:
            raise PluginInstallError(
                f"{type(error).__name__}: {error}", "internal_error"
            ) from error

    return wrapper


def _unavailable(plugin_id: str, problem: str) -> PluginError:
    return PluginError(
        "dependency_unavailable",
        f"Needs the plugin '{plugin_id}', which has a problem: {problem}",
        {"id": plugin_id, "problem": problem},
    )


def _wrong_version(plugin_id: str, spec: str, installed: Optional[str]) -> PluginError:
    return PluginError(
        "plugin_dependency_version",
        f"Needs the plugin '{plugin_id}' {spec}, not {installed or 'in the store'}",
        {"id": plugin_id, "required": spec, "installed": installed},
    )


class PluginInstaller:
    @beartype
    def __init__(
        self,
        storage: PluginStorage,
        registry: ComponentRegistry,
        dependencies: PluginDependencies,
        sources: Optional[Mapping[PluginSource, PluginSourceHandler]] = None,
        jobs_running: Callable[[], bool] = lambda: False,
        load_check: Optional[Callable[[Path], None]] = None,
        store: Optional[PluginStore] = None,
    ):
        self.storage = storage
        self.store = store  # its retired plugins are blocked
        self.registry = registry
        self.dependencies = dependencies
        self.sources = dict(sources or default_sources())
        if set(self.sources) != set(PluginSource):
            raise ValueError("Exactly one source per PluginSource is required")
        self._lock = threading.RLock()  # one plugin operation at a time
        self._jobs_running = jobs_running
        self._load_check = load_check or self._load_in_fresh_process
        # Plugins that only load here after reopening dashAI (not persisted).
        self.pending_restart: Set[str] = set()
        # Distributions replaced or removed after this process imported them.
        self._stale: Set[str] = set()
        # Startup repair failures, apart from load_errors which load retries rewrite
        self.repair_errors: Dict[str, str] = {}

    @beartype
    def _others(self, plugin_id: str) -> Iterator[Tuple[str, Optional[PluginManifest]]]:
        """Every other installed plugin and its manifest (None if unreadable)."""
        for other in self.storage.list_installed():
            if other != plugin_id:
                yield other, self._manifest_or_none(other)

    def _other_dependencies(self, plugin_id: str) -> List[str]:
        """Declared dependencies of every other installed plugin."""
        return [d for _, m in self._others(plugin_id) if m for d in m.dependencies]

    @beartype
    def _needed_by_others(self, plugin_id: str) -> Set[str]:
        """Distributions another installed plugin needs."""
        declared: List[str] = []
        needed: Set[str] = set()
        ledger = self.dependencies.read_ledger().plugins
        for other, manifest in self._others(plugin_id):
            if manifest is not None:
                declared.extend(manifest.dependencies)
            else:  # unreadable manifest, its ledger entry
                needed |= set(ledger.get(other, []))
        return needed | self.dependencies.closure(declared)

    @beartype
    def _owned(self, plugin_id: str, manifest: Optional[PluginManifest]) -> Set[str]:
        if manifest is not None:
            return self.dependencies.closure(manifest.dependencies)
        return set(self.dependencies.read_ledger().plugins.get(plugin_id, []))

    def _ensure_idle(self) -> None:
        """Raise ``PluginBusyError`` if a job runs: it could mix library versions."""
        try:
            running = self._jobs_running()
        except Exception as error:  # noqa: BLE001
            logger.warning("Could not tell whether a job is running: %s", error)
            running = False
        if running:
            raise PluginBusyError(BUSY_MESSAGE)

    def _request_worker_restart(self) -> None:
        marker = self.storage.root / WORKER_RESTART_MARKER
        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.touch()
            hide(marker)
        except OSError as error:
            logger.warning("Could not ask the job worker to restart: %s", error)

    def _imported_here(self, distribution_names: Iterable[str]) -> Set[str]:
        """Those imported by this process (call it while still on disk)."""
        imported = {name.split(".", 1)[0] for name in list(sys.modules)}
        return {
            name
            for name in distribution_names
            if self.dependencies.top_level_modules([name]) & imported
        }

    def _uses_stale(self, manifest: PluginManifest) -> bool:
        return bool(
            self._stale
            and self._stale & self.dependencies.closure(manifest.dependencies)
        )

    def _load_in_fresh_process(self, plugin_dir: Path) -> None:
        """See ``load_check``."""
        try:
            interpreter = python_executable()
        except PipInstallError as error:
            raise PluginInstallError(str(error), error.code) from error
        try:
            result = subprocess.run(
                [
                    interpreter,
                    "-m",
                    "DashAI.back.plugins.load_check",
                    str(plugin_dir),
                    str(self.storage.root.parent),
                ],
                capture_output=True,
                text=True,
                timeout=_LOAD_CHECK_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise PluginInstallError(
                "Load failed: the check timed out", "load_failed"
            ) from error
        if result.returncode == 3:  # a plugin it needs fails to load
            dependency = result.stdout.strip().splitlines()[-1]  # after its prints
            raise PluginInstallError(
                f"Needs the plugin '{dependency}', which fails to load: "
                f"{result.stderr.strip()}",
                "dependency_unavailable",
                id=dependency,
                problem="load_failed",
            )
        if result.returncode != 0:
            reason = (result.stderr or result.stdout or "").strip().splitlines()
            raise PluginInstallError(
                f"Load failed: {reason[-1] if reason else 'unknown error'}",
                "load_failed",
            )

    @beartype
    def startup_maintenance(self) -> None:
        """At startup: undo half-done operations, rebuild the ledger, prune."""
        try:
            with self._lock, operation(self.storage.root):
                # Skipped after a partial undo, locked plugins make deps look orphan
                if recover(self.storage.root):
                    self._maintain_ledger()
                try:
                    self._drop_other_pythons()
                except OSError as error:  # a file of it still open, next start retries
                    logger.warning(
                        "Could not remove another Python's plugins: %s", error
                    )
                previews.sweep(self.storage.root, taken=True)
        # Never stops dashAI from opening (e.g. the marker locked by an antivirus).
        except (OperationBusyError, OSError) as error:
            logger.warning("Skipping plugin maintenance: %s", error)

    def _maintain_ledger(self) -> None:
        read = self.dependencies.read_ledger()
        ledger = read.plugins
        # Finish a pending or skipped prune, only of packages the ledger knows
        candidates = set().union(*ledger.values()) | set(read.pending)
        rebuilt = {}
        for plugin_id in self.storage.list_installed():
            manifest = self._manifest_or_none(plugin_id)
            if manifest is not None:
                rebuilt[plugin_id] = manifest.dependencies
        try:
            self.dependencies.rebuild_ledger(rebuilt, pending=candidates)
            for plugin_id in self.storage.list_installed():
                if plugin_id not in rebuilt and plugin_id in ledger:
                    self.dependencies.record(plugin_id, ledger[plugin_id])
        except Exception as error:  # noqa: BLE001
            logger.warning("Could not rebuild the dependency ledger: %s", error)
        self._prune(candidates, plugin_id="")

    def _drop_other_pythons(self) -> None:
        """Remove another Python's dependencies after 30 days unused."""
        current = self.dependencies.directory()
        (current / _LAST_USED).touch()
        hide(current / _LAST_USED)
        cutoff = time.time() - _OTHER_PYTHON_SECONDS
        unused = []
        for folder in other_python_directories(current.parent):
            marker = folder / _LAST_USED
            if (marker if marker.exists() else folder).stat().st_mtime < cutoff:
                unused.append(folder)
        if unused:
            trash = Trash(self.storage.root, disposable=True)
            trash.move(*unused)
            trash.empty()
            logger.info(
                "Removed another Python's plugin dependencies: %s",
                [folder.name for folder in unused],
            )

    @contextmanager
    def _acquire(
        self,
        source: PluginSource,
        location: str,
        ref: Optional[str] = None,
        recorded_location: Optional[str] = None,
        listed: Optional[Tuple[StoreEntry, StoreRelease]] = None,
    ) -> Iterator[Preview]:
        """Fetch now, ``recorded_location`` being what ``.source`` keeps."""
        handler = self.sources[source]
        if listed is not None and listed[1].artifact is not None:
            entry, release = listed
            fetching = handler.fetch_listed(
                entry.location,  # as the bot read it, since an attestation names it
                release.tag,
                kind=release.artifact.kind,
                sha256=release.sha256,
                commit=release.commit,
                url=release.artifact.url,
                size=release.artifact.size,
                bundle_url=release.attestation and release.attestation.bundle_url,
            )
        else:
            fetching = handler.fetch(location, ref)
        try:
            with fetching as fetched:
                yield Preview(source.value, recorded_location or location, fetched)
        except RateLimitError as error:
            raise PluginRateLimitError(str(error), **error.params) from error
        except SourceError as error:
            raise PluginInstallError(
                f"Could not fetch the plugin: {error}", error.code, **error.params
            ) from error

    @contextmanager
    def _claim(
        self, token: str, origin: Optional[Tuple[str, str]] = None
    ) -> Iterator[Preview]:
        """The copy ``validate`` reviewed, which must come from ``origin`` if given."""
        with previews.claim(self.storage.root, token) as preview:
            if origin is not None and (preview.source, preview.location) != origin:
                raise PluginInstallError(
                    f"The preview is of {preview.location}, not of {origin[1]}",
                    "preview_mismatch",
                )
            yield preview

    @_install_errors
    @beartype
    def validate(
        self,
        source: PluginSource,
        location: str,
        ref: Optional[str] = None,
        recorded_location: Optional[str] = None,
    ) -> ValidationResult:
        """What installing would do, keeping a valid copy as ``result.preview``."""
        index = self._index()
        listed = listed_release(index, source, location, ref)
        # Locked (after downloading), as it reads what an operation may be changing.
        with (
            self._acquire(source, location, ref, recorded_location, listed) as preview,
            self._lock,
        ):
            fetched = preview.fetched
            manifest, result = PluginValidator.validate(fetched.path)
            listed = listed or listed_release(index, source, location, fetched.ref)
            result.ref = fetched.ref
            result.trust_level = fetched.trust_level
            result.needs_ack = needs_ack(fetched.trust_level)
            if manifest is None:
                return result
            for field in ("id", "version", "name", "description", "dependencies"):
                setattr(result, field, getattr(manifest, field))
            result.project_urls = manifest.project_urls
            result.authors = [author.model_dump() for author in manifest.authors]
            result.readme = read_readme(fetched.path)
            result.verified = fetched.verified
            result.sha256 = fetched.sha256
            if listed is not None:
                _check_listed(*listed, manifest, fetched)
            if revoked_release(index, manifest.id, fetched.sha256):
                raise PluginInstallError(
                    f"The plugin store revoked this release of '{manifest.id}'",
                    "revoked",
                )
            retired = removed_entry(index, manifest.id, source, location)
            result.removed = retired.type if retired else None
            handler = self.sources[source]
            if handler.can_update:  # a .zip has no owner and is not the store's
                result.owner = handler.owner(location)
                result.in_store = bool(
                    store_entry(index, manifest.id, source, location)
                )
            result.plugin_dependencies, errors = self._plugin_plan(manifest)
            result.errors.extend(errors)
            result.breaks = [
                m.name
                for m in bootstrap.installed_manifests(self.storage).values()
                if not in_range(manifest.version, m.plugin_specifiers.get(manifest.id))
            ]
            if result.is_valid and manifest.dependencies:
                resolution = self.dependencies.resolve(
                    manifest.dependencies, self._other_dependencies(manifest.id)
                )
                if not resolution.ok:
                    result.errors.append(
                        PluginError(
                            "dependency_conflict",
                            f"Dependency conflict: {resolution.explanation}",
                        )
                    )
            installed = self._manifest_or_none(manifest.id)
            if installed is not None:
                result.installed_version = installed.version
                new, old = Version(manifest.version), Version(installed.version)
                result.version_change = (
                    "newer" if new > old else "same" if new == old else "older"
                )
            if self.storage.is_installed(manifest.id):  # even if its manifest is broken
                try:
                    provenance = self.storage.read_source(manifest.id)
                except (ValueError, KeyError):
                    provenance = None
                if provenance is not None:
                    result.installed_location = provenance.location
                    # Same id from another origin, but a new local .zip updates it
                    result.replaces_other = origin_key(source, location) != origin_key(
                        provenance.source, provenance.location
                    )
                    result.needs_ack = needs_ack(
                        fetched.trust_level, provenance.trust_level
                    )
            if result.is_valid:
                result.preview = previews.save(self.storage.root, preview)
            return result

    def _plugin_plan(
        self, manifest: PluginManifest
    ) -> Tuple[List[Dict[str, Optional[str]]], List[PluginError]]:
        """``manifest``'s plugin dependencies in install order, from disk or store."""
        index = self._index()
        installed = bootstrap.installed_manifests(self.storage)
        plan: Dict[str, Dict[str, Optional[str]]] = {}
        # Id -> ids it needs, [] if unobtainable, so install_order drops only cycles
        graph = {manifest.id: manifest.plugin_dependencies}
        chosen: Dict[str, Union[PluginManifest, StoreRelease]] = {}
        errors: List[PluginError] = []
        todo = [(i, manifest.plugin_specifiers.get(i)) for i in graph[manifest.id]]
        while todo:
            plugin_id, spec = todo.pop(0)
            if plugin_id in graph:
                continue
            info, needer, error = self._plan_one(plugin_id, spec, installed, index)
            graph[plugin_id] = needer.plugin_dependencies if needer else []
            if error is not None:
                errors.append(error)
                continue
            plan[plugin_id] = info
            chosen[plugin_id] = needer
            todo += [(i, needer.plugin_specifiers.get(i)) for i in graph[plugin_id]]
        for needer in [manifest, *chosen.values()]:
            for i, spec in needer.plugin_specifiers.items():
                if i in chosen and not in_range(chosen[i].version, spec):
                    errors.append(
                        _wrong_version(
                            i,
                            spec,
                            None if plan[i]["state"] == "store" else chosen[i].version,
                        )
                    )
        order = bootstrap.install_order(
            {i: SimpleNamespace(plugin_dependencies=n) for i, n in graph.items()}
        )
        cycle = graph.keys() - set(order)
        # Without those that only need one in a cycle, as nobody left needs them.
        while behind := {i for i in cycle if not any(i in graph[j] for j in cycle)}:
            cycle -= behind
        if cycle := sorted(cycle):
            errors.append(
                PluginError(
                    "dependency_cycle",
                    f"These plugins need each other: {', '.join(cycle)}",
                    {"ids": cycle},
                )
            )
        return [plan[i] for i in order if i in plan], errors

    def _plan_one(
        self,
        plugin_id: str,
        spec: Optional[str],
        installed: Dict[str, PluginManifest],
        index: Optional[StoreIndex],
    ) -> Tuple[
        Optional[Dict[str, Optional[str]]],
        Union[PluginManifest, StoreRelease, None],
        Optional[PluginError],
    ]:
        """``(info, its manifest or release, problem)`` for ``_plugin_plan``."""
        if plugin_id in installed:
            manifest = installed[plugin_id]
            state = "active"
            if not PluginLoader.is_loaded(manifest, self.registry):
                problem = self._dependency_problem(plugin_id, manifest, installed)
                if problem:
                    return None, None, _unavailable(plugin_id, problem)
                state = "disabled"
            info = {"id": plugin_id, "name": manifest.name, "state": state}
            return {**info, "location": None, "ref": None}, manifest, None
        if self.storage.is_installed(plugin_id):  # its manifest is unreadable
            return None, None, _unavailable(plugin_id, "damaged")
        entry = next(
            (e for e in (index.plugins if index else []) if e.id == plugin_id), None
        )
        release = offered_release(entry, spec=spec) if entry else None
        if entry and not any(in_range(r.version, spec) for r in entry.releases):
            return None, None, _wrong_version(plugin_id, spec, None)
        if entry and release is None:
            return (
                None,
                None,
                PluginError(
                    "incompatible_plugin_dependency",
                    f"Needs the plugin '{plugin_id}', but no store release of it "
                    "runs on this dashAI",
                    {"id": plugin_id},
                ),
            )
        if release is None:
            return (
                None,
                None,
                PluginError(
                    "missing_plugin_dependency",
                    f"Needs the plugin '{plugin_id}', which is neither installed nor "
                    "in the plugin store",
                    # False only if a store exists and could not be read
                    {"id": plugin_id, "store_read": bool(index or not self.store)},
                ),
            )
        newest = next(r.tag for r in entry.releases if in_range(r.version, spec))
        info = {
            "id": plugin_id,
            "name": entry.name,
            "state": "store",
            "location": entry.location,
            "ref": release.tag,
            "latest": None if newest == release.tag else newest,
        }
        return info, release, None

    def _dependency_problem(
        self,
        plugin_id: str,
        manifest: PluginManifest,
        installed: Dict[str, PluginManifest],
    ) -> Optional[str]:
        """Why enabling an unloaded plugin wouldn't load it, or None."""
        if self.storage.is_blocked(plugin_id):
            return "blocked"
        incompatible, missing = bootstrap.check_requirements(
            manifest, self.dependencies.directory()
        )
        if incompatible:
            return "incompatible"
        if missing:
            return "repair_failed"
        if plugin_id in self.pending_restart:
            return "restart_required"
        if self.storage.is_enabled(plugin_id) and not bootstrap.unloaded_dependency(
            manifest, installed, self.registry
        ):
            return "load_failed"  # enabled, with what it needs, yet not loaded
        return None

    @beartype
    def install(
        self,
        source: PluginSource,
        location: str,
        ref: Optional[str] = None,
        provenance: Optional[Provenance] = None,
        repair: bool = False,
    ) -> InstalledPlugin:
        """Fetch and install or replace, all or nothing, ``repair`` won't wait."""
        return self._install(
            self._acquire(source, location, ref), provenance=provenance, repair=repair
        )

    @_install_errors
    @beartype
    def install_preview(
        self,
        token: str,
        origin: Optional[Tuple[str, str]] = None,
        newer_only: bool = False,
    ) -> InstalledPlugin:
        """Install the ``preview`` ``validate`` reviewed, rechecking its dependents."""
        # Taken under the lock, as two Windows renames of one folder can both succeed
        with self._lock, operation(self.storage.root):
            return self._install(self._claim(token, origin), newer_only=newer_only)

    @_install_errors
    def _install(
        self,
        acquire: AbstractContextManager,  # of a Preview, _acquire or _claim
        newer_only: bool = False,
        provenance: Optional[Provenance] = None,
        repair: bool = False,
    ) -> InstalledPlugin:
        with (
            acquire as (source, location, fetched),
            self._lock,
            operation(self.storage.root),
        ):
            plugin_dir = fetched.path
            manifest, result = PluginValidator.validate(plugin_dir)
            if not result.is_valid:  # the preview's errors, all of them
                raise PluginInstallError(
                    "; ".join(error.detail for error in result.errors),
                    "invalid_plugin",
                    errors=[asdict(error) for error in result.errors],
                )

            plugin_id = manifest.id
            is_update = self.storage.is_installed(plugin_id)
            previous = self._manifest_or_none(plugin_id)
            if (
                newer_only
                and previous is not None
                and Version(manifest.version) <= Version(previous.version)
            ):
                raise PluginInstallError(
                    f"No newer version: {previous.version} is installed and "
                    f"the latest release is {manifest.version}",
                    "no_newer_version",
                    installed=previous.version,
                    latest=manifest.version,
                )
            enabled = self.storage.is_enabled(plugin_id) if is_update else True
            # Retired as malicious, so its code never runs unless the user allows it
            blocked = self._blocked(
                plugin_id,
                provenance.source if provenance else source,
                provenance.location if provenance else location,
                provenance.sha256 if provenance else fetched.sha256,
            )
            runs = blocked is None or blocked.allowed
            # Needs its dependencies active here, checked before pip
            inactive = None
            if runs and not repair:
                inactive = bootstrap.unloaded_dependency(
                    manifest, bootstrap.installed_manifests(self.storage), self.registry
                )
                absent = next(
                    (
                        i
                        for i in manifest.plugin_dependencies
                        if not self.storage.is_installed(i)
                    ),
                    None,
                )
                if is_update and absent:
                    raise PluginInstallError(
                        f"'{plugin_id}' needs the plugin '{absent}', which is "
                        "not installed",
                        "missing_plugin_dependency",
                        id=absent,
                    )
                if inactive and not is_update:
                    raise PluginInstallError(
                        f"'{plugin_id}' needs the plugin '{inactive}', which is "
                        "not active",
                        "dependency_unavailable",
                        id=inactive,
                    )

            resolution = self.dependencies.resolve(
                manifest.dependencies, self._other_dependencies(plugin_id)
            )
            if not resolution.ok:
                raise PluginInstallError(resolution.explanation, "dependency_conflict")
            present = self.dependencies.installed()
            replaced = [
                d["name"] for d in resolution.distributions if d["name"] in present
            ]
            dependencies_change = bool(resolution.distributions) or (
                previous is not None
                and sorted(previous.dependencies) != sorted(manifest.dependencies)
            )
            if dependencies_change and not repair:
                self._ensure_idle()
            # Before the transaction, while the old RECORDs exist.
            replaced_here = self._imported_here(replaced)
            owned_before = self._owned(plugin_id, previous) if is_update else set()

            transaction = self.dependencies.transaction()
            registered = False
            load_error: Optional[str] = None
            try:
                try:
                    transaction.install(resolution.distributions)
                except DependencyError as error:
                    raise PluginInstallError(
                        f"Dependency install failed: {error}",
                        error.code,
                        **error.params,
                    ) from error

                stale_here = bool(replaced_here) or self._uses_stale(manifest)
                if not runs:
                    loaded = []
                elif stale_here or inactive:
                    # Old library in memory or dependencies inactive, so check apart
                    self._load_check(plugin_dir)
                    loaded = []
                else:
                    try:
                        loaded = PluginLoader.load(manifest, plugin_dir, self.registry)
                        registered = True
                    except PluginLoadError as error:
                        if not repair:
                            raise PluginInstallError(
                                f"Load failed: {error}", error.code, **error.params
                            ) from error
                        load_error, loaded = str(error), []
                    if registered and not enabled:
                        PluginLoader.unload(manifest, self.registry)
                        registered = False

                now = datetime.now(timezone.utc).isoformat()
                provenance = provenance or Provenance(
                    source=source,
                    location=location,
                    ref=fetched.ref,
                    trust_level=fetched.trust_level,
                    verified=fetched.verified,
                    sha256=fetched.sha256,
                    commit=fetched.commit,
                    asset=fetched.asset,
                    workflow=fetched.workflow,
                    signed_at=fetched.signed_at,
                    issuer=fetched.issuer,
                    installed_at=self._installed_at(plugin_id) or now,
                    updated_at=now,
                )
                # One trash with the dependencies, so they commit or undo together.
                stored = self.storage.save(
                    plugin_id,
                    plugin_dir,
                    provenance=provenance,
                    disabled=not enabled,
                    trash=transaction.trash,
                    blocked=blocked,
                )
                PluginLoader.relocate(plugin_id, plugin_dir, stored.path)
            except BaseException:
                transaction.rollback()
                if registered:
                    PluginLoader.unload(manifest, self.registry)
                    self._reload_previous(plugin_id, previous, enabled)
                raise

            transaction.commit()
            self._stale |= replaced_here
            needed = self.dependencies.closure(manifest.dependencies)
            self.dependencies.record(plugin_id, needed, pending=owned_before - needed)
            pruned = self._prune(owned_before - needed, plugin_id)
            if transaction.changed or pruned:
                self._request_worker_restart()

            if stale_here:
                if previous is not None:
                    PluginLoader.unload(previous, self.registry)
                self.pending_restart.add(plugin_id)
            else:
                self.pending_restart.discard(plugin_id)
                if previous is not None and enabled:
                    PluginLoader.unload(
                        previous,
                        self.registry,
                        keep=frozenset(
                            c.name for c in manifest.components if registered
                        ),
                    )
            bootstrap.load_errors.pop(plugin_id, None)
            if load_error is not None:
                bootstrap.load_errors[plugin_id] = load_error
            self.repair_errors.pop(plugin_id, None)
            self._sync_dependents(plugin_id)
            if transaction.changed:
                self._retry_failed()

            logger.info("Installed plugin %s %s", plugin_id, manifest.version)
            return InstalledPlugin(
                id=plugin_id,
                name=manifest.name,
                version=manifest.version,
                path=stored.path,
                components=loaded,
                ref=provenance.ref,
                trust_level=provenance.trust_level,
                verified=provenance.verified,
                sha256=provenance.sha256,
                commit=provenance.commit,
                pending_restart=stale_here,
            )

    @_install_errors
    @beartype
    def repair(self, plugin_id: str) -> InstalledPlugin:
        """Install what an installed plugin declares (``repair_missing``)."""
        with self._lock:
            provenance = self.storage.read_source(plugin_id) or Provenance(
                "local", "", None
            )
            return self.install(
                PluginSource.LOCAL,
                str(self.storage.plugin_dir(plugin_id)),
                provenance=provenance,
                repair=True,
            )

    def repair_missing(self) -> None:
        """At startup, install what plugins miss, failures in ``repair_errors``."""
        plugins_dir = self.dependencies.directory()
        installed = bootstrap.installed_manifests(self.storage)
        order = bootstrap.install_order(installed)
        manifests = [
            (plugin_id, installed[plugin_id])
            for plugin_id in order + sorted(installed.keys() - set(order))
        ]

        def needs_repair(manifest: PluginManifest) -> bool:
            incompatible, missing = bootstrap.check_requirements(manifest, plugins_dir)
            return bool(missing) and not incompatible

        todo = [(i, m) for i, m in manifests if needs_repair(m)]
        if not todo:
            return
        try:
            with self._lock, operation(self.storage.root):
                offline = not self.dependencies.index_reachable()
                for number, (plugin_id, manifest) in enumerate(todo, 1):
                    if not needs_repair(manifest):  # another's repair brought them
                        continue
                    logger.info(
                        "Repairing plugin dependencies (%d of %d: %s)",
                        number,
                        len(todo),
                        plugin_id,
                    )
                    try:
                        if offline:
                            raise PluginInstallError(
                                "no internet connection", "offline"
                            )
                        self.repair(plugin_id)
                    except Exception as error:  # noqa: BLE001
                        logger.warning(
                            "Could not repair plugin '%s': %s", plugin_id, error
                        )
                        self.repair_errors[plugin_id] = (
                            f"Could not install its dependencies: {error}; "
                            "dashAI tries again when it starts"
                        )
        # Another dashAI changing plugins, or the marker locked (an antivirus).
        except (OperationBusyError, OSError) as error:
            logger.warning("Skipping the plugin repair: %s", error)

    def _retry_failed(self) -> None:
        """Dependencies changed: a plugin that failed to load may load now."""
        for plugin_id in set(bootstrap.load_errors) - self.pending_restart:
            if self.storage.is_enabled(plugin_id):
                with contextlib.suppress(PluginInstallError):
                    self.enable(plugin_id)

    def _reload_previous(
        self, plugin_id: str, previous: Optional[PluginManifest], enabled: bool
    ) -> None:
        """After a failed update, re-register the version still on disk."""
        if previous is None or not enabled:
            return
        try:
            PluginLoader.load(
                previous, self.storage.plugin_dir(plugin_id), self.registry
            )
        except PluginLoadError as error:
            logger.warning(
                "Could not reload '%s' after a failure: %s", plugin_id, error
            )

    def _prune(self, candidates: Set[str], plugin_id: str) -> List[str]:
        """Remove orphans in ``candidates``, failures stay pending in the ledger."""
        orphans = candidates - self._needed_by_others(plugin_id)
        removed: List[str] = []
        if orphans:
            imported = self._imported_here(orphans)
            transaction = self.dependencies.transaction()
            try:
                transaction.remove(orphans)
            except Exception as error:  # noqa: BLE001
                transaction.rollback()
                logger.warning("Could not remove orphan dependencies: %s", error)
                return []
            transaction.commit()
            removed = transaction.removed
            self._stale |= imported & set(removed)
            if removed:
                logger.info("Pruned orphan dependencies: %s", removed)
        self.dependencies.settle(candidates)
        return removed

    @_install_errors
    @beartype
    def update(self, plugin_id: str, preview: str) -> InstalledPlugin:
        """Install the newer release ``validate`` reviewed for a GitHub plugin."""
        self._require_installed(plugin_id)
        provenance = self.storage.read_source(plugin_id)
        if provenance is None:
            raise PluginInstallError(
                f"No recorded source for '{plugin_id}'; reinstall it with install",
                "cannot_update",
            )
        if not self.sources[PluginSource(provenance.source)].can_update:
            raise PluginInstallError(
                f"'{plugin_id}' has no source to update from; upload the new version",
                "cannot_update",
            )
        origin = (provenance.source, provenance.location)
        return self.install_preview(preview, origin, newer_only=True)

    def _require_installed(self, plugin_id: str) -> None:
        if not self.storage.is_installed(plugin_id):
            raise PluginInstallError(
                f"Plugin not installed: {plugin_id}", "not_installed", id=plugin_id
            )

    @beartype
    def _manifest_or_none(self, plugin_id: str) -> Optional[PluginManifest]:
        """None if not installed or unreadable (logged), so it blocks nothing."""
        if not self.storage.is_installed(plugin_id):
            return None
        try:
            return PluginManifest.from_file(
                self.storage.plugin_dir(plugin_id) / self.storage.MANIFEST_FILENAME
            )
        except ManifestError as error:
            logger.warning("Unreadable manifest for plugin '%s': %s", plugin_id, error)
            return None

    def _installed_at(self, plugin_id: str) -> Optional[str]:
        """When this id was first installed (kept on updates), or None."""
        try:
            provenance = self.storage.read_source(plugin_id)
        except (OSError, ValueError, KeyError):
            return None
        return provenance.installed_at if provenance else None

    def _index(self) -> Optional[StoreIndex]:
        return self.store.read() if self.store else None

    def _blocked(
        self,
        plugin_id: str,
        source: str,
        location: str,
        sha256: Optional[str],
        index: Optional[StoreIndex] = None,
    ) -> Optional[Blocked]:
        """The ``.blocked`` marker the store implies, or the current one without it."""
        index = index or self._index()
        before = self.storage.read_blocked(plugin_id)
        if index is None:
            return before
        entry = removed_entry(index, plugin_id, source, location)
        reasons = [
            entry if entry and entry.type == "critical" else None,
            revoked_release(index, plugin_id, sha256),
        ]
        dates = [reason.date for reason in reasons if reason]
        if not dates:
            return None
        allowed = before is not None and before.allowed and before.date == max(dates)
        return Blocked(max(dates), allowed)

    def apply_removed(self) -> bool:
        """Sync ``.blocked`` markers with the store, True if any changed."""
        index = self._index()
        if index is None:
            return False
        changed = False
        with self._lock:
            for plugin_id in self.storage.list_installed():
                try:
                    provenance = self.storage.read_source(plugin_id)
                except (ValueError, KeyError):  # damaged, never loaded
                    continue
                if provenance is None:
                    continue
                before = self.storage.read_blocked(plugin_id)
                blocked = self._blocked(
                    plugin_id,
                    provenance.source,
                    provenance.location,
                    provenance.sha256,
                    index,
                )
                if blocked == before:
                    continue
                try:
                    self.storage.set_blocked(plugin_id, blocked)
                except OSError as error:  # tried again at the next reading
                    logger.warning("Could not mark '%s': %s", plugin_id, error)
                    continue
                was_blocked = before is not None and not before.allowed
                is_blocked = blocked is not None and not blocked.allowed
                changed |= is_blocked != was_blocked
                try:
                    if is_blocked and not was_blocked:
                        manifest = self._manifest_or_none(plugin_id)
                        if manifest is not None:
                            PluginLoader.unload(manifest, self.registry)
                        self._sync_dependents(plugin_id)
                        logger.warning(
                            "The plugin store blocked plugin '%s'", plugin_id
                        )
                    elif was_blocked and not is_blocked:
                        if self.storage.is_enabled(plugin_id):
                            with contextlib.suppress(PluginInstallError):
                                self.enable(plugin_id)
                except Exception:  # noqa: BLE001 (its mark is written, the rest go on)
                    logger.exception(
                        "Could not apply the store's mark to '%s'", plugin_id
                    )
        return changed

    @_install_errors
    @beartype
    def uninstall(self, plugin_id: str, prune_deps: bool = True) -> None:
        with self._lock, operation(self.storage.root):
            self._require_installed(plugin_id)
            manifest = self._manifest_or_none(plugin_id)
            orphans = self._owned(plugin_id, manifest) if prune_deps else set()
            if orphans:
                orphans -= self._needed_by_others(plugin_id)
            if orphans:
                self._ensure_idle()
            self.storage.remove(plugin_id)
            if manifest is not None:
                PluginLoader.unload(manifest, self.registry)
            self._sync_dependents(plugin_id)
            self.pending_restart.discard(plugin_id)
            bootstrap.load_errors.pop(plugin_id, None)
            self.repair_errors.pop(plugin_id, None)
            self.dependencies.forget(plugin_id, pending=orphans)
            if orphans and self._prune(orphans, plugin_id):
                self._request_worker_restart()

    @_install_errors
    @beartype
    def disable(self, plugin_id: str) -> None:
        with self._lock:
            self._require_installed(plugin_id)
            if not self.storage.is_enabled(plugin_id):
                return
            self.storage.set_enabled(plugin_id, False)
            manifest = self._manifest_or_none(plugin_id)
            if manifest is not None:
                PluginLoader.unload(manifest, self.registry)
            self._sync_dependents(plugin_id)

    @_install_errors
    @beartype
    def enable(self, plugin_id: str, allow_blocked: bool = False) -> None:
        """``allow_blocked`` runs a plugin the store retired, until retired again."""
        with self._lock:
            self._require_installed(plugin_id)
            if self.storage.is_blocked(plugin_id):
                if not allow_blocked:
                    raise PluginInstallError(
                        f"The plugin store retired '{plugin_id}' as malicious",
                        "blocked",
                    )
                blocked = self.storage.read_blocked(plugin_id)
                self.storage.set_blocked(plugin_id, blocked._replace(allowed=True))
            manifest = self._manifest_or_none(plugin_id)
            if manifest is None:
                raise PluginInstallError(
                    f"Invalid manifest for '{plugin_id}'; upload a fixed version",
                    "invalid_manifest",
                )
            manifests = bootstrap.installed_manifests(
                self.storage, manifest.plugin_dependencies
            )
            if bootstrap.unloaded_dependency(manifest, manifests, self.registry):
                self.storage.set_enabled(plugin_id, True)
                return
            plugin_dir = self.storage.plugin_dir(plugin_id)
            if plugin_id not in self.pending_restart and self._uses_stale(manifest):
                try:
                    self._load_check(plugin_dir)
                except PluginInstallError as error:
                    raise PluginInstallError(
                        f"Enable failed: {error}", error.code, **error.params
                    ) from error
                self.pending_restart.add(plugin_id)
            if plugin_id in self.pending_restart:
                self.storage.set_enabled(plugin_id, True)
                self._sync_dependents(plugin_id)
                return
            if self.storage.is_enabled(plugin_id) and PluginLoader.is_loaded(
                manifest, self.registry
            ):
                return
            try:
                bootstrap.load_plugin(self.storage, self.registry, plugin_id)
            except (PluginLoadError, ManifestError) as error:
                raise PluginInstallError(
                    f"Enable failed: {error}", error.code, **error.params
                ) from error
            try:
                self.storage.set_enabled(plugin_id, True)
            except OSError:
                PluginLoader.unload(manifest, self.registry)
                raise
            self._sync_dependents(plugin_id)

    def _sync_dependents(self, plugin_id: str) -> None:
        bootstrap.sync_dependents(
            self.storage, self.registry, plugin_id, skip=frozenset(self.pending_restart)
        )

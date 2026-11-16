import contextlib
import logging
from pathlib import Path
from weakref import WeakKeyDictionary

from beartype import beartype
from beartype.typing import Dict, FrozenSet, List, Optional, Tuple
from pydantic import TypeAdapter

from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.plugins.dependencies import (
    activate_dependencies,
    dependencies_directory,
    unmet_requirements,
)
from DashAI.back.plugins.disk.storage import PluginStorage
from DashAI.back.plugins.disk.trash import write_json
from DashAI.back.plugins.loader import PluginLoader, PluginLoadError
from DashAI.back.plugins.manifest.manifest import (
    PLUGIN_ID,
    ManifestError,
    PluginManifest,
    in_range,
)
from DashAI.back.plugins.manifest.validator import PluginValidator

# Per registry, plugin_id -> (fingerprint, manifest) of what this process loaded.
_loaded: (
    "WeakKeyDictionary[ComponentRegistry, Dict[str, Tuple[object, PluginManifest]]]"
)
_loaded = WeakKeyDictionary()

# Per registry, plugin_id -> fingerprint of a failed load, retried once it changes.
_failed: "WeakKeyDictionary[ComponentRegistry, Dict[str, tuple]]" = WeakKeyDictionary()

# Why an enabled plugin is not loaded here, by plugin id (shown to the user).
load_errors: Dict[str, str] = {}

# The job worker's load errors for the API, id -> [fingerprint, error].
WORKER_LOAD_ERRORS = ".worker-load-errors.json"
_WORKER_ERRORS = TypeAdapter(Dict[str, Tuple[int, str]])

logger = logging.getLogger(__name__)


def _fingerprint(storage: PluginStorage, plugin_id: str) -> Optional[int]:
    """Changes on each (re)install, which rewrites ``.source``. None if gone."""
    plugin_dir = storage.plugin_dir(plugin_id)
    for name in (storage.SOURCE_MARKER, storage.MANIFEST_FILENAME):
        with contextlib.suppress(OSError):
            return (plugin_dir / name).stat().st_mtime_ns
    return None


def install_order(
    manifests: Dict[str, PluginManifest], have: FrozenSet[str] = frozenset()
) -> List[str]:
    """Ids, each after those it needs (or in ``have``), minus unmet ones and cycles."""
    order, done, pending = [], set(have), dict(manifests)
    while ready := sorted(
        i for i, m in pending.items() if set(m.plugin_dependencies) <= done
    ):
        for plugin_id in ready:
            order.append(plugin_id)
            done.add(plugin_id)
            del pending[plugin_id]
    return order


def dependents(manifests: Dict[str, PluginManifest], plugin_id: str) -> List[str]:
    """What needs ``plugin_id`` transitively, in install order, even once it is gone."""
    others = {i: m for i, m in manifests.items() if i != plugin_id}
    without = set(install_order(others))
    return [
        i for i in install_order(others, frozenset({plugin_id})) if i not in without
    ]


def installed_manifests(
    storage: PluginStorage, plugin_ids: Optional[List[str]] = None
) -> Dict[str, PluginManifest]:
    """The readable manifests of the installed plugins, by id."""
    manifests = {}
    for plugin_id in storage.list_installed() if plugin_ids is None else plugin_ids:
        with contextlib.suppress(OSError, ManifestError):
            manifests[plugin_id] = PluginManifest.from_file(
                storage.plugin_dir(plugin_id) / storage.MANIFEST_FILENAME
            )
    return manifests


def wrong_versions(
    manifest: PluginManifest, manifests: Dict[str, PluginManifest]
) -> List[str]:
    return [
        i
        for i, spec in manifest.plugin_specifiers.items()
        if i in manifests and not in_range(manifests[i].version, spec)
    ]


def unloaded_dependency(
    manifest: PluginManifest,
    manifests: Dict[str, PluginManifest],
    registry: ComponentRegistry,
) -> Optional[str]:
    """The first plugin ``manifest`` needs that is not loaded in ``registry``."""
    wrong = wrong_versions(manifest, manifests)
    for needed in manifest.plugin_dependencies:
        if (
            needed not in manifests
            or needed in wrong
            or not PluginLoader.is_loaded(manifests[needed], registry)
        ):
            return needed
    return None


def sync_dependents(
    storage: PluginStorage,
    registry: ComponentRegistry,
    plugin_id: str,
    skip: FrozenSet[str] = frozenset(),
) -> None:
    """Unload ``plugin_id``'s dependents, reload loadable ones not in ``skip``."""
    manifests = installed_manifests(storage)
    found = dependents(manifests, plugin_id)
    for dependent in reversed(found):
        PluginLoader.unload(manifests[dependent], registry)
    for dependent in found:
        if (
            dependent in skip
            or not storage.is_enabled(dependent)
            or storage.is_blocked(dependent)
            or unloaded_dependency(manifests[dependent], manifests, registry)
        ):
            continue
        try:
            load_plugin(storage, registry, dependent)
        except Exception as error:  # noqa: BLE001
            logger.warning("Could not load plugin '%s': %s", dependent, error)


def check_requirements(
    manifest: PluginManifest, plugins_dir: Path
) -> Tuple[Optional[str], List[str]]:
    """``(why it can't run on this dashAI, what pip can still install)``."""
    missing, conflicts = unmet_requirements(manifest.dependencies, plugins_dir)
    too_old = PluginValidator.check_app_version(manifest.min_app_version)
    reasons = [reason for reason in (too_old, *conflicts) if reason]
    incompatible = f"Incompatible with this dashAI: {'; '.join(reasons)}"
    return (incompatible if reasons else None), missing


def load_plugin(
    storage: PluginStorage, registry: ComponentRegistry, plugin_id: str
) -> None:
    """Load an installed plugin; on failure keep why in ``load_errors``."""
    plugin_dir = storage.plugin_dir(plugin_id)
    manifest = PluginManifest.from_file(plugin_dir / storage.MANIFEST_FILENAME)
    incompatible, missing = check_requirements(
        manifest, dependencies_directory(storage.root)
    )
    try:
        if manifest.id != plugin_id:  # e.g. a folder renamed by hand
            raise PluginLoadError(
                f"Its manifest id is '{manifest.id}' but its folder is '{plugin_id}'"
            )
        if incompatible:
            raise PluginLoadError(incompatible, "incompatible")
        if missing:
            raise PluginLoadError(
                "Missing dependencies (dashAI installs them when it starts): "
                + ", ".join(missing),
                "missing_dependencies",
            )
        PluginLoader.load(manifest, plugin_dir, registry)
    except Exception as error:
        load_errors[plugin_id] = str(error)
        raise
    load_errors.pop(plugin_id, None)
    _loaded.setdefault(registry, {})[plugin_id] = (
        _fingerprint(storage, plugin_id),
        manifest,
    )


@beartype
def sync_installed_plugins(
    storage: PluginStorage, registry: ComponentRegistry, is_worker: bool = False
) -> List[str]:
    """Sync ``registry`` to the enabled, unblocked plugins on disk, return changes."""
    activate_dependencies(storage.root)
    loaded = _loaded.setdefault(registry, {})
    failed = _failed.setdefault(registry, {})
    own = {
        plugin_id: fingerprint
        for plugin_id in storage.list_installed()
        if storage.is_enabled(plugin_id)
        and not storage.is_blocked(plugin_id)
        and (fingerprint := _fingerprint(storage, plugin_id)) is not None
    }
    manifests = installed_manifests(storage, list(own))
    # Fingerprints include dependencies, so an update reloads its dependents
    desired: Dict[str, tuple] = {}
    for plugin_id in install_order(manifests):
        desired[plugin_id] = (
            own[plugin_id],
            *(desired[d] for d in manifests[plugin_id].plugin_dependencies),
        )
    for plugin_id in own.keys() - manifests.keys():
        desired[plugin_id] = (own[plugin_id],)
    changed: List[str] = []
    stale = [p for p, (fp, _) in loaded.items() if desired.get(p) != fp]
    for plugin_id in reversed(stale):  # dependents first
        PluginLoader.unload(loaded.pop(plugin_id)[1], registry)
        changed.append(plugin_id)
    for plugin_id, fingerprint in desired.items():
        if plugin_id in loaded or failed.get(plugin_id) == fingerprint:
            continue
        needs = manifests.get(plugin_id)
        if needs and (
            not set(needs.plugin_dependencies) <= loaded.keys()
            or wrong_versions(needs, manifests)
        ):
            continue  # one it needs failed, the API shows it as unavailable
        try:
            load_plugin(storage, registry, plugin_id)
            loaded[plugin_id] = (fingerprint, loaded[plugin_id][1])
            failed.pop(plugin_id, None)
            if plugin_id not in changed:
                changed.append(plugin_id)
        except Exception as error:  # noqa: BLE001
            failed[plugin_id] = fingerprint
            logger.warning("Could not load plugin '%s': %s", plugin_id, error)
    if is_worker:
        try:
            write_json(
                storage.root / WORKER_LOAD_ERRORS,
                {
                    p: [own[p], load_errors[p]]
                    for p in failed
                    if p in load_errors and p in own
                },
            )
        except OSError as error:
            logger.warning("Could not write %s: %s", WORKER_LOAD_ERRORS, error)
    return changed


def worker_load_errors(storage: PluginStorage) -> Dict[str, str]:
    """The job worker's load errors that still apply to what is on disk."""
    try:
        data = _WORKER_ERRORS.validate_json(
            (storage.root / WORKER_LOAD_ERRORS).read_bytes()
        )
    except (OSError, ValueError):  # also not one (e.g. edited by hand)
        return {}
    return {
        plugin_id: error
        for plugin_id, (fingerprint, error) in data.items()
        if PLUGIN_ID.fullmatch(plugin_id)
        and storage.is_installed(plugin_id)
        and _fingerprint(storage, plugin_id) == fingerprint
    }

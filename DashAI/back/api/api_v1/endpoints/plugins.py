import ipaddress
import tempfile
from contextlib import asynccontextmanager, contextmanager, suppress
from dataclasses import asdict
from pathlib import Path
from typing import AsyncIterator, Dict, Iterator, List, Optional, Tuple
from urllib.parse import urlsplit

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.concurrency import run_in_threadpool
from kink import di, inject

from DashAI.back.api.api_v1.schemas.plugin_params import (
    InstalledPluginResponse,
    InstallPluginRequest,
    PluginProblem,
    PluginSettingsResponse,
    PluginSettingsValues,
    PluginUpdatesResponse,
    PluginValidationResponse,
    ProblemInfo,
    SetEnabledRequest,
    StoreResponse,
    ValidatePluginRequest,
)
from DashAI.back.core.enums.plugin_source import PluginSource
from DashAI.back.core.utils import localize
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.plugins import bootstrap
from DashAI.back.plugins import settings as plugin_settings
from DashAI.back.plugins.dependencies import dependencies_directory
from DashAI.back.plugins.disk import previews
from DashAI.back.plugins.disk.storage import PluginStorage, read_readme
from DashAI.back.plugins.errors import PluginError
from DashAI.back.plugins.loader import PluginLoader
from DashAI.back.plugins.manifest.manifest import ManifestError, PluginManifest
from DashAI.back.plugins.plugin_installer import (
    PluginBusyError,
    PluginInstaller,
    PluginInstallError,
    PluginRateLimitError,
)
from DashAI.back.plugins.sources import HANDLERS, source_for
from DashAI.back.plugins.sources.base import (
    MAX_PLUGIN_BYTES,
    RateLimitError,
    SourceError,
)
from DashAI.back.plugins.store.store import (
    STORE_DISABLED,
    PluginStore,
    StoreIndex,
    removed_entry,
)
from DashAI.back.plugins.store.updates import PluginUpdates

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def _from_dashai(request: Request) -> None:
    """Allow no ``Origin``, this machine or dashAI by IP, not a name (DNS rebinding)."""
    origin = request.headers.get("origin")
    if origin is None:
        return
    parts = urlsplit(origin)
    host = parts.hostname or ""
    if host in _LOCAL_HOSTS:
        return
    with suppress(ValueError):
        ipaddress.ip_address(host)
        if parts.netloc == request.headers.get("host"):
            return
    raise _http_error(
        status.HTTP_403_FORBIDDEN,
        PluginError(
            "forbidden_origin", "Plugins can only be managed from dashAI itself"
        ),
    )


def _http_error(status_code: int, error: PluginError) -> HTTPException:
    """An HTTP error whose ``detail`` is a ``PluginErrorInfo``."""
    return HTTPException(status_code=status_code, detail=asdict(error))


router = APIRouter(dependencies=[Depends(_from_dashai)])


def _remote(source: str, location: str, at: Optional[str]) -> dict:
    """Whether its source can update it, its page, owner and files at ``at``."""
    try:
        handler = HANDLERS[PluginSource(source)]
        if handler.can_update:
            return {
                "can_update": True,
                "web_url": handler.web_url(location),
                "owner": handler.owner(location),
                "readme_base": at and handler.readme_base(location, at),
                "readme_links": at and handler.web_url(location, at),
            }
    except (ValueError, SourceError):  # a .source edited by hand
        pass
    return {}


def _response_from_disk(
    storage: PluginStorage,
    registry: ComponentRegistry,
    installer: PluginInstaller,
    plugin_id: str,
    manifest: Optional[PluginManifest],
    index: Optional[StoreIndex],
    active: Dict[str, bool],
    load_errors: Dict[str, str],
) -> InstalledPluginResponse:
    """A plugin as read from disk, a damaged one still with its origin."""
    plugin_dir = storage.plugin_dir(plugin_id)
    enabled = storage.is_enabled(plugin_id)
    try:
        provenance, problem = storage.read_source(plugin_id), None
    except (ValueError, KeyError) as error:
        provenance = None
        problem = ProblemInfo(
            code=PluginProblem.DAMAGED,
            detail=f"Unreadable {storage.SOURCE_MARKER}: {error}",
        )
    origin = {}
    if provenance is not None:
        origin = {
            **provenance._asdict(),
            **_remote(
                provenance.source,
                provenance.location,
                provenance.commit or provenance.ref,
            ),
        }
    retired = provenance and removed_entry(
        index, plugin_id, provenance.source, provenance.location
    )
    origin["removed"] = retired.type if retired else None
    try:  # one unreadable is read again only to say why
        manifest = manifest or PluginManifest.from_file(
            plugin_dir / storage.MANIFEST_FILENAME
        )
    except (ManifestError, OSError) as error:
        return InstalledPluginResponse(
            id=plugin_id,
            name=plugin_id,
            version="",
            enabled=enabled,
            problem=ProblemInfo(
                code=PluginProblem.DAMAGED, detail=f"Unreadable manifest.json: {error}"
            ),
            **origin,
        )
    problem = problem or _problem(
        storage, installer, plugin_id, manifest, enabled, active, load_errors
    )
    return InstalledPluginResponse(
        id=plugin_id,
        name=manifest.name,
        version=manifest.version,
        components=[component.name for component in manifest.components],
        component_types=[component.type for component in manifest.components],
        description=manifest.description,
        dependencies=manifest.dependencies,
        plugin_dependencies=manifest.plugin_dependencies,
        plugin_specifiers=manifest.plugin_specifiers,
        authors=[author.model_dump() for author in manifest.authors],
        project_urls=manifest.project_urls,
        has_settings=manifest.settings is not None,
        enabled=enabled,
        active=problem is None
        and enabled
        and PluginLoader.is_loaded(manifest, registry),
        problem=problem,
        **origin,
    )


def _problem(
    storage: PluginStorage,
    installer: PluginInstaller,
    plugin_id: str,
    manifest: PluginManifest,
    enabled: bool,
    active: Dict[str, bool],
    load_errors: Dict[str, str],
) -> Optional[ProblemInfo]:
    """Why a readable plugin is not working, in ``PluginProblem``'s order."""
    if storage.is_blocked(plugin_id):  # even if disabled, it asks to enable
        return ProblemInfo(
            code=PluginProblem.BLOCKED,
            detail="The plugin store retired it as malicious",
        )
    incompatible, missing = bootstrap.check_requirements(
        manifest, dependencies_directory(storage.root)
    )
    if incompatible:  # checked even if disabled, it could not be enabled
        return ProblemInfo(code=PluginProblem.INCOMPATIBLE, detail=incompatible)
    if missing:  # still missing after startup's repair, which the API waits for
        return ProblemInfo(
            code=PluginProblem.REPAIR_FAILED,
            detail=installer.repair_errors.get(plugin_id)
            or f"Missing dependencies: {', '.join(missing)}",
        )
    if enabled:
        # Active, as a dependency may fail only in the job worker
        if needs := [i for i in manifest.plugin_dependencies if not active.get(i)]:
            return ProblemInfo(
                code=PluginProblem.DEPENDENCY_UNAVAILABLE,
                detail=f"Needs {', '.join(needs)}, not active",
            )
        if wrong := bootstrap.wrong_versions(
            manifest,
            bootstrap.installed_manifests(storage, list(manifest.plugin_specifiers)),
        ):
            return ProblemInfo(
                code=PluginProblem.DEPENDENCY_VERSION,
                detail=f"Needs another version of {', '.join(wrong)}",
                params={"ids": wrong},
            )
        if error := load_errors.get(plugin_id):
            return ProblemInfo(code=PluginProblem.LOAD_FAILED, detail=error)
    if plugin_id in installer.pending_restart:
        return ProblemInfo(
            code=PluginProblem.RESTART_REQUIRED,
            detail="Its new dependencies load here after reopening dashAI",
        )
    return None


def _in_order(
    storage: PluginStorage,
    registry: ComponentRegistry,
    installer: PluginInstaller,
    plugin_ids: List[str],
) -> List[InstalledPluginResponse]:
    """Those plugins in install order, so each sees if its dependencies are active."""
    index = installer.store.read() if installer.store else None
    manifests = bootstrap.installed_manifests(storage, plugin_ids)
    worker_errors = bootstrap.worker_load_errors(storage)
    load_errors = {  # this process's own first, then the job worker's
        **{i: f"In the job worker: {error}" for i, error in worker_errors.items()},
        **bootstrap.load_errors,
    }
    order = bootstrap.install_order(
        {i: manifests[i] for i in plugin_ids if i in manifests}
    )
    active: Dict[str, bool] = {}
    responses = []
    for plugin_id in order + sorted(set(plugin_ids) - set(order)):
        response = _response_from_disk(
            storage,
            registry,
            installer,
            plugin_id,
            manifests.get(plugin_id),
            index,
            active,
            load_errors,
        )
        active[plugin_id] = response.active
        responses.append(response)
    return responses


def _installed_response(plugin_id: str) -> InstalledPluginResponse:
    """The plugin as ``GET /installed`` lists it, built with only what it needs."""
    storage = di["plugin_storage"]
    closure, todo = set(), [plugin_id]
    while todo:
        i = todo.pop()
        if i in closure:
            continue
        found = bootstrap.installed_manifests(storage, [i])
        if i == plugin_id or found:
            closure.add(i)
            todo += found[i].plugin_dependencies if found else []
    responses = _in_order(
        storage, di["component_registry"], di["plugin_installer"], sorted(closure)
    )
    return next(r for r in responses if r.id == plugin_id)


def _require_installed(plugin_id: str) -> None:
    """404 unless ``plugin_id`` is installed (an invalid id is not)."""
    try:
        installed = di["plugin_storage"].is_installed(plugin_id)
    except ValueError:
        installed = False
    if not installed:
        raise _http_error(
            status.HTTP_404_NOT_FOUND,
            PluginError(
                "not_installed", f"Plugin not installed: {plugin_id}", {"id": plugin_id}
            ),
        )


@contextmanager
def _http_errors() -> Iterator[None]:
    """A ``PluginInstallError`` as 409 (busy), 429 (rate limit) or 400."""
    try:
        yield
    except PluginInstallError as error:
        code = {
            PluginBusyError: status.HTTP_409_CONFLICT,
            PluginRateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
        }.get(type(error), status.HTTP_400_BAD_REQUEST)
        raise _http_error(code, error.error) from error


@router.get("/installed", response_model=List[InstalledPluginResponse])
@inject
def list_installed_plugins(  # disk reads would stall the whole API
    storage: PluginStorage = Depends(lambda: di["plugin_storage"]),
    registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
    installer: PluginInstaller = Depends(lambda: di["plugin_installer"]),
):
    return _in_order(storage, registry, installer, storage.list_installed())


@router.get("/{plugin_id}/readme", response_model=Optional[str])
@inject
def get_plugin_readme(
    plugin_id: str, storage: PluginStorage = Depends(lambda: di["plugin_storage"])
):
    _require_installed(plugin_id)
    return read_readme(storage.plugin_dir(plugin_id))


@router.post(
    "/", response_model=InstalledPluginResponse, status_code=status.HTTP_201_CREATED
)
@inject
def install_plugin(
    request: InstallPluginRequest,
    installer: PluginInstaller = Depends(lambda: di["plugin_installer"]),
):
    """Install the very copy a preview reviewed."""
    with _http_errors():
        installed = installer.install_preview(request.preview)
    return _installed_response(installed.id)


@asynccontextmanager
async def _uploaded_zip(file: UploadFile) -> AsyncIterator[Tuple[Path, str]]:
    """The upload in a temp dir, and its original name (recorded in ``.source``)."""
    name = Path(file.filename or "").name
    if not name.lower().endswith(".zip"):
        raise _http_error(
            status.HTTP_400_BAD_REQUEST,
            PluginError("not_a_zip", "Only .zip files are supported"),
        )
    if (file.size or 0) > MAX_PLUGIN_BYTES:
        max_mb = MAX_PLUGIN_BYTES // (1024 * 1024)
        raise _http_error(
            status.HTTP_413_CONTENT_TOO_LARGE,
            PluginError("too_big", f"The zip is over {max_mb} MB", {"max_mb": max_mb}),
        )
    with tempfile.TemporaryDirectory() as tmp_dir:
        # A fixed name, the uploaded one may be invalid here
        zip_path = Path(tmp_dir) / "plugin.zip"
        zip_path.write_bytes(await file.read())
        yield zip_path, name


@router.post("/upload/validate", response_model=PluginValidationResponse)
@inject
async def validate_uploaded_plugin(
    file: UploadFile = File(...),
    installer: PluginInstaller = Depends(lambda: di["plugin_installer"]),
):
    """What installing this ``.zip`` would do, keeping a valid one as ``preview``."""
    async with _uploaded_zip(file) as (zip_path, name):
        with _http_errors():
            return await run_in_threadpool(
                installer.validate,
                PluginSource.LOCAL,
                str(zip_path),
                recorded_location=name,
            )


@router.post("/validate", response_model=PluginValidationResponse)
@inject
def validate_plugin(
    request: ValidatePluginRequest,
    installer: PluginInstaller = Depends(lambda: di["plugin_installer"]),
):
    """Preview an install without changes, keeping a valid one as ``preview``."""
    try:
        source = source_for(request.location)
    except SourceError as error:
        raise _http_error(status.HTTP_400_BAD_REQUEST, error.error) from error
    with _http_errors():
        return installer.validate(source, request.location, ref=request.ref)


@router.get("/updates", response_model=PluginUpdatesResponse)
@inject
def get_plugin_updates(updates: PluginUpdates = Depends(lambda: di["plugin_updates"])):
    """What the last lookup found; never asks a source."""
    return updates.status()


@router.post("/updates/check", response_model=PluginUpdatesResponse)
@inject
def check_plugin_updates(
    updates: PluginUpdates = Depends(lambda: di["plugin_updates"]),
):
    """Read the store again and look up the latest releases now."""
    try:
        return updates.check(force=True)
    except RateLimitError as error:
        raise _http_error(status.HTTP_429_TOO_MANY_REQUESTS, error.error) from error


@router.get("/store", response_model=StoreResponse)
@inject
def get_store(
    store: Optional[PluginStore] = Depends(lambda: di["plugin_store"]),
    updates: PluginUpdates = Depends(lambda: di["plugin_updates"]),
):
    """The store's index as last read, already JSON, never asking a source."""
    if store is None:
        return StoreResponse(checking=False, error=STORE_DISABLED)
    return Response(store.catalog(updates.checking), media_type="application/json")


@router.delete("/previews/{token}", status_code=status.HTTP_204_NO_CONTENT)
@inject
def discard_preview(
    token: str, storage: PluginStorage = Depends(lambda: di["plugin_storage"])
):
    """Drop a preview the dialog closed without installing, if still there."""
    previews.discard(storage.root, token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{plugin_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
def uninstall_plugin(
    plugin_id: str, installer: PluginInstaller = Depends(lambda: di["plugin_installer"])
):
    _require_installed(plugin_id)
    with _http_errors():
        installer.uninstall(plugin_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{plugin_id}/update", response_model=InstalledPluginResponse)
@inject
def update_plugin(
    plugin_id: str,
    request: InstallPluginRequest,
    installer: PluginInstaller = Depends(lambda: di["plugin_installer"]),
):
    """Install a newer release: the one ``/validate``'s ``preview`` reviewed."""
    _require_installed(plugin_id)
    with _http_errors():
        updated = installer.update(plugin_id, preview=request.preview)
    return _installed_response(updated.id)


@router.patch("/{plugin_id}", response_model=InstalledPluginResponse)
@inject
def set_plugin_enabled(
    plugin_id: str,
    request: SetEnabledRequest,
    installer: PluginInstaller = Depends(lambda: di["plugin_installer"]),
):
    _require_installed(plugin_id)
    with _http_errors():
        if request.enabled:
            installer.enable(plugin_id, allow_blocked=request.allow_blocked)
        else:
            installer.disable(plugin_id)
    return _installed_response(plugin_id)


def _settings_class(storage: PluginStorage, plugin_id: str) -> type:
    """The plugin's settings class, editable only while the plugin is active."""
    _require_installed(plugin_id)

    def unavailable(detail: str) -> HTTPException:
        return _http_error(
            status.HTTP_409_CONFLICT,
            PluginError("settings_unavailable", detail, {"id": plugin_id}),
        )

    try:
        manifest = PluginManifest.from_file(
            storage.plugin_dir(plugin_id) / storage.MANIFEST_FILENAME
        )
    except (ManifestError, OSError) as error:
        raise unavailable(f"Unreadable manifest.json: {error}") from error
    if manifest.settings is None:
        raise _http_error(
            status.HTTP_404_NOT_FOUND,
            PluginError(
                "no_settings", f"Plugin {plugin_id} has no settings", {"id": plugin_id}
            ),
        )
    # Checked first, as sys.modules keeps a disabled or outdated plugin's code
    if not _installed_response(plugin_id).active:
        raise unavailable(f"Plugin {plugin_id} is not active")
    return PluginLoader.settings_class(manifest)


@router.get("/{plugin_id}/settings", response_model=PluginSettingsResponse)
@inject
def get_plugin_settings(
    plugin_id: str,
    accept_language: str | None = Header(default=None),
    storage: PluginStorage = Depends(lambda: di["plugin_storage"]),
    registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
):
    """The settings form's schema and saved values."""
    settings_class = _settings_class(storage, plugin_id)
    saved = plugin_settings.read(plugin_settings.settings_file(storage.root, plugin_id))
    return PluginSettingsResponse(
        schema=localize(
            plugin_settings.schema(settings_class, registry), accept_language
        ),
        values=plugin_settings.clean(settings_class, saved, registry),
    )


@router.put("/{plugin_id}/settings", response_model=PluginSettingsValues)
@inject
def save_plugin_settings(
    plugin_id: str,
    request: PluginSettingsValues,
    storage: PluginStorage = Depends(lambda: di["plugin_storage"]),
    registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
):
    """Save the form's values, returning the non-default ones kept."""
    settings_class = _settings_class(storage, plugin_id)
    try:
        values = plugin_settings.changed(settings_class, request.values, registry)
    except plugin_settings.InvalidSettingsError as error:
        raise _http_error(status.HTTP_422_UNPROCESSABLE_CONTENT, error.error) from error
    plugin_settings.save(plugin_settings.settings_file(storage.root, plugin_id), values)
    return PluginSettingsValues(values=values)

"""Store index copy, signed when on GitHub and never older."""

import gc
import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from functools import cached_property
from typing import Annotated, Callable, Dict, Hashable, List, Literal, Optional, Tuple

import httpx
from packaging.version import InvalidVersion
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from DashAI.back.core.enums.plugin_source import PluginSource
from DashAI.back.plugins.bootstrap import installed_manifests, wrong_versions
from DashAI.back.plugins.disk.storage import PluginStorage
from DashAI.back.plugins.disk.trash import write_file, write_json
from DashAI.back.plugins.manifest.manifest import (
    PLUGIN_ID,
    in_range,
    split_plugin_dependencies,
)
from DashAI.back.plugins.manifest.validator import PluginValidator
from DashAI.back.plugins.sources import HANDLERS, trust_level
from DashAI.back.plugins.sources.base import MAX_PLUGIN_BYTES, SourceError
from DashAI.back.plugins.sources.github_source import _verify_with_sigstore

logger = logging.getLogger(__name__)

STORE_FILE = ".store.json"  # url, etag, checked_at, error
INDEX_FILE = ".store-index.json"  # the index as downloaded
INDEX_URL_VARIABLE = "DASHAI_PLUGIN_INDEX_URL"
DEFAULT_INDEX_URL: Optional[str] = None  # no store unless the variable names one
_GITHUB_INDEX = re.compile(
    r"https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/index\.json"
)
_MAX_INDEX_BYTES = 50 * 1024 * 1024
_TIMEOUT_SECONDS = 5  # opening dashAI never waits long for the store

OFFLINE = "offline"  # no connection, a timeout or the host failing (5xx)
RATE_LIMITED = "rate_limited"
INVALID_STORE = "invalid_store"  # not an index this dashAI reads
UNVERIFIED_STORE = "unverified_store"  # the bot's signature is missing or wrong
STORE_DISABLED = "disabled"  # no index URL, so no store


def index_url() -> Optional[str]:
    return os.getenv(INDEX_URL_VARIABLE) or DEFAULT_INDEX_URL


def _signer(url: str) -> Optional[Tuple[str, str, str]]:
    """Repo, ref and workflow that sign a GitHub index: its build.yml bot."""
    match = _GITHUB_INDEX.fullmatch(url)
    if match is None:
        return None
    owner, repo, branch = match.groups()
    repo_uri, ref = f"https://github.com/{owner}/{repo}", f"refs/heads/{branch}"
    return repo_uri, ref, f"{repo_uri}/.github/workflows/build.yml@{ref}"


def _parse(raw: bytes) -> "StoreIndex":
    """The index in ``raw``, the cycle collector paused (half the time at 10k)."""
    enabled = gc.isenabled()
    gc.disable()
    try:
        return StoreIndex.model_validate(json.loads(raw))
    finally:
        if enabled:
            gc.enable()


def _instant(value: str) -> datetime:
    """A ``built_at`` as a moment (one without a zone: UTC), to compare."""
    when = datetime.fromisoformat(value)
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def _link(value: str) -> str:
    """The front shows it as a link: http(s) only."""
    if value and not value.startswith(("http://", "https://")):
        raise ValueError(f"not an http(s) link: {value}")
    return value


def _plugin_id(value: str) -> str:
    if not PLUGIN_ID.fullmatch(value):  # the manifest's own rule
        raise ValueError(f"not a plugin id: {value}")
    return value


PluginId = Annotated[str, AfterValidator(_plugin_id)]


def _https(value: str) -> str:
    if not value.startswith("https://"):
        raise ValueError(f"not an https link: {value}")
    return value


class Artifact(BaseModel):
    """What installing downloads, a release ``asset`` or the code at its commit."""

    kind: Literal["asset", "source"]
    url: Optional[str] = None
    size: Optional[int] = None  # the download stops there

    @model_validator(mode="before")
    @classmethod
    def _source_has_no_file(cls, data):
        if isinstance(data, dict) and data.get("kind") == "source":
            return {"kind": "source"}
        return data

    @model_validator(mode="after")
    def _asset(self):
        if self.kind == "asset":
            _https(self.url or "")
            if not self.size or not 0 < self.size <= MAX_PLUGIN_BYTES:
                raise ValueError(f"not a release file size: {self.size}")
        return self


class Attestation(BaseModel):
    """The release file's signature, a separate file the source verifies."""

    bundle_url: Annotated[str, AfterValidator(_https)]


class StoreRelease(BaseModel):
    tag: str
    version: str
    min_app_version: str
    trust_level: str  # as the bot's review found it, installing never gives less
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")  # installing compares it
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")  # the README is read there
    published_at: str
    dependencies: List[str] = []
    plugin_dependencies: List[str] = []  # the manifest's, other plugins' ids
    plugin_specifiers: Dict[str, str] = {}
    workflow: Optional[str] = None  # the workflow that built it, if attested
    signed_at: Optional[str] = None
    artifact: Optional[Artifact] = None  # in an older index, fetched through the API
    attestation: Optional[Attestation] = None

    _split_plugin_dependencies = model_validator(mode="before")(
        split_plugin_dependencies
    )


class StoreAuthor(BaseModel):
    name: str = ""
    email: str = ""
    url: Annotated[str, AfterValidator(_link)] = ""


class StoreEntry(BaseModel):
    id: PluginId
    source: PluginSource
    location: str  # where its source fetches it from (a GitHub repo)
    name: str
    description: str = ""
    authors: List[StoreAuthor] = []
    components: List[str] = []
    component_types: List[str] = []  # same order as components
    releases: List[StoreRelease] = Field(min_length=1)  # newest first
    project_urls: Dict[str, Annotated[str, AfterValidator(_link)]] = {}
    license: Optional[str] = None  # the repo's, as an SPDX id

    @field_validator("location")
    @classmethod
    def _own_location(cls, value: str, info: ValidationInfo) -> str:
        # Where installing fetches from, so a source that can update
        if "source" in info.data:
            HANDLERS[info.data["source"]].key(value)
        return value


Removed = Literal["withdrawn", "unmaintained", "critical"]


class RemovedEntry(BaseModel):
    """A plugin the store retired, with generic notices."""

    id: str
    source: PluginSource = PluginSource.GIT
    location: str  # as its plugin's entry names it
    type: Removed
    date: str  # a new critical entry blocks again what the user allowed

    @model_validator(mode="before")
    @classmethod
    def _repo(cls, data):
        """The GitHub-only index names the repo as ``repo`` (owner/name)."""
        if isinstance(data, dict) and "location" not in data and "repo" in data:
            return {**data, "location": f"https://github.com/{data['repo']}"}
        return data


class RevokedRelease(BaseModel):
    """A release revoked by its bytes, blocked wherever it is installed."""

    id: PluginId
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    date: str  # as RemovedEntry's


class StoreIndex(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_version: Literal[1] = Field(alias="schema")
    built_at: str  # when what the store lists last changed
    plugins: List[StoreEntry] = []
    removed: List[RemovedEntry] = []
    revoked: List[RevokedRelease] = []

    @field_validator("built_at")
    @classmethod
    def _when(cls, value: str) -> str:
        datetime.fromisoformat(value)  # compared with the copy's
        return value

    @field_validator("plugins", "removed", "revoked", mode="before")
    @classmethod
    def _skip_bad_entries(cls, value, info):
        """Leave out only a bad or repeated entry, keeping the rest."""
        if not isinstance(value, list):
            raise ValueError(f"{info.field_name} must be a list")
        model = {
            "plugins": StoreEntry,
            "removed": RemovedEntry,
            "revoked": RevokedRelease,
        }[info.field_name]
        entries: Dict[object, BaseModel] = {}
        for number, item in enumerate(value):
            try:
                entry = model.model_validate(item)
            except (ValidationError, SourceError) as error:
                logger.warning("Store entry left out: %s", error)
                continue
            entries.setdefault(entry.id if model is StoreEntry else number, entry)
        return list(entries.values())

    @model_validator(mode="after")
    def _not_revoked(self):
        """Drop revoked releases, and entries left without any."""
        revoked = {(item.id, item.sha256) for item in self.revoked}
        for entry in self.plugins:
            entry.releases = [
                release
                for release in entry.releases
                if (entry.id, release.sha256) not in revoked
            ]
        self.plugins = [entry for entry in self.plugins if entry.releases]
        return self


def origin_key(
    source: Optional[str], location: Optional[str]
) -> Optional[Tuple[PluginSource, Hashable]]:
    """A plugin's origin as its source compares locations, None if not updatable."""
    try:
        source = PluginSource(source)
        handler = HANDLERS[source]
        return (source, handler.key(location or "")) if handler.can_update else None
    except (ValueError, SourceError):
        return None


def _same_origin(entries, plugin_id, source, location):
    """The entry with this id **and** origin."""
    origin = origin_key(source, location)
    for entry in entries if origin else ():
        if entry.id == plugin_id and origin_key(entry.source, entry.location) == origin:
            return entry
    return None


def store_entry(
    index: Optional[StoreIndex],
    plugin_id: str,
    source: Optional[str],
    location: Optional[str],
) -> Optional[StoreEntry]:
    """The store's entry for an installed plugin."""
    return index and _same_origin(index.plugins, plugin_id, source, location)


def listed_release(
    index: Optional[StoreIndex],
    source: Optional[str],
    location: Optional[str],
    tag: Optional[str],
) -> Optional[Tuple[StoreEntry, StoreRelease]]:
    """The store's entry for this origin and its release ``tag``, if listed."""
    origin = origin_key(source, location)
    if index is None or origin is None or tag is None:
        return None
    for entry in index.plugins:
        if origin_key(entry.source, entry.location) == origin:
            release = next((r for r in entry.releases if r.tag == tag), None)
            return (entry, release) if release else None
    return None


def removed_entry(
    index: Optional[StoreIndex],
    plugin_id: str,
    source: Optional[str],
    location: Optional[str],
) -> Optional[RemovedEntry]:
    """The store's retirement of an installed plugin."""
    return index and _same_origin(index.removed, plugin_id, source, location)


def revoked_release(
    index: Optional[StoreIndex], plugin_id: str, sha256: Optional[str]
) -> Optional[RevokedRelease]:
    """The store's revocation of these bytes of a plugin, if any."""
    for item in index.revoked if index else ():
        if item.id == plugin_id and item.sha256 == sha256:
            return item
    return None


def offered_release(
    entry: StoreEntry, app_version: Optional[str] = None, spec: Optional[str] = None
) -> Optional[StoreRelease]:
    """The newest release this dashAI can run, or None."""
    for release in entry.releases:
        if not in_range(release.version, spec):
            continue
        try:
            too_old = PluginValidator.check_app_version(
                release.min_app_version, app_version
            )
        except InvalidVersion:
            continue
        if too_old is None:
            return release
    return None


class PluginStore:
    def __init__(
        self,
        storage: PluginStorage,
        url: Optional[str] = None,
        client: Optional[httpx.Client] = None,
        verify: Callable[..., bytes] = _verify_with_sigstore,
    ):
        self.storage = storage
        self.url = url or index_url()
        if client is not None:
            self._client = client
        self._verify = verify
        # both files' mtime and size, STORE_FILE, index, each entry's JSON or None
        self._copy: tuple = (None, {}, None, None)

    @cached_property
    def _client(self) -> httpx.Client:
        """Made on first use, loading its certificates takes ~0.2 s."""
        return httpx.Client(follow_redirects=True, timeout=_TIMEOUT_SECONDS)

    def _stamp(self) -> tuple:
        stamp = []
        for name in (STORE_FILE, INDEX_FILE):
            try:
                stat = (self.storage.root / name).stat()
                stamp.append((stat.st_mtime_ns, stat.st_size))
            except OSError:
                stamp.append(None)
        return tuple(stamp)

    def _read_file(self) -> dict:
        try:
            data = json.loads((self.storage.root / STORE_FILE).read_text("utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _read(self) -> Tuple[dict, Optional[StoreIndex]]:
        """The copy and its index, parsed again only when a file changed."""
        stamp = self._stamp()
        if stamp != self._copy[0]:
            data = self._read_file()
            data.pop("index", None)
            try:
                index = _parse((self.storage.root / INDEX_FILE).read_bytes())
            except (OSError, ValueError):  # absent or unreadable
                index = None
            self._copy = (stamp, data, index, None)
        copy = self._copy  # one copy, even if a reading replaces it meanwhile
        return copy[1], copy[2]

    def read(self) -> Optional[StoreIndex]:
        return self._read()[1]

    def status(self) -> dict:
        """When it was last read and, if the last reading failed, why."""
        data = self._read()[0]
        return {"checked_at": data.get("checked_at"), "error": data.get("error")}

    def refresh(self) -> Optional[str]:
        """Refetch the index, returning why it failed or None. Not thread safe."""
        data, old = self._read()
        data = dict(data)
        same = old if data.get("url") == self.url else None
        etag = data.get("etag") if same is not None else None
        index = None
        try:
            index, raw, etag = self._fetch(etag, same)
        except _StoreError as error:
            logger.warning("Could not read the plugin store: %s", error)
            data["error"] = error.code
        else:
            data.update(
                url=self.url,
                etag=etag,
                checked_at=datetime.now(timezone.utc).isoformat(),
                error=None,
            )
        try:
            self.storage.root.mkdir(parents=True, exist_ok=True)
            # As downloaded (a newer dashAI may read more), before the etag naming it
            if index is not None:
                write_file(self.storage.root / INDEX_FILE, raw)
            write_json(self.storage.root / STORE_FILE, data)
        except OSError as error:
            logger.warning("Could not save the plugin store: %s", error)
        else:
            # Unchanged (304, or it failed), so the entries' JSON already made holds.
            made = self._copy[3] if index is None and self._copy[2] is old else None
            self._copy = (self._stamp(), data, index or old, made)
        self.catalog()  # built here in the background, ready when the page asks
        return data["error"]

    def _fetch(
        self, etag: Optional[str], old: Optional[StoreIndex]
    ) -> Tuple[Optional[StoreIndex], Optional[bytes], Optional[str]]:
        """``(index, its bytes, etag)``, Nones if unchanged, never older than old."""
        headers = {"If-None-Match": etag} if etag else {}
        try:
            with self._client.stream("GET", self.url, headers=headers) as response:
                if response.status_code == 304:
                    return None, None, etag
                if response.status_code == 429:
                    raise _StoreError(RATE_LIMITED, "rate limited")
                if response.status_code >= 500:
                    raise _StoreError(OFFLINE, f"HTTP {response.status_code}")
                if response.status_code != 200:
                    raise _StoreError(INVALID_STORE, f"HTTP {response.status_code}")
                body = bytearray()
                for chunk in response.iter_bytes():
                    body += chunk
                    if len(body) > _MAX_INDEX_BYTES:
                        raise _StoreError(INVALID_STORE, "over 50 MB")
                new_etag = response.headers.get("etag")
        except httpx.HTTPError as error:
            raise _StoreError(OFFLINE, str(error)) from error
        signer = _signer(self.url)
        if signer:
            self._check_signature(body, signer)
        else:
            logger.warning("Plugin store %s: its signature is not checked", self.url)
        try:
            index = _parse(body)
        except ValueError as error:  # not JSON, or not an index (ValidationError)
            raise _StoreError(INVALID_STORE, str(error)) from error
        if old is not None and _instant(index.built_at) < _instant(old.built_at):
            raise _StoreError(
                INVALID_STORE, f"built {index.built_at}, before the copy's"
            )
        return index, body, new_etag

    def _check_signature(self, body: bytes, signer: Tuple[str, str, str]) -> None:
        """Raises unless the bundle next to the index signs these bytes."""
        try:
            response = self._client.get(self.url + ".sigstore.json")
        except httpx.HTTPError as error:
            raise _StoreError(OFFLINE, str(error)) from error
        if response.status_code != 200:
            code = OFFLINE if response.status_code >= 500 else UNVERIFIED_STORE
            raise _StoreError(code, f"signature: HTTP {response.status_code}")
        try:
            statement = json.loads(self._verify(response.json(), *signer))
            signed = {s["digest"]["sha256"] for s in statement["subject"]}
        except Exception as error:  # noqa: BLE001 (any failure, not the bot's)
            raise _StoreError(UNVERIFIED_STORE, f"signature: {error}") from error
        if hashlib.sha256(body).hexdigest() not in signed:
            raise _StoreError(UNVERIFIED_STORE, "signature of another index")

    @staticmethod
    def _entry_json(entry: StoreEntry, installed: Optional[tuple] = None) -> str:
        """An entry as ``StoreEntryResponse``, ``installed`` its local origin."""
        origin = origin_key(entry.source, entry.location)
        handler = HANDLERS[entry.source]
        offered = offered_release(entry)
        plugin = entry.model_dump(
            mode="json", exclude={"releases": {"__all__": {"artifact", "attestation"}}}
        )
        for release in plugin["releases"]:
            release["trust_tier"] = trust_level(release["trust_level"]).tier
        here = installed != ()
        commit = (offered or entry.releases[0]).commit
        plugin.update(
            installed=here and installed == origin,
            installed_other=here and installed != origin,
            offered=offered.tag if offered else None,
            official=handler.official(entry.location),
            owner=handler.owner(entry.location),
            web_url=handler.web_url(entry.location),
            readme_base=handler.readme_base(entry.location, commit),
            readme_links=handler.web_url(entry.location, commit),
        )
        return json.dumps(plugin, ensure_ascii=False)

    def catalog(self, checking: bool = False) -> str:
        """The copy as ``StoreResponse`` JSON, cached, installed entries rebuilt."""
        self._read()
        stamp, data, index, made = copy = self._copy
        plugins = index.plugins if index else []
        if made is None:
            made = [self._entry_json(entry, ()) for entry in plugins]
            if self._copy is copy:
                self._copy = (stamp, data, index, made)
        parts = list(made)
        installed = self._installed_origins()
        manifests = installed_manifests(self.storage, list(installed))
        entries = {entry.id: entry for entry in plugins}
        wrong = {}
        for number, entry in enumerate(plugins):
            if entry.id in installed:
                parts[number] = self._entry_json(entry, installed[entry.id])
            offered = offered_release(entry)
            if offered and (
                ids := wrong_versions(offered, manifests)
                + [
                    i
                    for i, spec in offered.plugin_specifiers.items()
                    if i not in manifests
                    and i in entries
                    and not offered_release(entries[i], spec=spec)
                ]
            ):
                wrong[entry.id] = ids
        head = {
            "checking": checking,
            "checked_at": data.get("checked_at"),
            "error": data.get("error"),
            "built_at": index.built_at if index else None,
            "wrong_versions": wrong,
        }
        return json.dumps(head)[:-1] + ', "plugins": [' + ", ".join(parts) + "]}"

    def _installed_origins(self) -> Dict[str, Optional[tuple]]:
        """Installed id -> its origin (None: a .zip, or unreadable)."""
        origins = {}
        for plugin_id in self.storage.list_installed():
            try:
                provenance = self.storage.read_source(plugin_id)
            except (ValueError, KeyError):
                provenance = None
            origins[plugin_id] = provenance and origin_key(
                provenance.source, provenance.location
            )
        return origins


class _StoreError(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code

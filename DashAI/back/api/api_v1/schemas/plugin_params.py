from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field

from DashAI.back.plugins.disk.previews import TOKEN
from DashAI.back.plugins.sources import trust_level as _trust_level
from DashAI.back.plugins.sources.base import TrustTier
from DashAI.back.plugins.sources.local_source import UNKNOWN
from DashAI.back.plugins.store.store import Removed


class TrustInfo(BaseModel):
    """A trust level and its tier on the scale shared by every source."""

    trust_level: str | None = None

    @computed_field
    @property
    def trust_tier(self) -> TrustTier:
        return _trust_level(self.trust_level).tier


class ValidatePluginRequest(BaseModel):
    location: str
    ref: str | None = None  # a release tag, None for the latest


class InstallPluginRequest(BaseModel):
    # A preview's token, to install or update that very copy.
    preview: str = Field(pattern=TOKEN)


class SetEnabledRequest(BaseModel):
    enabled: bool
    # Run it although the store retired it as malicious (the user confirmed).
    allow_blocked: bool = False


class PluginErrorInfo(BaseModel):
    """A failed preview or operation (also the ``detail`` of an HTTP error)."""

    code: str
    detail: str
    params: dict[str, Any] = {}  # what the message needs (versions, names, MB...)


class AuthorInfo(BaseModel):
    name: str = ""
    email: str = ""
    url: str = ""


class PluginDependencyInfo(BaseModel):
    """A plugin the previewed one needs, in install order."""

    id: str
    name: str  # its manifest's or the store's
    state: Literal["active", "disabled", "store"]
    location: str | None = None  # the repo to preview (store)
    ref: str | None = None  # its offered tag (store)
    latest: str | None = None  # its newest tag, if it needs a newer dashAI (store)


class PluginValidationResponse(TrustInfo):
    is_valid: bool
    errors: list[PluginErrorInfo] = []
    ref: str | None = None  # remote tag validated, None for local
    id: str | None = None  # None if the manifest could not be read
    version: str | None = None
    name: str | None = None  # None if the manifest could not be read
    description: str = ""
    dependencies: list[str] = []  # pip requirements, as declared
    # The plugins it needs and the ones those need, in install order.
    plugin_dependencies: list[PluginDependencyInfo] = []
    breaks: list[str] = []
    authors: list[AuthorInfo] = []
    project_urls: dict[str, str] = {}
    readme: str | None = None
    installed_version: str | None = None  # None if it is a new install
    # Than the installed one (PEP 440), None if it is a new install.
    version_change: Literal["newer", "same", "older"] | None = None
    installed_location: str | None = None  # where the installed one came from
    # Decided by the back (the level, or a replacement at a lower tier).
    needs_ack: bool = True
    verified: bool = False
    sha256: str | None = None  # of the downloaded file (recorded in .source)
    # Token to install this very copy via POST / or /{id}/update, None if invalid
    preview: str | None = None
    removed: Removed | None = None  # the store retired it (critical means blocked)
    owner: str | None = None  # who publishes it by its source, None for a .zip
    in_store: bool = False  # the store lists this id from this same origin
    # Replaces an installed plugin with its id from another origin
    replaces_other: bool = False


class PluginProblem(str, Enum):
    """Why a plugin isn't working, the first listed when several apply."""

    DAMAGED = "damaged"  # its manifest.json or .source can't be read
    BLOCKED = "blocked"  # the store retired it as malicious
    INCOMPATIBLE = "incompatible"  # needs another dashAI or a package version
    REPAIR_FAILED = "repair_failed"  # dependencies missing after startup's repair
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"  # a plugin it needs is not active
    DEPENDENCY_VERSION = "dependency_version"
    LOAD_FAILED = "load_failed"  # its code fails to load (here or in jobs)
    RESTART_REQUIRED = "restart_required"  # usable here after reopening dashAI


class ProblemInfo(BaseModel):
    code: PluginProblem  # the front shows its message for this
    detail: str  # technical, in English
    params: dict = {}


class PluginUpdatesResponse(BaseModel):
    checking: bool  # a lookup is running, ask again in a few seconds
    # Lookups that blocked or unblocked a plugin, the front reloads when it grows
    blocked_changes: int = 0
    checked_at: str | None = None  # of the last full lookup (ISO, UTC)
    updates: dict[str, str] = {}  # plugin id -> its newer release's tag
    errors: dict[str, str] = {}  # plugin id -> rate_limited | not_found | offline
    # Store plugin id -> its newest release's tag, which needs a newer dashAI.
    needs_newer_dashai: dict[str, str] = {}
    # offline | rate_limited | invalid_store | unverified_store
    store_error: str | None = None


class StoreReleaseResponse(TrustInfo):
    tag: str
    version: str
    min_app_version: str
    sha256: str  # of the reviewed file, installing compares it
    commit: str  # the reviewed commit, where the README is read
    published_at: str
    dependencies: list[str] = []
    plugin_dependencies: list[str] = []  # other plugins' ids
    plugin_specifiers: dict[str, str] = {}
    workflow: str | None = None  # the workflow that built it, if attested
    signed_at: str | None = None


class StoreEntryResponse(BaseModel):
    """An entry of the store's index, plus what the back decides about it."""

    id: str
    source: str  # a PluginSource that can update ("git")
    location: str  # where it is fetched from (a GitHub repo)
    name: str
    description: str = ""
    authors: list[AuthorInfo] = []
    components: list[str] = []
    component_types: list[str] = []  # same order as `components`
    releases: list[StoreReleaseResponse]  # newest first
    project_urls: dict[str, str] = {}
    license: str | None = None  # the repo's, as an SPDX id
    installed: bool  # installed here with the same id and repo
    installed_other: bool  # another plugin with this id is installed
    offered: str | None  # tag of the newest release this dashAI runs
    official: bool  # from a DashAISoftware repo
    owner: str  # who publishes it, by its source
    web_url: str  # its repo's page
    # The offered release's README folder and where its relative links go
    readme_base: str
    readme_links: str


class StoreResponse(BaseModel):
    checking: bool  # reading it again, ask again in a few seconds
    checked_at: str | None = None  # last successful reading (ISO, UTC)
    error: str | None = None  # why it has no reading (offline, disabled...)
    built_at: str | None = None  # when the store last changed, None if no copy
    wrong_versions: dict[str, list[str]] = {}
    plugins: list[StoreEntryResponse] = []


class InstalledPluginResponse(TrustInfo):
    id: str
    name: str
    version: str
    components: list[str] = []
    component_types: list[str] = []  # same order as `components`
    description: str = ""
    dependencies: list[str] = []  # pip requirements, as declared
    plugin_dependencies: list[str] = []  # other plugins' ids, as declared
    plugin_specifiers: dict[str, str] = {}
    authors: list[AuthorInfo] = []
    project_urls: dict[str, str] = {}  # label -> http(s) URL
    has_settings: bool = False  # its manifest names a settings class
    enabled: bool  # the user's choice, kept while a problem lasts
    # Enabled, registered and without a problem, what the front shows as on
    active: bool = False
    source: str | None = None  # "local" | "git"
    location: str | None = None  # GitHub repo URL, or the uploaded .zip's name
    # Its source has newer releases to offer (not a .zip), then its page and owner.
    can_update: bool = False
    web_url: str | None = None
    owner: str | None = None
    # Its files at the installed commit, for the README's relative URLs
    readme_base: str | None = None
    readme_links: str | None = None
    ref: str | None = None  # GitHub tag, None for local
    trust_level: str = UNKNOWN.name  # a source's level (sources/)
    verified: bool = False  # from a DashAISoftware repo
    sha256: str | None = None  # of the installed file, None for a folder
    commit: str | None = None  # None for local or an unattested asset
    asset: str | None = None  # the GitHub release file's name
    # From an accepted attestation (tier "attested"), what built it and when.
    workflow: str | None = None
    signed_at: str | None = None  # ISO 8601, UTC
    issuer: str | None = None  # who vouched for the signer
    problem: ProblemInfo | None = None  # None if it works when enabled
    removed: Removed | None = None  # the store retired it (same id and repo)
    # ISO 8601 UTC. First install of this id (kept on updates) and this copy's.
    installed_at: str | None = None
    updated_at: str | None = None


class PluginSettingsValues(BaseModel):
    # What the settings form sent, in the format it takes back as is.
    values: dict[str, Any]


class PluginSettingsResponse(PluginSettingsValues):
    # The form's JSON schema, localized. "schema" would shadow BaseModel.schema.
    json_schema: dict[str, Any] = Field(alias="schema")

"""What every plugin source provides. The set is closed: plugins can't add one."""

from contextlib import AbstractContextManager
from enum import Enum
from pathlib import Path
from typing import Hashable, NamedTuple, Optional, Protocol, Tuple, runtime_checkable

from DashAI.back.plugins.errors import CodedError

MAX_PLUGIN_BYTES = 200 * 1024 * 1024


class SourceError(CodedError):
    """A plugin could not be fetched."""

    code = "fetch_failed"


class RateLimitError(SourceError):
    """The source refuses more requests for now (e.g. GitHub's hourly limit)."""

    code = "rate_limited"


class NotFoundError(SourceError):
    """The source has no such plugin, or no published release of it."""

    code = "not_found"


def check_size(total_bytes: int, what: str) -> None:
    """Refuse before downloading or extracting what is too big (zip bombs)."""
    if total_bytes > MAX_PLUGIN_BYTES:
        max_mb = MAX_PLUGIN_BYTES // (1024 * 1024)
        raise SourceError(
            f"{what} is too big (over {max_mb} MB)", "too_big", max_mb=max_mb
        )


class TrustTier(str, Enum):
    """Traceability to a public source, most first, shared by every source."""

    ATTESTED = "attested"  # a file the repo's CI built and signed for that version
    SOURCE = "source"  # the repo's code at a pinned commit
    UNVERIFIED = "unverified"  # a downloaded file whose build can't be checked
    LOCAL = "local"  # uploaded by hand
    UNKNOWN = "unknown"  # not recorded (a folder copied by hand)

    @property
    def needs_ack(self) -> bool:
        """Installing asks "I understand the risk" first."""
        return self in (TrustTier.UNVERIFIED, TrustTier.LOCAL, TrustTier.UNKNOWN)

    def is_below(self, other: "TrustTier") -> bool:
        order = list(TrustTier)
        return order.index(self) > order.index(other)


class TrustLevel(NamedTuple):
    """A source's trust level, its name (front ``trust.<name>``) and tier."""

    name: str
    tier: TrustTier


class Fetched(NamedTuple):
    path: Path  # folder with manifest.json, removed when the fetch closes
    ref: Optional[str]  # GitHub tag, None for local
    trust_level: str  # the name of one of the source's ``trust_levels``
    verified: bool
    sha256: Optional[str]  # of the downloaded file, None for a folder
    commit: Optional[str]
    asset: Optional[str] = None  # the release file's name, None for source code
    # Attested build workflow, signing time and the signer's OIDC issuer
    workflow: Optional[str] = None
    signed_at: Optional[str] = None  # ISO 8601, UTC
    issuer: Optional[str] = None


@runtime_checkable
class PluginSourceHandler(Protocol):
    can_update: bool  # has somewhere to fetch a newer version from
    trust_levels: Tuple[TrustLevel, ...]  # every level its ``fetch`` may give

    def fetch(
        self, location: str, ref: Optional[str] = None
    ) -> AbstractContextManager[Fetched]: ...

    # Only called on a source that ``can_update``, with a location of its own.

    def fetch_listed(
        self,
        location: str,
        tag: str,
        *,
        kind: str,
        sha256: str,
        commit: str,
        url: Optional[str] = None,
        size: Optional[int] = None,
        bundle_url: Optional[str] = None,
    ) -> AbstractContextManager[Fetched]:
        """Download a release as the store's index lists it, checked by ``sha256``."""

    def key(self, location: str) -> Hashable:
        """The origin's identity, ``SourceError`` if not this source's."""

    def latest_tag(
        self, location: str, etag: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """``(tag, etag)`` of the latest release, tag None if unchanged."""

    def web_url(self, location: str, commit: Optional[str] = None) -> str:
        """Where a person browses it (its files at ``commit``, if given)."""

    def readme_base(self, location: str, commit: str) -> str:
        """The URL of its raw files at ``commit``, for the README and images."""

    def owner(self, location: str) -> str:
        """Who publishes it, as the front shows it when there is no author."""

    def official(self, location: str) -> bool:
        """Published by DashAISoftware, as this source can tell."""

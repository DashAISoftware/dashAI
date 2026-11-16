"""Plugin sources by ``PluginSource``, with their handlers in ``HANDLERS``."""

from typing import Callable, Dict, Iterable, Optional, Type

from DashAI.back.core.enums.plugin_source import PluginSource
from DashAI.back.plugins.sources.base import (
    PluginSourceHandler,
    SourceError,
    TrustLevel,
)
from DashAI.back.plugins.sources.github_source import GitHubSource
from DashAI.back.plugins.sources.local_source import UNKNOWN, LocalSource

HANDLERS: Dict[PluginSource, Type[PluginSourceHandler]] = {
    PluginSource.LOCAL: LocalSource,
    PluginSource.GIT: GitHubSource,
}


def default_sources(
    github_token: Callable[[], Optional[str]] = lambda: None,
) -> Dict[PluginSource, PluginSourceHandler]:
    return {
        PluginSource.LOCAL: LocalSource(),
        PluginSource.GIT: GitHubSource(token=github_token),
    }


def source_for(location: str) -> PluginSource:
    """The first updatable source that owns a typed location (a repo URL)."""
    for source, handler in HANDLERS.items():
        if not handler.can_update:
            continue
        try:
            handler.key(location)
        except SourceError:
            continue
        return source
    raise SourceError(f"No plugin source takes {location}", "invalid_location")


def _index(handlers: Iterable[Type[PluginSourceHandler]]) -> Dict[str, TrustLevel]:
    """Every source's levels by name, failing at startup on a duplicate."""
    levels: Dict[str, TrustLevel] = {}
    for handler in handlers:
        for level in handler.trust_levels:
            if level.name in levels:
                raise ValueError(f"Trust level declared twice: {level.name}")
            levels[level.name] = level
    return levels


_LEVELS = _index(HANDLERS.values())


def trust_level(name: Optional[str]) -> TrustLevel:
    """The level called ``name``, else UNKNOWN."""
    return _LEVELS.get(name or "", UNKNOWN)


def needs_ack(name: Optional[str], installed: Optional[str] = None) -> bool:
    """Whether level ``name`` asks "I understand the risk" or lowers a tier."""
    tier = trust_level(name).tier
    return tier.needs_ack or (
        installed is not None and tier.is_below(trust_level(installed).tier)
    )

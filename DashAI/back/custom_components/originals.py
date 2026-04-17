"""In-memory cache of built-in / plugin component classes.

The editor lets users override any component registered at startup (core or
plugin). To support reverting an override, we capture the original class
objects before any user-authored override is applied. The cache is scoped to
a single process, so every process that wants to revert must snapshot its
own registry.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Type

logger = logging.getLogger(__name__)

_originals: Dict[str, Type] = {}
_snapshotted = False


def snapshot_originals(registry) -> None:
    """Freeze the current registry contents as the "original" component set.

    Safe to call multiple times; subsequent calls are no-ops. Must be called
    after built-in and plugin components are registered but BEFORE any
    custom-component override is applied.
    """
    global _snapshotted
    if _snapshotted:
        return
    for type_registry in registry.registry.values():
        for component_name, entry in type_registry.items():
            _originals[component_name] = entry["class"]
    _snapshotted = True
    logger.info(
        "Snapshotted %d original components for override/revert support.",
        len(_originals),
    )


def get_original(class_name: str) -> Optional[Type]:
    """Return the original class for `class_name` or None if not snapshotted."""
    return _originals.get(class_name)


def has_original(class_name: str) -> bool:
    return class_name in _originals


def is_snapshotted() -> bool:
    return _snapshotted


def reset_snapshot() -> None:
    """Test helper: clear the cache so a fresh snapshot can be taken."""
    global _snapshotted
    _originals.clear()
    _snapshotted = False

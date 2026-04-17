"""Rehydration and cross-process reconciliation of stored custom components.

The FastAPI process and the Huey worker process each own a separate
ComponentRegistry instance. When the user adds, edits, or deletes a custom
component via the API, only the FastAPI-side registry mutates. The worker
must reconcile its own registry against the `custom_component` table before
running any job so that tasks can resolve the user-authored class.

`rehydrate_custom_components` is the startup entry point (both processes).
`reconcile_custom_components` is the cheap per-job diff.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Dict, Optional

from kink import di
from sqlalchemy import select

from DashAI.back.custom_components.loader import load_user_class
from DashAI.back.custom_components.registry_bridge import (
    register_custom,
    unregister_custom,
)
from DashAI.back.dependencies.database.models import CustomComponent

logger = logging.getLogger(__name__)

# Per-process cache of {class_name: last_modified} for loaded custom components.
# Lets `reconcile_custom_components` skip rows that are already up to date.
_state_lock = threading.Lock()
_loaded_state: Dict[str, Optional[datetime]] = {}


def _load_and_register(row: CustomComponent, registry) -> bool:
    try:
        # Replace any stale registration (previous override or a core/plugin
        # class). `register_custom` with override=True handles the swap.
        unload_only = row.class_name in registry and not row.is_override
        if unload_only:
            # Custom (non-override) row: drop any stale entry of the same name
            # without restoring an original.
            unregister_custom(row.class_name, registry, restore_original=False)
        cls = load_user_class(row.source_code, row.class_name)
        register_custom(cls, registry, override=True)
        return True
    except Exception:  # noqa: BLE001
        logger.exception(
            "Failed to load custom component '%s' (id=%s); skipping.",
            row.class_name,
            row.id,
        )
        return False


def rehydrate_custom_components() -> None:
    """Re-register every persisted custom component into the registry."""
    session_factory = di["session_factory"]
    registry = di["component_registry"]

    with session_factory() as db:
        rows = db.execute(select(CustomComponent)).scalars().all()

    with _state_lock:
        _loaded_state.clear()
        for row in rows:
            if _load_and_register(row, registry):
                _loaded_state[row.class_name] = row.last_modified


def reconcile_custom_components() -> None:
    """Sync this process's registry to the current DB state.

    - New rows: load and register.
    - Edited rows (different `last_modified`): unregister the old class, load
      the new source, register.
    - Rows that are gone from the DB but still registered here: unregister.

    Designed to be cheap for the common case where nothing changed.
    """
    try:
        session_factory = di["session_factory"]
        registry = di["component_registry"]
    except KeyError:
        return

    with session_factory() as db:
        rows = db.execute(select(CustomComponent)).scalars().all()

    db_by_name = {row.class_name: row for row in rows}

    with _state_lock:
        for name, row in db_by_name.items():
            known = _loaded_state.get(name)
            if known == row.last_modified and name in registry:
                continue
            if _load_and_register(row, registry):
                _loaded_state[name] = row.last_modified

        for name in list(_loaded_state.keys()):
            if name in db_by_name:
                continue
            # Row disappeared. If it was an override (we know because an
            # original snapshot exists), restore the original; otherwise just
            # drop the class.
            unregister_custom(name, registry, restore_original=True)
            _loaded_state.pop(name, None)


def record_custom_component(row: CustomComponent) -> None:
    """Record a just-registered component in the per-process state cache.

    Called from the API process right after a successful create/update so the
    next reconcile pass does not pointlessly reload the class we just wrote.
    """
    with _state_lock:
        _loaded_state[row.class_name] = row.last_modified


def forget_custom_component(class_name: str) -> None:
    """Drop a class from the per-process state cache."""
    with _state_lock:
        _loaded_state.pop(class_name, None)

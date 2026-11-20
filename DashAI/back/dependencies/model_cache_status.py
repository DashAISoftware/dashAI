"""Publishes the worker's model cache state in the database.

The job worker and the API run in different processes, so the worker writes
what it keeps loaded to the ``loaded_model`` table and the API reads it and
requests unloads through the same table.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import sessionmaker

from DashAI.back.dependencies.database.models import LoadedModel
from DashAI.back.dependencies.model_cache import CacheEntry

log = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SqlCacheReporter:
    """Cache reporter that mirrors the cache into the ``loaded_model`` table.

    Every database error is logged and swallowed, a status failure must never
    fail a reply.

    Parameters
    ----------
    session_factory : sessionmaker
        Factory of database sessions.
    worker_pid : int
        Process id of the worker owning the cache.
    """

    def __init__(self, session_factory: sessionmaker, worker_pid: int) -> None:
        self._session_factory = session_factory
        self._pid = worker_pid

    def on_load(self, entry: CacheEntry) -> None:
        """Insert or update the row of a freshly loaded entry."""
        now = _utcnow()
        try:
            with self._session_factory() as db:
                row = db.scalars(
                    select(LoadedModel).where(LoadedModel.key == entry.key)
                ).first()
                if row is None:
                    row = LoadedModel(key=entry.key)
                    db.add(row)
                row.worker_pid = self._pid
                row.slot = entry.slot
                row.label = entry.label
                row.load_params = entry.load_params
                row.ram_bytes = entry.ram_bytes
                row.gpu_bytes = entry.gpu_bytes
                row.loaded_at = now
                row.last_used_at = now
                row.in_use = entry.in_use
                row.unload_requested = False
                db.commit()
        except Exception:
            log.exception("Could not report a loaded model")

    def on_use(self, entry: CacheEntry) -> None:
        """Update the usage state of an entry."""
        try:
            with self._session_factory() as db:
                row = db.scalars(
                    select(LoadedModel).where(LoadedModel.key == entry.key)
                ).first()
                if row is None:
                    return
                row.in_use = entry.in_use
                row.last_used_at = _utcnow()
                db.commit()
        except Exception:
            log.exception("Could not report a model use")

    def on_unload(self, entry: CacheEntry, reason: str) -> None:
        """Delete the row of an unloaded entry."""
        try:
            with self._session_factory() as db:
                db.execute(delete(LoadedModel).where(LoadedModel.key == entry.key))
                db.commit()
        except Exception:
            log.exception("Could not report a model unload")

    def pending_unloads(self) -> List[str]:
        """Return the keys of this worker's rows with an unload request."""
        try:
            with self._session_factory() as db:
                return list(
                    db.scalars(
                        select(LoadedModel.key).where(
                            LoadedModel.unload_requested.is_(True),
                            LoadedModel.worker_pid == self._pid,
                        )
                    )
                )
        except Exception:
            log.exception("Could not read pending model unloads")
            return []


def clear_loaded_models(
    session_factory: sessionmaker, except_pid: Optional[int] = None
) -> None:
    """Delete the rows left by workers that are gone.

    Parameters
    ----------
    session_factory : sessionmaker
        Factory of database sessions.
    except_pid : int | None
        When given, rows of this worker pid are kept.
    """
    with session_factory() as db:
        stmt = delete(LoadedModel)
        if except_pid is not None:
            stmt = stmt.where(LoadedModel.worker_pid != except_pid)
        db.execute(stmt)
        db.commit()

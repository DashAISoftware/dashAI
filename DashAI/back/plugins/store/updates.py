"""Newer releases of remote plugins, looked up at startup into ``.updates.json``."""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Mapping, Optional, Set

from packaging.version import InvalidVersion, Version
from pydantic import BaseModel

from DashAI.back.core.enums.plugin_source import PluginSource
from DashAI.back.plugins.disk.storage import PluginStorage
from DashAI.back.plugins.disk.trash import write_json
from DashAI.back.plugins.sources.base import (
    NotFoundError,
    PluginSourceHandler,
    RateLimitError,
)
from DashAI.back.plugins.store.store import PluginStore, offered_release, store_entry

logger = logging.getLogger(__name__)

UPDATES_FILE = ".updates.json"
_RECHECK_AFTER = timedelta(hours=12)
_PARALLEL_REQUESTS = 4

RATE_LIMITED = "rate_limited"
NOT_FOUND = "not_found"
OFFLINE = "offline"  # also a timeout, the source did not answer


class _Lookup(BaseModel):
    location: str
    latest: Optional[str] = None
    etag: Optional[str] = None
    error: Optional[str] = None


class _UpdatesFile(BaseModel):
    checked_at: Optional[str] = None
    plugins: Dict[str, _Lookup] = {}


def is_newer(latest: str, installed: Optional[str]) -> bool:
    """Compare version-like tags as versions, any other different tag counts as new."""

    def version(tag: str) -> Version:
        return Version(tag[1:] if tag[:1] in "vV" else tag)

    try:
        return version(latest) > version(installed or "")
    except InvalidVersion:
        return latest != installed


class PluginUpdates:
    def __init__(
        self,
        storage: PluginStorage,
        sources: Mapping[PluginSource, PluginSourceHandler],
        store: Optional[PluginStore] = None,
        apply_removed: Callable[[], bool] = lambda: False,
    ):
        self.storage = storage
        self.sources = sources
        self.store = store
        self.apply_removed = apply_removed  # PluginInstaller's, after each reading
        self.checking = False
        # Lookups (since this process started) that blocked or unblocked one.
        self.blocked_changes = 0
        self._lock = threading.Lock()  # one lookup at a time

    def _read(self) -> dict:
        try:
            return _UpdatesFile.model_validate_json(
                (self.storage.root / UPDATES_FILE).read_bytes()
            ).model_dump(exclude_unset=True)
        except (OSError, ValueError):  # also not one, looked up again
            return {}

    def _remote_plugins(self) -> Dict[str, Dict[str, Optional[str]]]:
        """``{id: {"source", "location", "ref"}}`` of updatable installed plugins."""
        plugins = {}
        for plugin_id in self.storage.list_installed():
            try:
                provenance = self.storage.read_source(plugin_id)
                handler = provenance and self.sources[PluginSource(provenance.source)]
            except (ValueError, KeyError):  # corrupt .source, nowhere to ask
                continue
            if handler and handler.can_update:
                plugins[plugin_id] = {
                    "source": provenance.source,
                    "location": provenance.location,
                    "ref": provenance.ref,
                }
        return plugins

    def status(self) -> dict:
        """What the last lookup found, for the plugins installed now."""
        data = self._read()
        known = data.get("plugins", {})
        index = self.store.read() if self.store else None
        updates, errors, needs_newer_dashai = {}, {}, {}
        for plugin_id, installed in self._remote_plugins().items():
            listed = store_entry(
                index, plugin_id, installed["source"], installed["location"]
            )
            if listed:
                offered = offered_release(listed)
                if offered and is_newer(offered.tag, installed["ref"]):
                    updates[plugin_id] = offered.tag
                newest = listed.releases[0]
                if newest is not offered and is_newer(newest.tag, installed["ref"]):
                    needs_newer_dashai[plugin_id] = newest.tag
                continue
            entry = known.get(plugin_id)
            if not entry or entry.get("location") != installed["location"]:
                continue  # not looked up yet (installed since, from another repo)
            if entry.get("error"):
                errors[plugin_id] = entry["error"]
            latest = entry.get("latest")
            if latest and is_newer(latest, installed["ref"]):
                updates[plugin_id] = latest
        return {
            "checking": self.checking,
            "blocked_changes": self.blocked_changes,
            "checked_at": data.get("checked_at"),
            "updates": updates,
            "errors": errors,
            "needs_newer_dashai": needs_newer_dashai,
            "store_error": self.store.status()["error"] if self.store else None,
        }

    def check_in_background(self) -> None:
        """When dashAI opens: without delaying it."""

        def check() -> None:
            try:
                self.check()
            except Exception as error:  # noqa: BLE001 (rate limited, in status())
                logger.warning("Could not look for plugin updates: %s", error)

        self.checking = True  # already, for whoever asks before the thread runs
        threading.Thread(target=check, name="plugin-updates", daemon=True).start()

    def check(self, force: bool = False) -> dict:
        """Look up releases (every 12 h unless ``force``) and return ``status()``."""
        with self._lock:
            self.checking = True
            try:
                rate_limited = self._check(force)
            finally:
                self.checking = False
        if rate_limited:
            raise RateLimitError(rate_limited)
        return self.status()

    def _check(self, force: bool) -> Optional[str]:
        index = None
        if self.store:
            self.store.refresh()  # a failure is kept for status()
            index = self.store.read()
            if self.apply_removed():
                self.blocked_changes += 1
        data = self._read()
        known: Dict[str, dict] = data.get("plugins", {})
        plugins = {
            plugin_id: installed
            for plugin_id, installed in self._remote_plugins().items()
            if not store_entry(
                index, plugin_id, installed["source"], installed["location"]
            )
        }
        try:
            checked_at = datetime.fromisoformat(data["checked_at"])
            fresh = datetime.now(timezone.utc) - checked_at < _RECHECK_AFTER
        except (KeyError, TypeError, ValueError):
            fresh = False
        full = force or not fresh

        def due(plugin_id: str) -> bool:
            entry = known.get(plugin_id, {})
            return entry.get("location") != plugins[plugin_id]["location"] or bool(
                entry.get("error")
            )

        todo: List[str] = [p for p in plugins if full or due(p)]
        if not todo:
            return None
        # Rate-limited sources are skipped, others still looked up
        stopped: Set[PluginSource] = set()
        rate_limited: List[str] = []

        def look_up(plugin_id: str) -> None:
            source_name = PluginSource(plugins[plugin_id]["source"])
            if source_name in stopped:
                return
            location = plugins[plugin_id]["location"]
            source = self.sources[source_name]
            previous = known.get(plugin_id, {})
            if previous.get("location") != location:
                previous = {}
            entry = {**previous, "location": location, "error": None}
            try:
                latest, etag = source.latest_tag(location, previous.get("etag"))
                entry["etag"] = etag
                if latest is not None:  # None if unchanged since the last lookup
                    entry["latest"] = latest
            except RateLimitError as error:
                stopped.add(source_name)
                rate_limited.append(str(error))
                entry["error"] = RATE_LIMITED
            except NotFoundError:
                entry["error"] = NOT_FOUND
            except Exception as error:  # noqa: BLE001 (offline, timeout, bad URL)
                logger.warning("Could not look up '%s' updates: %s", plugin_id, error)
                entry["error"] = OFFLINE
            known[plugin_id] = entry

        with ThreadPoolExecutor(_PARALLEL_REQUESTS) as pool:
            list(pool.map(look_up, todo))
        # Only the plugins it missed, or rate limited, so the 12 hours don't restart.
        if full and not rate_limited:
            data["checked_at"] = datetime.now(timezone.utc).isoformat()
        data["plugins"] = {p: e for p, e in known.items() if p in plugins}
        try:
            write_json(self.storage.root / UPDATES_FILE, data)
        except OSError as error:
            logger.warning("Could not save the plugin updates: %s", error)
        return rate_limited[0] if rate_limited else None

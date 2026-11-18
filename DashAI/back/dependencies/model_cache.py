"""In-process cache that keeps generative models loaded between jobs.

The job worker acquires models through :class:`ModelCache` so consecutive chat
messages reuse the same loaded object instead of reloading it from disk.
"""

import contextlib
import gc
import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterator, List, Optional, Protocol, Tuple

log = logging.getLogger(__name__)


def split_params(model_class: type, params: dict) -> Tuple[dict, dict]:
    """Split parameters into load parameters and generation parameters.

    Parameters
    ----------
    model_class : type
        Model class, optionally declaring a ``GENERATION_PARAMS`` set.
    params : dict
        All the parameters of the model.

    Returns
    -------
    tuple[dict, dict]
        ``(load_params, generation_params)``.
    """
    generation_names = getattr(model_class, "GENERATION_PARAMS", set())
    load_params = {k: v for k, v in params.items() if k not in generation_names}
    generation_params = {k: v for k, v in params.items() if k in generation_names}
    return load_params, generation_params


def cache_key(model_class: type, load_params: dict) -> str:
    """Build the cache key of a model class loaded with the given parameters.

    Parameters
    ----------
    model_class : type
        Model class.
    load_params : dict
        Parameters that require a reload when they change.

    Returns
    -------
    str
        Deterministic key.
    """
    prefix = f"{model_class.__module__}.{model_class.__qualname__}:"
    return prefix + json.dumps(load_params, sort_keys=True, default=str)


@dataclass
class CacheEntry:
    """A model object held (or just handed out) by the cache."""

    slot: str
    key: str
    label: str
    obj: Any
    load_params: dict
    cached: bool
    in_use: bool
    loaded_at: float
    last_used: float
    ram_bytes: Optional[int] = None
    gpu_bytes: Optional[int] = None


class CacheReporter(Protocol):
    """Receiver of cache events, used to expose the cache state elsewhere."""

    def on_load(self, entry: CacheEntry) -> None: ...

    def on_use(self, entry: CacheEntry) -> None: ...

    def on_unload(self, entry: CacheEntry, reason: str) -> None: ...

    def pending_unloads(self) -> List[str]: ...


def close_object(obj: Any) -> None:
    """Call ``obj.close()`` when available, logging and swallowing errors.

    The memory is not reclaimed here because the caller still references the
    object. Call :func:`reclaim_memory` after dropping every reference.

    Parameters
    ----------
    obj : Any
        Object to close.
    """
    close = getattr(obj, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            log.exception("Error while closing %r", obj)


def reclaim_memory() -> None:
    """Run the garbage collector and empty the CUDA cache when available."""
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        log.debug("Could not empty the CUDA cache", exc_info=True)


def _free_gpu_bytes() -> Optional[int]:
    try:
        import torch

        if torch.cuda.is_available():
            return torch.cuda.mem_get_info()[0]
    except Exception:
        log.debug("Could not read GPU memory", exc_info=True)
    return None


def _rss_bytes() -> Optional[int]:
    try:
        import psutil

        return psutil.Process().memory_info().rss
    except Exception:
        log.debug("Could not read process memory", exc_info=True)
        return None


class ModelCache:
    """Cache of loaded models, one entry per slot.

    Parameters
    ----------
    enabled : bool
        When False every acquire builds a fresh object closed on release.
    idle_seconds : int
        Seconds an unused entry may stay loaded before ``evict_idle`` unloads it.
    reporter : CacheReporter | None
        Optional receiver of load, use and unload events.
    clock : Callable[[], float]
        Monotonic time source, injectable for tests.
    """

    def __init__(
        self,
        enabled: bool,
        idle_seconds: int,
        reporter: Optional[CacheReporter] = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.enabled = enabled
        self.idle_seconds = idle_seconds
        self.reporter = reporter
        self._clock = clock
        self._entries: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._scope = threading.local()

    def _report(self, hook: str, *args: Any) -> None:
        if self.reporter is None:
            return
        try:
            getattr(self.reporter, hook)(*args)
        except Exception:
            log.exception("Model cache reporter failed in %s", hook)

    def _build(
        self,
        slot: str,
        key: str,
        build: Callable[[], Any],
        label: str,
        load_params: dict,
        cached: bool,
    ) -> CacheEntry:
        ram_before = _rss_bytes()
        gpu_before = _free_gpu_bytes()
        started = self._clock()
        obj = build()
        elapsed = self._clock() - started
        ram_after = _rss_bytes()
        gpu_after = _free_gpu_bytes()
        now = self._clock()
        entry = CacheEntry(
            slot=slot,
            key=key,
            label=label,
            obj=obj,
            load_params=load_params,
            cached=cached,
            in_use=True,
            loaded_at=now,
            last_used=now,
            ram_bytes=(
                None
                if ram_before is None or ram_after is None
                else max(ram_after - ram_before, 0)
            ),
            gpu_bytes=(
                None
                if gpu_before is None or gpu_after is None
                else max(gpu_before - gpu_after, 0)
            ),
        )
        log.info("Loaded model '%s' for slot '%s' in %.2f s", label, slot, elapsed)
        return entry

    def acquire(
        self,
        slot: str,
        key: str,
        build: Callable[[], Any],
        *,
        label: str,
        load_params: dict,
        on_miss: Optional[Callable[[], None]] = None,
    ) -> CacheEntry:
        """Return the model for a slot, building it only when needed.

        Parameters
        ----------
        slot : str
            Role of the model (for example the chat model or the embedder).
        key : str
            Cache key, see :func:`cache_key`.
        build : Callable[[], Any]
            Factory that loads the model.
        label : str
            Human readable name used in logs and reports.
        load_params : dict
            Load parameters the entry was built with.
        on_miss : Callable[[], None] | None
            Called right before building when the model is not cached.

        Returns
        -------
        CacheEntry
            Entry marked as in use. Pass it to ``release`` or ``discard``.
        """
        with self._lock:
            current = self._entries.get(slot)
            cached = self.enabled
            if cached and current is not None:
                if current.in_use:
                    # The slot is busy: build a private, uncached object.
                    cached = False
                elif current.key == key:
                    current.in_use = True
                    current.last_used = self._clock()
                    log.info("Reusing loaded model '%s' for slot '%s'", label, slot)
                    self._report("on_use", current)
                    self._track(current)
                    return current
                else:
                    self._unload(current, "params_changed")
            if on_miss is not None:
                on_miss()
            entry = self._build(slot, key, build, label, load_params, cached)
            if cached:
                self._entries[slot] = entry
                self._report("on_load", entry)
            self._track(entry)
            return entry

    def _track(self, entry: CacheEntry) -> None:
        scope = getattr(self._scope, "entries", None)
        if scope is not None:
            scope.append(entry)

    def _unload(self, entry: CacheEntry, reason: str) -> None:
        if self._entries.get(entry.slot) is entry:
            del self._entries[entry.slot]
        log.info("Unloading model '%s' (reason: %s)", entry.label, reason)
        obj, entry.obj = entry.obj, None
        if entry.cached:
            self._report("on_unload", entry, reason)
        close_object(obj)
        del obj
        reclaim_memory()

    def release(self, entry: CacheEntry) -> None:
        """Hand an entry back. Uncached entries are closed."""
        with self._lock:
            if not entry.cached:
                if entry.obj is not None:
                    obj, entry.obj = entry.obj, None
                    close_object(obj)
                    del obj
                    reclaim_memory()
                entry.in_use = False
                return
            entry.in_use = False
            entry.last_used = self._clock()

    def discard(self, entry: CacheEntry, reason: str = "error") -> None:
        """Unload an entry, for example after its model failed."""
        with self._lock:
            entry.in_use = False
            if entry.obj is not None:
                self._unload(entry, reason)

    def clear(self, reason: str, slot: Optional[str] = None) -> None:
        """Unload entries that are not in use, optionally only one slot."""
        with self._lock:
            for entry in list(self._entries.values()):
                if (slot is None or entry.slot == slot) and not entry.in_use:
                    self._unload(entry, reason)

    def evict_idle(self) -> int:
        """Unload entries unused for longer than ``idle_seconds``.

        Returns
        -------
        int
            Number of entries unloaded.
        """
        evicted = 0
        with self._lock:
            now = self._clock()
            for entry in list(self._entries.values()):
                if not entry.in_use and now - entry.last_used > self.idle_seconds:
                    self._unload(entry, "idle")
                    evicted += 1
        return evicted

    def apply_pending_unloads(self) -> None:
        """Unload the entries the reporter asks to unload (for example from a panel)."""
        if self.reporter is None:
            return
        try:
            keys = set(self.reporter.pending_unloads())
        except Exception:
            log.exception("Model cache reporter failed in pending_unloads")
            return
        with self._lock:
            for entry in list(self._entries.values()):
                if entry.key in keys and not entry.in_use:
                    self._unload(entry, "panel")

    def entries(self) -> List[CacheEntry]:
        """Return the entries currently held by the cache."""
        with self._lock:
            return list(self._entries.values())

    @contextlib.contextmanager
    def job_scope(self) -> Iterator[None]:
        """Track entries acquired inside the block.

        On an exception the entries are discarded and the exception is
        re-raised. On exit, entries still in use are released.
        """
        previous = getattr(self._scope, "entries", None)
        acquired: List[CacheEntry] = []
        self._scope.entries = acquired
        try:
            yield
        except BaseException:
            for entry in acquired:
                self.discard(entry)
            raise
        finally:
            self._scope.entries = previous
            for entry in acquired:
                if entry.in_use:
                    self.release(entry)


_model_cache: Optional[ModelCache] = None
_singleton_lock = threading.Lock()


def get_model_cache() -> ModelCache:
    """Return the process wide cache, creating it on first use."""
    global _model_cache
    with _singleton_lock:
        if _model_cache is None:
            from DashAI.back.config import DefaultSettings

            defaults = DefaultSettings()
            enabled = defaults.MODEL_CACHE_ENABLED
            idle = defaults.MODEL_CACHE_IDLE_SECONDS
            try:
                from kink import di

                config = di["config"]
                enabled = config.get("MODEL_CACHE_ENABLED", enabled)
                idle = config.get("MODEL_CACHE_IDLE_SECONDS", idle)
            except Exception:
                log.debug("No DI config, using model cache defaults")
            _model_cache = ModelCache(enabled=bool(enabled), idle_seconds=int(idle))
        return _model_cache


def reset_model_cache() -> None:
    """Drop the process wide cache, closing its entries."""
    global _model_cache
    with _singleton_lock:
        if _model_cache is not None:
            for entry in _model_cache.entries():
                _model_cache.discard(entry, "reset")
        _model_cache = None

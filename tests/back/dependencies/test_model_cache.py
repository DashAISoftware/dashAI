"""Tests for the in-process model cache."""

import pytest

from DashAI.back.dependencies.model_cache import (
    ModelCache,
    cache_key,
    split_params,
)


class FakeModel:
    GENERATION_PARAMS = {"temperature"}
    builds = 0

    def __init__(self):
        type(self).builds += 1
        self.closed = 0

    def close(self):
        self.closed += 1


@pytest.fixture(autouse=True)
def reset_builds():
    FakeModel.builds = 0


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def _acquire(cache, params, slot="model"):
    load, _ = split_params(FakeModel, params)
    return cache.acquire(
        slot,
        cache_key(FakeModel, load),
        FakeModel,
        label="fake",
        load_params=load,
    )


def test_same_key_builds_once():
    cache = ModelCache(enabled=True, idle_seconds=300)
    params = {"context_window": 512}
    first = _acquire(cache, params)
    cache.release(first)
    second = _acquire(cache, params)
    cache.release(second)
    assert FakeModel.builds == 1
    assert first.obj is second.obj


def test_load_param_change_rebuilds_and_closes_previous():
    cache = ModelCache(enabled=True, idle_seconds=300)
    first = _acquire(cache, {"context_window": 512})
    first_obj = first.obj
    cache.release(first)
    second = _acquire(cache, {"context_window": 1024})
    cache.release(second)
    assert FakeModel.builds == 2
    assert first_obj.closed == 1


def test_generation_param_change_reuses():
    cache = ModelCache(enabled=True, idle_seconds=300)
    a = _acquire(cache, {"context_window": 512, "temperature": 0.1})
    cache.release(a)
    b = _acquire(cache, {"context_window": 512, "temperature": 0.7})
    cache.release(b)
    assert a.key == b.key
    assert FakeModel.builds == 1


def test_idle_entry_evicted():
    clock = Clock()
    cache = ModelCache(enabled=True, idle_seconds=300, clock=clock)
    entry = _acquire(cache, {"context_window": 512})
    obj = entry.obj
    cache.release(entry)
    clock.now += 301
    assert cache.evict_idle() == 1
    assert obj.closed == 1
    assert cache.entries() == []


def test_job_scope_discards_on_error():
    cache = ModelCache(enabled=True, idle_seconds=300)
    holder = {}

    def failing_job():
        with cache.job_scope():
            entry = _acquire(cache, {"context_window": 512})
            holder["obj"] = entry.obj
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        failing_job()
    assert holder["obj"].closed == 1
    assert cache.entries() == []


def test_disabled_cache_builds_and_closes_every_time():
    cache = ModelCache(enabled=False, idle_seconds=300)
    objs = []
    for _ in range(2):
        entry = _acquire(cache, {"context_window": 512})
        objs.append(entry.obj)
        cache.release(entry)
    assert FakeModel.builds == 2
    assert [o.closed for o in objs] == [1, 1]


def test_in_use_entry_not_evicted_second_key_bypasses():
    cache = ModelCache(enabled=True, idle_seconds=300)
    a = _acquire(cache, {"context_window": 512})
    b = _acquire(cache, {"context_window": 1024})
    assert a.cached is True
    assert b.cached is False
    assert a.obj.closed == 0
    assert [e.key for e in cache.entries()] == [a.key]
    b_obj = b.obj
    cache.release(b)
    assert b_obj.closed == 1

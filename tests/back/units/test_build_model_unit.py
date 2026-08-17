"""Tests for BuildModelUnit's model-class resolution and its caching."""

import pytest
from kink import di

from DashAI.back.units.build_model_unit import BuildModelUnit
from DashAI.back.units.context import ExecutionContext


class _ModelA:
    def __init__(self, **kwargs):
        pass


class _ModelB:
    def __init__(self, **kwargs):
        pass


@pytest.fixture
def fake_registry():
    """A minimal dict-shaped registry: enough for name -> class lookups."""
    registry = {
        "ModelA": {"class": _ModelA},
        "ModelB": {"class": _ModelB},
    }
    di["component_registry"] = registry
    yield registry
    del di["component_registry"]


def _build_unit(model_name):
    return BuildModelUnit(
        model={"component": model_name, "params": {}},
        train_metrics=[],
        validation_metrics=[],
        test_metrics=[],
    )


def test_two_build_model_units_in_one_context_resolve_independently(fake_registry):
    """Regression: the model-class cache must not be keyed by the context.

    Two ``BuildModelUnit`` instances configured for different models, run
    against the same context, must each build their own model. Before this
    fix the class was memoized under a context-global ``"model_class"`` key,
    so the second unit would silently reuse the first one's resolved class —
    and its download-gate check would validate the wrong model too.
    """
    ctx = ExecutionContext()
    ctx.put("x", {"train": None, "validation": None})
    ctx.put("y", {"train": None, "validation": None})
    ctx.put("n_labels", None)

    a = _build_unit("ModelA")
    a(ctx)
    model_a = ctx.get("model")

    b = _build_unit("ModelB")
    b(ctx)
    model_b = ctx.get("model")

    assert isinstance(model_a, _ModelA)
    assert isinstance(model_b, _ModelB)


def test_resolve_model_class_is_memoized_per_instance_not_shared(fake_registry):
    a = _build_unit("ModelA")
    b = _build_unit("ModelB")

    assert a._resolve_model_class() is _ModelA
    assert b._resolve_model_class() is _ModelB
    # Calling again must return the same, still-correct class from the cache.
    assert a._resolve_model_class() is _ModelA

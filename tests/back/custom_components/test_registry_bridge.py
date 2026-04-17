"""Unit tests for register_custom / unregister_custom override semantics."""

import pytest

from DashAI.back.custom_components.originals import (
    reset_snapshot,
    snapshot_originals,
)
from DashAI.back.custom_components.registry_bridge import (
    register_custom,
    unregister_custom,
)
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.base_model import BaseModel


class _OriginalModel(BaseModel):
    DISPLAY_NAME = "Original"

    def save(self, filename):
        pass

    def load(self, filename):
        return self

    def train(self, x_train, y_train, x_validation=None, y_validation=None):
        return self

    def predict(self, x_data):
        return []


class _OverrideModel(BaseModel):
    """User-authored replacement that happens to share the original's name."""

    DISPLAY_NAME = "Overridden"

    def save(self, filename):
        pass

    def load(self, filename):
        return self

    def train(self, x_train, y_train, x_validation=None, y_validation=None):
        return self

    def predict(self, x_data):
        return []


# Force override class to share the registered name of the original.
_OverrideModel.__name__ = _OriginalModel.__name__


@pytest.fixture
def registry():
    reset_snapshot()
    reg = ComponentRegistry(initial_components=[_OriginalModel])
    snapshot_originals(reg)
    yield reg
    reset_snapshot()


def test_register_override_replaces_original(registry):
    assert registry[_OriginalModel.__name__]["class"] is _OriginalModel

    register_custom(_OverrideModel, registry, override=True)

    assert registry[_OriginalModel.__name__]["class"] is _OverrideModel


def test_register_without_override_raises_on_collision(registry):
    with pytest.raises(ValueError, match="already registered"):
        register_custom(_OverrideModel, registry, override=False)


def test_unregister_with_restore_brings_back_original(registry):
    register_custom(_OverrideModel, registry, override=True)
    assert registry[_OriginalModel.__name__]["class"] is _OverrideModel

    unregister_custom(
        _OriginalModel.__name__,
        registry,
        restore_original=True,
    )

    assert registry[_OriginalModel.__name__]["class"] is _OriginalModel


def test_unregister_without_restore_drops_the_class(registry):
    register_custom(_OverrideModel, registry, override=True)
    unregister_custom(
        _OriginalModel.__name__,
        registry,
        restore_original=False,
    )
    assert _OriginalModel.__name__ not in registry

"""Tests for cross-process custom component reconciliation."""

from datetime import datetime

import pytest
from kink import di

from DashAI.back.custom_components.loader import unload_user_module
from DashAI.back.custom_components.startup import (
    _loaded_state,
    forget_custom_component,
    reconcile_custom_components,
    record_custom_component,
    rehydrate_custom_components,
)
from DashAI.back.dependencies.database.models import CustomComponent

VALID_MODEL_SOURCE = """
from DashAI.back.models.base_model import BaseModel


class ReconcileModel(BaseModel):
    DISPLAY_NAME = "Reconcile Model"

    def save(self, filename):
        pass

    def load(self, filename):
        return self

    def train(self, x_train, y_train, x_validation=None, y_validation=None):
        return self

    def predict(self, x_data):
        return []
"""


@pytest.fixture(autouse=True)
def reset_state(client):
    """Clean state cache and any stray class between tests."""
    _loaded_state.clear()
    unload_user_module("ReconcileModel")
    registry = di["component_registry"]
    if "ReconcileModel" in registry:
        registry.unregister_component(registry["ReconcileModel"]["class"])
    with di["session_factory"]() as db:
        for row in db.query(CustomComponent).all():
            db.delete(row)
        db.commit()
    yield
    _loaded_state.clear()
    unload_user_module("ReconcileModel")
    if "ReconcileModel" in registry:
        registry.unregister_component(registry["ReconcileModel"]["class"])
    with di["session_factory"]() as db:
        for row in db.query(CustomComponent).all():
            db.delete(row)
        db.commit()


def _insert_row(class_name: str = "ReconcileModel"):
    with di["session_factory"]() as db:
        row = CustomComponent(
            class_name=class_name,
            base_type="Model",
            base_class="BaseModel",
            source_code=VALID_MODEL_SOURCE,
            description=None,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row


def test_reconcile_registers_new_row():
    registry = di["component_registry"]
    assert "ReconcileModel" not in registry
    _insert_row()

    reconcile_custom_components()

    assert "ReconcileModel" in registry


def test_reconcile_unregisters_deleted_row():
    registry = di["component_registry"]
    row = _insert_row()
    reconcile_custom_components()
    assert "ReconcileModel" in registry

    with di["session_factory"]() as db:
        db.delete(db.get(CustomComponent, row.id))
        db.commit()

    reconcile_custom_components()
    assert "ReconcileModel" not in registry


def test_reconcile_reloads_on_last_modified_change():
    registry = di["component_registry"]
    row = _insert_row()
    reconcile_custom_components()
    original_cls = registry["ReconcileModel"]["class"]

    # Simulate an edit from the FastAPI process.
    with di["session_factory"]() as db:
        persisted = db.get(CustomComponent, row.id)
        persisted.source_code = VALID_MODEL_SOURCE.replace(
            "Reconcile Model", "Edited Model"
        )
        persisted.last_modified = datetime(2099, 1, 1)
        db.commit()

    reconcile_custom_components()
    new_cls = registry["ReconcileModel"]["class"]
    assert new_cls is not original_cls
    assert new_cls.DISPLAY_NAME.get("en") == "Edited Model"


def test_record_forget_state_helpers():
    row = _insert_row()
    record_custom_component(row)
    assert _loaded_state["ReconcileModel"] == row.last_modified
    forget_custom_component("ReconcileModel")
    assert "ReconcileModel" not in _loaded_state


def test_rehydrate_populates_registry_and_state():
    registry = di["component_registry"]
    _insert_row()
    assert "ReconcileModel" not in registry

    rehydrate_custom_components()

    assert "ReconcileModel" in registry
    assert "ReconcileModel" in _loaded_state

"""API tests for overriding and reverting core/plugin components."""

import pytest
from kink import di

from DashAI.back.custom_components.loader import unload_user_module
from DashAI.back.custom_components.originals import snapshot_originals
from DashAI.back.custom_components.startup import _loaded_state
from DashAI.back.dependencies.database.models import CustomComponent

# Pick a known built-in model that ships with DashAI. If this ever changes,
# any Model-type registered at startup works.
TARGET_CLASS = "KNeighborsClassifier"


OVERRIDE_SOURCE = f"""
from DashAI.back.models.base_model import BaseModel


class {TARGET_CLASS}(BaseModel):
    DISPLAY_NAME = "Overridden KNN"

    def save(self, filename):
        pass

    def load(self, filename):
        return self

    def train(self, x_train, y_train, x_validation=None, y_validation=None):
        return self

    def predict(self, x_data):
        return [42]
"""


@pytest.fixture(autouse=True)
def reset_state(client):
    """Ensure overrides table and override class are clean between tests."""
    _loaded_state.clear()
    registry = di["component_registry"]
    # Re-snapshot in case an earlier test cleared it.
    snapshot_originals(registry)

    with di["session_factory"]() as db:
        for row in db.query(CustomComponent).all():
            db.delete(row)
        db.commit()

    unload_user_module(TARGET_CLASS)
    yield

    _loaded_state.clear()
    unload_user_module(TARGET_CLASS)
    with di["session_factory"]() as db:
        for row in db.query(CustomComponent).all():
            db.delete(row)
        db.commit()


def test_get_source_for_core_component(client):
    resp = client.get(f"/api/v1/custom-component/source/{TARGET_CLASS}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["class_name"] == TARGET_CLASS
    assert "class" in data["source_code"]
    assert data["origin"] in ("core", "plugin")
    assert data["editable"] is True


def test_get_source_for_unknown_component_404(client):
    resp = client.get("/api/v1/custom-component/source/NopeNotAComponent")
    assert resp.status_code == 404


def test_override_and_revert_flow(client):
    registry = di["component_registry"]
    original_cls = registry[TARGET_CLASS]["class"]
    assert original_cls.__name__ == TARGET_CLASS

    # Create override
    resp = client.post(
        "/api/v1/custom-component/",
        json={
            "class_name": TARGET_CLASS,
            "base_class": "BaseModel",
            "source_code": OVERRIDE_SOURCE,
        },
    )
    assert resp.status_code == 201, resp.text
    row = resp.json()
    assert row["is_override"] is True

    overridden_cls = registry[TARGET_CLASS]["class"]
    assert overridden_cls is not original_cls
    assert overridden_cls.DISPLAY_NAME.get("en") == "Overridden KNN"

    # Source endpoint now reports the override
    src = client.get(f"/api/v1/custom-component/source/{TARGET_CLASS}").json()
    assert src["origin"] == "custom-override"

    # Delete the override → original restored
    resp = client.delete(f"/api/v1/custom-component/{row['id']}")
    assert resp.status_code == 204

    restored_cls = registry[TARGET_CLASS]["class"]
    assert restored_cls is original_cls


def test_cannot_override_pure_custom_component(client):
    # First create a brand-new custom component with an unused name.
    resp = client.post(
        "/api/v1/custom-component/",
        json={
            "class_name": "MyPureCustom",
            "base_class": "BaseModel",
            "source_code": OVERRIDE_SOURCE.replace(TARGET_CLASS, "MyPureCustom"),
        },
    )
    assert resp.status_code == 201, resp.text

    # Attempt to POST another component with the same name → rejected because
    # there is no original to fall back on (not an override candidate).
    resp = client.post(
        "/api/v1/custom-component/",
        json={
            "class_name": "MyPureCustom",
            "base_class": "BaseModel",
            "source_code": OVERRIDE_SOURCE.replace(TARGET_CLASS, "MyPureCustom"),
        },
    )
    assert resp.status_code == 409

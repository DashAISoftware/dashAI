"""API tests for /v1/custom-component endpoints."""

VALID_MODEL_SOURCE = """
from DashAI.back.models.base_model import BaseModel


class ApiTestModel(BaseModel):
    DISPLAY_NAME = "Api Test Model"

    def save(self, filename):
        pass

    def load(self, filename):
        return self

    def train(self, x_train, y_train, x_validation=None, y_validation=None):
        return self

    def predict(self, x_data):
        return []
"""


def test_list_base_classes(client):
    resp = client.get("/api/v1/custom-component/base-classes")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    names = {r["name"] for r in data}
    assert "BaseModel" in names


def test_get_base_class_info(client):
    resp = client.get("/api/v1/custom-component/base-classes/BaseModel")
    assert resp.status_code == 200
    info = resp.json()
    method_names = {m["name"] for m in info["abstract_methods"]}
    assert {"save", "load", "train"}.issubset(method_names)
    assert "class MyModel(BaseModel)" in info["skeleton"]


def test_get_base_class_info_not_found(client):
    resp = client.get("/api/v1/custom-component/base-classes/Nonexistent")
    assert resp.status_code == 404


def test_validate_endpoint_ok(client):
    resp = client.post(
        "/api/v1/custom-component/validate",
        json={
            "source_code": VALID_MODEL_SOURCE,
            "class_name": "ApiTestModel",
            "base_class": "BaseModel",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["errors"] == []


def test_validate_endpoint_missing_abstract(client):
    bad_source = """
from DashAI.back.models.base_model import BaseModel


class IncompleteModel(BaseModel):
    def save(self, filename):
        pass

    def predict(self, x_data):
        return []
"""
    resp = client.post(
        "/api/v1/custom-component/validate",
        json={
            "source_code": bad_source,
            "class_name": "IncompleteModel",
            "base_class": "BaseModel",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert any("abstract methods" in e for e in data["errors"])


def test_create_list_delete_custom_component(client):
    create_payload = {
        "source_code": VALID_MODEL_SOURCE,
        "class_name": "ApiTestModel",
        "base_class": "BaseModel",
        "description": "E2E test model",
    }
    resp = client.post("/api/v1/custom-component/", json=create_payload)
    assert resp.status_code == 201, resp.text
    created = resp.json()
    assert created["class_name"] == "ApiTestModel"
    assert created["base_type"] == "Model"
    comp_id = created["id"]

    # Appears in live ComponentRegistry via /v1/component/
    resp = client.get("/api/v1/component/", params={"select_types": "Model"})
    assert resp.status_code == 200
    names = {c["name"] for c in resp.json()}
    assert "ApiTestModel" in names

    # Appears in our listing
    resp = client.get("/api/v1/custom-component/")
    assert resp.status_code == 200
    assert any(c["id"] == comp_id for c in resp.json())

    # Cannot create duplicate
    resp = client.post("/api/v1/custom-component/", json=create_payload)
    assert resp.status_code in (409, 422)

    # Delete
    resp = client.delete(f"/api/v1/custom-component/{comp_id}")
    assert resp.status_code == 204

    # Disappears from registry
    resp = client.get("/api/v1/component/", params={"select_types": "Model"})
    names = {c["name"] for c in resp.json()}
    assert "ApiTestModel" not in names


def test_create_rejects_invalid_source(client):
    resp = client.post(
        "/api/v1/custom-component/",
        json={
            "source_code": "class Broken(:\n    pass",
            "class_name": "Broken",
            "base_class": "BaseModel",
        },
    )
    assert resp.status_code == 422

"""Tests for the /api/v1/dataset-export endpoints."""

import pytest

from DashAI.back.core.enums.status import DatasetExportStatus
from DashAI.back.dataset_exporters.base_dataset_exporter import (
    BaseDatasetExporter,
    ExportPayload,
    ExportResult,
)
from DashAI.back.dependencies.database.models import DatasetExport
from DashAI.back.dependencies.database.utils import find_entity_by_huey_id

URL = "/api/v1/dataset-export"
PARAMS = {"name": "iris", "description": "Classic iris dataset."}


class FakeDatasetExporter(BaseDatasetExporter):
    """Exporter that publishes nowhere and needs no credential."""

    DISPLAY_NAME = "Fake"
    DESCRIPTION = "Exporter used by the API tests."

    def prepare(self, dataset, params, temp_path):
        return ExportPayload(metadata={"rows": dataset.num_rows})

    def upload(self, payload, params):
        return ExportResult(remote_id="533", url="https://example.org/d/533")


@pytest.fixture(name="fake_exporter", scope="module")
def fixture_fake_exporter(client):
    registry = client.app.container["component_registry"]
    registry.register_component(FakeDatasetExporter)
    yield "FakeDatasetExporter"
    registry.unregister_component(FakeDatasetExporter)


@pytest.fixture(name="session_factory", scope="module")
def fixture_session_factory(client):
    return client.app.container["session_factory"]


def _add_export(session_factory, dataset, export_status):
    with session_factory() as db:
        row = DatasetExport(
            dataset_id=dataset.id,
            dataset_name=dataset.name,
            exporter_name="FakeDatasetExporter",
            params=PARAMS,
            status=export_status,
        )
        db.add(row)
        db.commit()
        return row.id


def test_create_publishes_the_dataset(client, dataset_1, fake_exporter):
    response = client.post(
        f"{URL}/",
        json={
            "dataset_id": dataset_1.id,
            "exporter_name": fake_exporter,
            "params": PARAMS,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()

    export = client.get(f"{URL}/{body['export_id']}").json()
    assert export["status"] == DatasetExportStatus.PUBLISHED.value
    assert export["remote_id"] == "533"
    assert export["remote_url"] == "https://example.org/d/533"
    assert export["dataset_name"] == dataset_1.name
    assert export["params"] == PARAMS
    assert export["huey_id"]


def test_the_jobs_panel_finds_the_export(client, dataset_1, fake_exporter):
    body = client.post(
        f"{URL}/",
        json={
            "dataset_id": dataset_1.id,
            "exporter_name": fake_exporter,
            "params": PARAMS,
        },
    ).json()
    export = client.get(f"{URL}/{body['export_id']}").json()

    entity = find_entity_by_huey_id(export["huey_id"])

    assert entity["entity_type"] == "dataset_export"
    assert entity["entity_id"] == body["export_id"]
    assert entity["entity_name"] == dataset_1.name


def test_create_refuses_an_unknown_exporter(client, dataset_1):
    response = client.post(
        f"{URL}/",
        json={"dataset_id": dataset_1.id, "exporter_name": "Nope", "params": PARAMS},
    )
    assert response.status_code == 404


def test_create_refuses_an_unknown_dataset(client, fake_exporter):
    response = client.post(
        f"{URL}/",
        json={"dataset_id": 999999, "exporter_name": fake_exporter, "params": PARAMS},
    )
    assert response.status_code == 404


def test_create_requires_the_exporter_credential(client, dataset_1):
    response = client.post(
        f"{URL}/",
        json={
            "dataset_id": dataset_1.id,
            "exporter_name": "OpenMLDatasetExporter",
            "params": PARAMS,
        },
    )
    assert response.status_code == 422
    assert "OpenMLCredential" in response.json()["detail"]


def test_create_refuses_params_outside_the_schema(client, dataset_1, fake_exporter):
    response = client.post(
        f"{URL}/",
        json={
            "dataset_id": dataset_1.id,
            "exporter_name": fake_exporter,
            "params": {"name": "iris"},
        },
    )
    assert response.status_code == 422
    assert any("description" in error for error in response.json()["detail"])


def test_validate_accepts_valid_params(client, dataset_1, fake_exporter):
    response = client.post(
        f"{URL}/{fake_exporter}/validate",
        json={"dataset_id": dataset_1.id, "params": PARAMS},
    )
    assert response.status_code == 200
    assert response.json() == {"errors": []}


def test_validate_reports_exporter_rules(client, dataset_1, fake_exporter):
    response = client.post(
        f"{URL}/{fake_exporter}/validate",
        json={"dataset_id": dataset_1.id, "params": {**PARAMS, "name": "  "}},
    )
    assert response.json() == {"errors": ["The dataset name cannot be blank."]}


def test_validate_reports_schema_errors(client, dataset_1, fake_exporter):
    response = client.post(
        f"{URL}/{fake_exporter}/validate",
        json={"dataset_id": dataset_1.id, "params": {"name": "iris"}},
    )
    errors = response.json()["errors"]
    assert len(errors) == 1
    assert errors[0].startswith("description")


def test_validate_refuses_an_unknown_exporter(client, dataset_1):
    response = client.post(
        f"{URL}/Nope/validate",
        json={"dataset_id": dataset_1.id, "params": PARAMS},
    )
    assert response.status_code == 404


def test_validate_does_not_create_an_export(client, dataset_1, fake_exporter):
    before = len(client.get(f"{URL}/").json())
    client.post(
        f"{URL}/{fake_exporter}/validate",
        json={"dataset_id": dataset_1.id, "params": PARAMS},
    )
    assert len(client.get(f"{URL}/").json()) == before


def test_list_filters_by_dataset(client, dataset_1, session_factory):
    export_id = _add_export(session_factory, dataset_1, DatasetExportStatus.ERROR)

    ids = [row["id"] for row in client.get(f"{URL}/?dataset_id={dataset_1.id}").json()]
    assert export_id in ids
    assert ids == sorted(ids, reverse=True)
    assert client.get(f"{URL}/?dataset_id=999999").json() == []


def test_get_refuses_an_unknown_export(client):
    assert client.get(f"{URL}/999999").status_code == 404


def test_delete_removes_a_finished_export(client, dataset_1, session_factory):
    export_id = _add_export(session_factory, dataset_1, DatasetExportStatus.PUBLISHED)

    assert client.delete(f"{URL}/{export_id}").status_code == 204
    assert client.get(f"{URL}/{export_id}").status_code == 404


@pytest.mark.parametrize(
    "export_status",
    [
        DatasetExportStatus.PENDING,
        DatasetExportStatus.PREPARING,
        DatasetExportStatus.UPLOADING,
    ],
)
def test_delete_refuses_an_export_in_progress(
    client, dataset_1, session_factory, export_status
):
    export_id = _add_export(session_factory, dataset_1, export_status)

    assert client.delete(f"{URL}/{export_id}").status_code == 409
    assert client.get(f"{URL}/{export_id}").status_code == 200


def test_delete_refuses_an_unknown_export(client):
    assert client.delete(f"{URL}/999999").status_code == 404

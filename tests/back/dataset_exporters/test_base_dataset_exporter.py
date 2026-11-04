"""Tests for BaseDatasetExporter and its helper classes."""

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from DashAI.back.dataset_exporters.base_dataset_exporter import (
    BaseDatasetExporter,
    DatasetExportValidationError,
    ExportPayload,
    ExportResult,
)

VALID_PARAMS = {"name": "Iris", "description": "Classic iris dataset."}


class ConcreteExporter(BaseDatasetExporter):
    DISPLAY_NAME = "Test Exporter"
    DESCRIPTION = "A test exporter"

    def __init__(self):
        self.calls = []

    def validate(self, dataset, params):
        self.calls.append("validate")
        return super().validate(dataset, params)

    def prepare(self, dataset, params, temp_path):
        self.calls.append("prepare")
        return ExportPayload(files=[f"{temp_path}/data.csv"], metadata=params)

    def upload(self, payload, params):
        self.calls.append("upload")
        return ExportResult(remote_id="42", url="https://example.com/d/42")


def _dataset(num_rows=10):
    dataset = MagicMock()
    dataset.num_rows = num_rows
    return dataset


def test_exporter_has_type():
    assert ConcreteExporter.TYPE == "DatasetExporter"


def test_base_exporter_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseDatasetExporter()


def test_subclass_without_upload_cannot_be_instantiated():
    class MissingUpload(BaseDatasetExporter):
        def prepare(self, dataset, params, temp_path):
            return ExportPayload()

    with pytest.raises(TypeError):
        MissingUpload()


def test_export_runs_validate_prepare_upload_in_order():
    exporter = ConcreteExporter()
    result = exporter.export(_dataset(), VALID_PARAMS, "/tmp/export")

    assert exporter.calls == ["validate", "prepare", "upload"]
    assert result == ExportResult(remote_id="42", url="https://example.com/d/42")


def test_export_stops_when_validation_fails():
    exporter = ConcreteExporter()

    with pytest.raises(DatasetExportValidationError) as exc_info:
        exporter.export(_dataset(num_rows=0), VALID_PARAMS, "/tmp/export")

    assert exc_info.value.errors == ["The dataset has no rows."]
    assert exporter.calls == ["validate"]


@pytest.mark.parametrize("missing", ["name", "description"])
def test_export_rejects_params_missing_schema_fields(missing):
    exporter = ConcreteExporter()
    params = {k: v for k, v in VALID_PARAMS.items() if k != missing}

    with pytest.raises(ValidationError):
        exporter.export(_dataset(), params, "/tmp/export")

    assert exporter.calls == []


def test_default_validate_accepts_valid_input():
    assert ConcreteExporter().validate(_dataset(), VALID_PARAMS) == []


def test_default_validate_reports_blank_fields():
    errors = ConcreteExporter().validate(_dataset(), {"name": "  ", "description": ""})
    assert errors == [
        "The dataset name cannot be blank.",
        "The dataset description cannot be blank.",
    ]


def test_get_remote_status_defaults_to_none():
    assert ConcreteExporter().get_remote_status("42") is None


def test_validation_error_keeps_errors_and_joins_message():
    error = DatasetExportValidationError(["first", "second"])
    assert error.errors == ["first", "second"]
    assert str(error) == "first; second"


def test_schema_exposes_common_fields():
    properties = ConcreteExporter.get_schema()["properties"]
    assert {"name", "description"} <= set(properties)


def test_export_payload_defaults_to_empty():
    payload = ExportPayload()
    assert payload.files == []
    assert payload.metadata == {}

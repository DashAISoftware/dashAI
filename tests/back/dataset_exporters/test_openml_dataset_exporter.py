"""Tests for OpenMLDatasetExporter and OpenMLExportSchema."""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import arff
import pandas as pd
import pyarrow as pa
import pytest
from pydantic import ValidationError

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.dataset_exporters.base_dataset_exporter import (
    ExportPayload,
    ExportResult,
)
from DashAI.back.dataset_exporters.openml_dataset_exporter import (
    OpenMLDatasetExporter,
    OpenMLExportSchema,
)
from DashAI.back.dependencies.config_builder import get_initial_components
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.value_types import Binary, Float, Integer

VALID_PARAMS = {
    "name": "iris",
    "description": "Classic iris dataset.",
    "default_target_attribute": "class",
    "licence": "CC0",
    "creator": "R. A. Fisher",
    "contributor": None,
    "collection_date": "1936",
    "language": "English",
    "ignore_attribute": ["id"],
    "citation": None,
    "original_data_url": None,
}


def _dataset(columns=("id", "sepal_length", "class"), num_rows=150, types=None):
    dataset = MagicMock()
    dataset.num_rows = num_rows
    dataset.column_names = list(columns)
    dataset.types = types or {}
    return dataset


def _real_dataset():
    """Small DashAIDataset with numeric, binary and categorical columns."""
    table = pa.table(
        {
            "id": pa.array([1, 2, 3, 4], pa.int64()),
            "sepal_length": pa.array([5.1, 4.9, None, 6.3], pa.float64()),
            "photo": pa.array([b"a", b"b", b"c", b"d"], pa.binary()),
            "class": pa.array(["setosa", "virginica", "setosa", None]),
        }
    )
    types = {
        "id": Integer(pa.int64()),
        "sepal_length": Float(pa.float64()),
        "photo": Binary(pa.binary()),
        "class": Categorical(["setosa", "virginica", "setosa", None]),
    }
    return DashAIDataset(table, types=types)


def _credential(events):
    """Fake OpenMLCredential whose configured() records when it is active."""

    @contextmanager
    def configured():
        events.append("enter")
        yield
        events.append("exit")

    credential = MagicMock()
    credential.configured = configured
    return credential


def test_exporter_metadata():
    assert OpenMLDatasetExporter.TYPE == "DatasetExporter"
    assert OpenMLDatasetExporter.SCHEMA is OpenMLExportSchema
    assert OpenMLDatasetExporter.REQUIRED_CREDENTIALS == ["OpenMLCredential"]
    assert OpenMLDatasetExporter.SOURCE_NAME == "OpenMLDatasetSource"


def test_exporter_is_registered():
    assert OpenMLDatasetExporter in get_initial_components()


def test_schema_accepts_valid_params():
    params = OpenMLExportSchema.model_validate(VALID_PARAMS).model_dump()
    assert params["default_target_attribute"] == "class"
    assert params["ignore_attribute"] == ["id"]


def test_schema_rejects_unknown_licence():
    with pytest.raises(ValidationError):
        OpenMLExportSchema.model_validate({**VALID_PARAMS, "licence": "MIT"})


def test_schema_requires_target_column():
    params = {k: v for k, v in VALID_PARAMS.items() if k != "default_target_attribute"}
    with pytest.raises(ValidationError):
        OpenMLExportSchema.model_validate(params)


def test_schema_exposes_openml_fields():
    properties = OpenMLDatasetExporter.get_schema()["properties"]
    assert {
        "name",
        "description",
        "default_target_attribute",
        "licence",
        "ignore_attribute",
    } <= set(properties)


def test_validate_accepts_valid_input():
    assert OpenMLDatasetExporter().validate(_dataset(), VALID_PARAMS) == []


def test_validate_reports_missing_target():
    params = {**VALID_PARAMS, "default_target_attribute": "species"}
    errors = OpenMLDatasetExporter().validate(_dataset(), params)
    assert errors == ["The target column 'species' is not in the dataset."]


def test_validate_rejects_unsupported_target_type():
    dataset = _dataset(types={"class": Binary(pa.binary())})
    errors = OpenMLDatasetExporter().validate(dataset, VALID_PARAMS)
    assert errors == ["The target column 'class' has a type OpenML cannot store."]


def test_validate_reports_missing_ignored_columns():
    params = {**VALID_PARAMS, "ignore_attribute": ["id", "row"]}
    errors = OpenMLDatasetExporter().validate(_dataset(), params)
    assert errors == ["The ignored columns ['row'] are not in the dataset."]


def test_validate_rejects_target_in_ignored_columns():
    params = {**VALID_PARAMS, "ignore_attribute": ["class"]}
    errors = OpenMLDatasetExporter().validate(_dataset(), params)
    assert errors == ["The target column cannot also be an ignored column."]


def test_validate_keeps_base_errors():
    errors = OpenMLDatasetExporter().validate(_dataset(num_rows=0), VALID_PARAMS)
    assert "The dataset has no rows." in errors


def test_prepare_builds_openml_dataset():
    payload = OpenMLDatasetExporter().prepare(
        _real_dataset(), {**VALID_PARAMS, "ignore_attribute": ["id", "photo"]}, "."
    )
    openml_dataset = payload.metadata["openml_dataset"]

    assert payload.metadata["dropped_columns"] == ["photo"]
    assert openml_dataset.name == "iris"
    assert openml_dataset.licence == "CC0"
    assert openml_dataset.default_target_attribute == "class"
    assert openml_dataset.ignore_attribute == ["id"]

    attributes = dict(arff.loads(openml_dataset._dataset)["attributes"])
    assert "photo" not in attributes
    assert attributes["class"] == ["setosa", "virginica"]
    assert attributes["id"] == "INTEGER"


def test_upload_publishes_inside_configured_credential():
    events = []
    openml_dataset = MagicMock(dataset_id=123, openml_url="https://test/d/123")
    openml_dataset.publish.side_effect = lambda: events.append("publish")
    payload = ExportPayload(
        metadata={"openml_dataset": openml_dataset, "dropped_columns": ["photo"]}
    )
    exporter = OpenMLDatasetExporter()

    with patch.object(exporter, "get_credential", return_value=_credential(events)):
        result = exporter.upload(payload, VALID_PARAMS)

    assert events == ["enter", "publish", "exit"]
    assert result == ExportResult(
        remote_id="123",
        url="https://test/d/123",
        detail={"dropped_columns": ["photo"]},
    )


def test_get_remote_status_returns_openml_status():
    exporter = OpenMLDatasetExporter()
    listing = pd.DataFrame([{"did": 123, "status": "in_preparation"}])

    with (
        patch.object(exporter, "get_credential", return_value=_credential([])),
        patch("openml.datasets.list_datasets", return_value=listing) as list_mock,
    ):
        assert exporter.get_remote_status("123") == "in_preparation"
    assert list_mock.call_args.kwargs["data_id"] == [123]


def test_get_remote_status_unknown_dataset():
    exporter = OpenMLDatasetExporter()

    with (
        patch.object(exporter, "get_credential", return_value=_credential([])),
        patch("openml.datasets.list_datasets", return_value=pd.DataFrame()),
    ):
        assert exporter.get_remote_status("999") is None

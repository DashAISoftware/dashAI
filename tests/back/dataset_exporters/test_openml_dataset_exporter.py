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
    COLUMN_FIELD_KEY,
    CompatibilityStatus,
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


def test_schema_marks_the_column_fields():
    properties = OpenMLDatasetExporter.get_schema()["properties"]
    columns = {
        key: prop[COLUMN_FIELD_KEY]
        for key, prop in properties.items()
        if COLUMN_FIELD_KEY in prop
    }

    assert columns == {
        "default_target_attribute": "single",
        "ignore_attribute": "multiple",
    }


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


def test_check_dataset_accepts_tabular_columns():
    column_types = {
        "id": Integer(pa.int64()),
        "sepal_length": Float(pa.float64()),
        "class": Categorical(["setosa", "virginica"]),
    }

    compatibility = OpenMLDatasetExporter().check_dataset(column_types)

    assert compatibility.status == CompatibilityStatus.COMPATIBLE
    assert compatibility.unsupported_columns == []


def test_check_dataset_warns_about_columns_left_out():
    column_types = {
        "price": Float(pa.float64()),
        "photo": Binary(pa.binary()),
        "category": Categorical(["a", "b"]),
    }

    compatibility = OpenMLDatasetExporter().check_dataset(column_types)

    assert compatibility.status == CompatibilityStatus.WARNING
    assert compatibility.unsupported_columns == ["photo"]
    assert "photo" in compatibility.messages[0]


def test_check_dataset_refuses_when_too_little_would_remain():
    # Like an image dataset: the image is dropped and only the label is left.
    column_types = {
        "image": Binary(pa.binary()),
        "label": Categorical(["a", "b"]),
    }

    compatibility = OpenMLDatasetExporter().check_dataset(column_types)

    assert compatibility.status == CompatibilityStatus.INCOMPATIBLE
    assert compatibility.unsupported_columns == ["image"]


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


def test_validate_accepts_accents_it_can_convert():
    params = {
        **VALID_PARAMS,
        "name": "energía año",
        "description": "Consumo de energía",
    }
    assert OpenMLDatasetExporter().validate(_dataset(), params) == []


def test_validate_rejects_characters_it_cannot_convert():
    params = {
        **VALID_PARAMS,
        "name": "iris/v2",
        "description": "Price in €",
        "citation": "Fisher ✓",
    }

    errors = OpenMLDatasetExporter().validate(_dataset(), params)

    assert errors == [
        "The name has characters OpenML does not accept: '/'.",
        "The description has characters OpenML does not accept: '€'.",
        "The citation has characters OpenML does not accept: '✓'.",
    ]


def test_get_warnings_announces_converted_text():
    params = {
        **VALID_PARAMS,
        "name": "Mi dataset de energía",
        "description": "Consumo de energía",
        "citation": "Pérez (2024)",
    }

    warnings = OpenMLDatasetExporter().get_warnings(_dataset(), params)

    assert len(warnings) == 3
    assert "'Mi_dataset_de_energia'" in warnings[0]
    assert "description" in warnings[1]
    assert "citation" in warnings[2]


def test_get_warnings_is_empty_for_plain_text():
    assert OpenMLDatasetExporter().get_warnings(_dataset(), VALID_PARAMS) == []


def test_get_warnings_lists_renamed_columns():
    dataset = _dataset(columns=("Building Type", "Energía", "class"))

    warnings = OpenMLDatasetExporter().get_warnings(dataset, VALID_PARAMS)

    assert warnings == [
        "Columns will be renamed, since OpenML does not accept spaces or "
        "accents in column names: 'Building Type' to 'Building_Type', "
        "'Energía' to 'Energia'."
    ]


def test_validate_rejects_column_names_it_cannot_convert():
    dataset = _dataset(columns=("price/kg", "id", "class"))

    errors = OpenMLDatasetExporter().validate(dataset, VALID_PARAMS)

    assert errors == [
        "The columns ['price/kg'] have characters OpenML does not accept in "
        "column names."
    ]


def test_validate_rejects_columns_that_would_share_a_name():
    dataset = _dataset(columns=("total cost", "total_cost", "id", "class"))

    errors = OpenMLDatasetExporter().validate(dataset, VALID_PARAMS)

    assert errors == [
        "Several columns would be renamed to the same name ['total_cost']; "
        "rename them in DashAI first."
    ]


def test_prepare_renames_columns_target_and_ignored_together():
    table = pa.table(
        {
            "Building ID": pa.array([1, 2, 3], pa.int64()),
            "Square Footage": pa.array([7063.0, 44372.0, 19255.0], pa.float64()),
            "Building Type": pa.array(["Residential", "Commercial", "Industrial"]),
        }
    )
    dataset = DashAIDataset(
        table,
        types={
            "Building ID": Integer(pa.int64()),
            "Square Footage": Float(pa.float64()),
            "Building Type": Categorical(["Residential", "Commercial", "Industrial"]),
        },
    )
    params = {
        **VALID_PARAMS,
        "default_target_attribute": "Building Type",
        "ignore_attribute": ["Building ID"],
    }

    payload = OpenMLDatasetExporter().prepare(dataset, params, ".")
    openml_dataset = payload.metadata["openml_dataset"]
    attributes = dict(arff.loads(openml_dataset._dataset)["attributes"])

    assert set(attributes) == {"Building_ID", "Square_Footage", "Building_Type"}
    assert openml_dataset.default_target_attribute == "Building_Type"
    assert openml_dataset.ignore_attribute == ["Building_ID"]


def test_prepare_sends_converted_text():
    params = {
        **VALID_PARAMS,
        "name": "Mi dataset de energía",
        "description": "Consumo de energía en años",
        "citation": "Pérez (2024)",
    }

    payload = OpenMLDatasetExporter().prepare(_real_dataset(), params, ".")
    openml_dataset = payload.metadata["openml_dataset"]

    assert openml_dataset.name == "Mi_dataset_de_energia"
    assert openml_dataset.description == "Consumo de energia en anos"
    assert openml_dataset.citation == "Perez (2024)"


def test_prepare_leaves_blank_optional_fields_out_of_the_description():
    # OpenML rejects empty elements such as <oml:citation></oml:citation>.
    params = {**VALID_PARAMS, "citation": "", "creator": "  ", "language": None}
    payload = OpenMLDatasetExporter().prepare(_real_dataset(), params, ".")
    xml = payload.metadata["openml_dataset"]._to_xml()

    assert "oml:citation" not in xml
    assert "oml:creator" not in xml
    assert "oml:language" not in xml
    assert "<oml:collection_date>1936</oml:collection_date>" in xml


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

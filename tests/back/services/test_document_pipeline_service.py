"""Tests for the batch document converter pipeline."""

import pyarrow as pa
import pytest

from DashAI.back.converters.base_converter import BaseConverter, BaseConverterSchema
from DashAI.back.converters.document.text_splitter import TextSplitter
from DashAI.back.converters.document_converter import DocumentConverter
from DashAI.back.converters.simple_converters.character_replacer import (
    CharacterReplacer,
)
from DashAI.back.core.data_kinds import DATASET, DOCUMENT
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.exploration.explorers.describe_explorer import DescribeExplorer
from DashAI.back.services.documents.document_pipeline_service import (
    PIPELINE_METADATA_KEY,
    DocumentPipelineDownloadError,
    DocumentPipelineInvalidError,
    DocumentPipelineService,
)
from DashAI.back.types.dashai_image import DashAIImage
from DashAI.back.types.value_types import Text
from tests.back.document_fixtures import build_document, image, text


class _DatasetOnly(BaseConverter):
    """A converter that only runs on datasets."""

    SCHEMA = BaseConverterSchema
    metadata = {"data_kinds": [DATASET], "allowed_types": [Text]}

    def get_output_type(self, column_name=None):
        return Text(arrow_type=pa.string())

    def fit(self, x, y=None):
        return self

    def transform(self, x, y=None):
        return x


class _RowChanger(BaseConverter):
    """A non document converter that changes the row count."""

    SCHEMA = BaseConverterSchema
    CHANGES_ROW_COUNT = True
    metadata = {"data_kinds": [DOCUMENT]}

    def get_output_type(self, column_name=None):
        return Text(arrow_type=pa.string())

    def fit(self, x, y=None):
        return self

    def transform(self, x, y=None):
        return x


class _FakeOCR(DocumentConverter):
    """Turn every image into a Text item without a model."""

    SCHEMA = BaseConverterSchema
    metadata = {"allowed_types": [DashAIImage], "allowed_dtypes": []}

    def transform(self, x, y=None):
        count = len(x)
        return self.items_result(
            [f"read {index}. end" for index in range(count)], list(range(count))
        )


class _SupervisedOCR(_FakeOCR):
    SUPERVISED = True


class _DownloadableOCR(_FakeOCR):
    REQUIRES_DOWNLOAD = True
    downloaded = False

    @classmethod
    def is_downloaded(cls):
        return cls.downloaded


class _DocumentTypesConverter(_FakeOCR):
    metadata = {
        "document_allowed_types": [Text],
        "allowed_types": [Text, DashAIImage],
        "allowed_dtypes": [],
    }


def _service():
    registry = ComponentRegistry(
        [
            TextSplitter,
            CharacterReplacer,
            _FakeOCR,
            _SupervisedOCR,
            _DownloadableOCR,
            _DatasetOnly,
            _RowChanger,
        ]
    )
    return DocumentPipelineService(registry)


def _layout(document):
    return [
        (item.position, item.type.display_name(), item.content)
        for item in document.items()
    ]


def test_validate_returns_a_normalized_pipeline():
    pipeline = [{"converter": "TextSplitter", "params": {"split_by": "Lines"}}]

    normalized = _service().validate(pipeline)

    assert normalized == pipeline
    assert normalized is not pipeline


@pytest.mark.parametrize("pipeline", [None, []])
def test_validate_returns_none_for_an_empty_pipeline(pipeline):
    assert _service().validate(pipeline) is None


def test_validate_rejects_an_unknown_converter():
    with pytest.raises(DocumentPipelineInvalidError, match="does not exist"):
        _service().validate([{"converter": "NopeConverter", "params": {}}])


def test_validate_rejects_a_dataset_only_converter():
    with pytest.raises(DocumentPipelineInvalidError, match="runs on datasets"):
        _service().validate([{"converter": "_DatasetOnly", "params": {}}])


def test_validate_rejects_a_supervised_converter():
    with pytest.raises(DocumentPipelineInvalidError, match="supervised"):
        _service().validate([{"converter": "_SupervisedOCR", "params": {}}])


def test_validate_rejects_a_row_changing_non_document_converter():
    with pytest.raises(DocumentPipelineInvalidError, match="DocumentConverter"):
        _service().validate([{"converter": "_RowChanger", "params": {}}])


def test_validate_rejects_invalid_params():
    with pytest.raises(DocumentPipelineInvalidError, match="split_by"):
        _service().validate(
            [{"converter": "TextSplitter", "params": {"split_by": "Nope"}}]
        )


def test_validate_rejects_unknown_params():
    with pytest.raises(DocumentPipelineInvalidError, match="bogus"):
        _service().validate([{"converter": "TextSplitter", "params": {"bogus": 1}}])


def test_validate_fills_the_schema_defaults():
    normalized = _service().validate([{"converter": "TextSplitter", "params": {}}])

    assert normalized == [
        {"converter": "TextSplitter", "params": {"split_by": "Sentences"}}
    ]


def test_validate_rejects_a_constructor_error():
    with pytest.raises(DocumentPipelineInvalidError, match="char_to_replace"):
        _service().validate(
            [{"converter": "CharacterReplacer", "params": {"char_to_replace": ""}}]
        )


def test_validate_rejects_a_component_that_is_not_a_converter():
    registry = ComponentRegistry([DescribeExplorer])

    with pytest.raises(DocumentPipelineInvalidError, match="not a converter"):
        DocumentPipelineService(registry).validate(
            [{"converter": "DescribeExplorer", "params": {}}]
        )


def test_declared_types_prefers_document_allowed_types():
    assert DocumentPipelineService._declared_types(_DocumentTypesConverter) == ["Text"]


def test_validate_rejects_a_converter_that_must_be_downloaded():
    with pytest.raises(DocumentPipelineDownloadError, match="must be downloaded"):
        _service().validate([{"converter": "_DownloadableOCR", "params": {}}])


def test_validate_accepts_a_downloaded_converter():
    _DownloadableOCR.downloaded = True
    try:
        assert _service().validate([{"converter": "_DownloadableOCR", "params": {}}])
    finally:
        _DownloadableOCR.downloaded = False


def test_apply_splits_text_with_the_text_splitter():
    document = build_document(["One. Two."])
    converted = _service().apply(
        document, [{"converter": "TextSplitter", "params": {"split_by": "Sentences"}}]
    )

    assert converted[Text] == ["One.", "Two."]
    assert converted.metadata[PIPELINE_METADATA_KEY] == [
        {
            "converter": "TextSplitter",
            "status": "applied",
            "content_types": ["Text"],
        }
    ]


def test_apply_scopes_the_ocr_to_images_automatically():
    document = build_document([text("Intro"), image(), text("End")])
    converted = _service().apply(document, [{"converter": "_FakeOCR", "params": {}}])

    assert _layout(converted) == [
        (0, "Text", "Intro"),
        (1, "Text", "read 0. end"),
        (2, "Text", "End"),
    ]
    assert converted.metadata[PIPELINE_METADATA_KEY][0]["content_types"] == ["Image"]


def test_apply_runs_the_steps_in_order():
    document = build_document([image()])
    converted = _service().apply(
        document,
        [
            {"converter": "_FakeOCR", "params": {}},
            {"converter": "TextSplitter", "params": {"split_by": "Sentences"}},
        ],
    )

    assert converted[Text] == ["read 0.", "end"]
    statuses = [entry["status"] for entry in converted.metadata[PIPELINE_METADATA_KEY]]
    assert statuses == ["applied", "applied"]


def test_apply_skips_a_step_without_matching_items():
    document = build_document(["Only text."])
    converted = _service().apply(document, [{"converter": "_FakeOCR", "params": {}}])

    assert converted[Text] == ["Only text."]
    assert converted.metadata[PIPELINE_METADATA_KEY] == [
        {
            "converter": "_FakeOCR",
            "status": "skipped",
            "content_types": ["Image"],
            "reason": "The document has no Image items.",
        }
    ]


def test_apply_does_not_mutate_the_input_when_every_step_is_skipped():
    document = build_document(["Only text."])
    original_metadata = dict(document.metadata)

    converted = _service().apply(document, [{"converter": "_FakeOCR", "params": {}}])

    assert converted is not document
    assert document.metadata == original_metadata
    assert PIPELINE_METADATA_KEY not in document.metadata
    assert converted.metadata[PIPELINE_METADATA_KEY][0]["status"] == "skipped"


def test_apply_keeps_the_other_items_when_a_step_only_sees_some_types():
    document = build_document([text("Keep me"), image()])
    converted = _service().apply(document, [{"converter": "_FakeOCR", "params": {}}])

    assert converted[Text] == ["Keep me", "read 0. end"]
    assert converted.count(DashAIImage) == 0

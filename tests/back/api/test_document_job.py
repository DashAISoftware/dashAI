"""Tests for DocumentJob, run directly against the API test app's container."""

import json
import os
import uuid
from pathlib import Path

import pytest

from DashAI.back.converters.base_converter import BaseConverterSchema
from DashAI.back.converters.document_converter import DocumentConverter
from DashAI.back.core.enums.status import DatafileStatus, DocumentStatus
from DashAI.back.dataloaders.classes.dashai_document import load_document
from DashAI.back.dependencies.database.models import DataDocument, Datafile
from DashAI.back.job.base_job import JobError
from DashAI.back.job.document_job import DocumentJob
from DashAI.back.services.documents.document_pipeline_service import (
    PIPELINE_METADATA_KEY,
)
from DashAI.back.types.dashai_image import DashAIImage
from DashAI.back.types.value_types import Text


def _create_row(
    client,
    file_name,
    dataloader="PlainTextDocumentDataLoader",
    dataloader_params=None,
    converter_pipeline=None,
):
    with client.app.container["session_factory"]() as db:
        row = DataDocument(
            name=f"doc_{uuid.uuid4().hex[:8]}",
            file_name=file_name,
            file_type=Path(file_name).suffix.lstrip(".").lower(),
            file_hash="",
            file_path="",
            dataloader=dataloader,
            dataloader_params=dataloader_params or {},
            content_counts={},
            converter_pipeline=converter_pipeline,
            status=DocumentStatus.NOT_STARTED,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id


def _get_row(client, document_id):
    with client.app.container["session_factory"]() as db:
        return db.get(DataDocument, document_id)


def _upload(tmp_path, file_name, content):
    temp_dir = tmp_path / f"upload_{uuid.uuid4().hex[:8]}"
    temp_dir.mkdir()
    file_path = temp_dir / file_name
    file_path.write_bytes(content)
    return temp_dir, file_path


def _documents_root(client):
    return Path(client.app.container["config"]["DOCUMENTS_PATH"])


def _create_datafile(client, local_path, status=DatafileStatus.READY):
    with client.app.container["session_factory"]() as db:
        row = Datafile(
            source_name="HuggingFaceDatasetSource",
            dataset_id=f"org/docs_{uuid.uuid4().hex[:8]}",
            name="docs",
            local_path=str(local_path),
            status=status,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id


def test_document_job_parses_and_stores_a_text_document(client, tmp_path):
    document_id = _create_row(
        client, "notes.txt", dataloader_params={"split_paragraphs": True}
    )
    temp_dir, file_path = _upload(
        tmp_path, "notes.txt", b"First paragraph.\n\nSecond paragraph."
    )
    DocumentJob(
        kwargs={
            "document_id": document_id,
            "file_path": str(file_path),
            "temp_dir": str(temp_dir),
            "filename": "notes.txt",
            "huey_id": "huey-document-job-1",
        }
    ).run()

    row = _get_row(client, document_id)
    assert row.status == DocumentStatus.FINISHED
    assert row.content_counts == {"Text": 2}
    assert row.total_pages is None
    assert row.huey_id == "huey-document-job-1"
    assert len(row.file_hash) == 64
    root = Path(row.file_path)
    assert root.parent == _documents_root(client).resolve()
    assert (root / "source" / "notes.txt").read_bytes() == (
        b"First paragraph.\n\nSecond paragraph."
    )
    assert load_document(str(root / "document"))[Text] == [
        "First paragraph.",
        "Second paragraph.",
    ]
    assert not temp_dir.exists()


def test_document_job_decodes_the_uploaded_file_name(client, tmp_path):
    document_id = _create_row(client, "my notes.txt")
    temp_dir, file_path = _upload(tmp_path, "my%20notes.txt", b"Body.")
    DocumentJob(
        kwargs={
            "document_id": document_id,
            "file_path": str(file_path),
            "temp_dir": str(temp_dir),
            "filename": "my%20notes.txt",
        }
    ).run()

    row = _get_row(client, document_id)
    assert row.status == DocumentStatus.FINISHED
    assert row.file_name == "my notes.txt"
    assert (Path(row.file_path) / "source" / "my notes.txt").is_file()


def test_document_job_cleans_up_when_the_loader_fails(client, tmp_path):
    document_id = _create_row(client, "broken.pdf", "PypdfDocumentDataLoader")
    temp_dir, file_path = _upload(tmp_path, "broken.pdf", b"not a pdf")
    before = set(os.listdir(_documents_root(client)))

    with pytest.raises(JobError, match="Error loading document"):
        DocumentJob(
            kwargs={
                "document_id": document_id,
                "file_path": str(file_path),
                "temp_dir": str(temp_dir),
                "filename": "broken.pdf",
            }
        ).run()

    row = _get_row(client, document_id)
    assert row.status == DocumentStatus.ERROR
    assert row.file_path == ""
    assert set(os.listdir(_documents_root(client))) == before
    assert not temp_dir.exists()


@pytest.mark.parametrize(
    ("dataloader", "message"),
    [
        ("MissingLoader", "is not registered"),
        ("CSVDataLoader", "loads datasets, not documents"),
    ],
)
def test_document_job_rejects_a_non_document_loader(
    client, tmp_path, dataloader, message
):
    document_id = _create_row(client, "notes.txt", dataloader)
    temp_dir, file_path = _upload(tmp_path, "notes.txt", b"Body.")

    with pytest.raises(JobError, match=message):
        DocumentJob(
            kwargs={
                "document_id": document_id,
                "file_path": str(file_path),
                "temp_dir": str(temp_dir),
                "filename": "notes.txt",
            }
        ).run()

    assert _get_row(client, document_id).status == DocumentStatus.ERROR


def test_document_job_requires_an_uploaded_file(client):
    document_id = _create_row(client, "notes.txt")
    with pytest.raises(JobError, match="No file was uploaded"):
        DocumentJob(kwargs={"document_id": document_id}).run()
    assert _get_row(client, document_id).status == DocumentStatus.ERROR


def test_document_job_requires_the_row(client, tmp_path):
    temp_dir, file_path = _upload(tmp_path, "notes.txt", b"Body.")
    with pytest.raises(JobError, match="not found"):
        DocumentJob(
            kwargs={
                "document_id": 999999,
                "file_path": str(file_path),
                "temp_dir": str(temp_dir),
                "filename": "notes.txt",
            }
        ).run()


def test_status_hooks_and_job_name(client):
    document_id = _create_row(client, "notes.txt")
    job = DocumentJob(kwargs={"document_id": document_id, "name": "Report"})
    job.set_status_as_delivered()
    assert _get_row(client, document_id).status == DocumentStatus.DELIVERED
    job.set_status_as_error()
    assert _get_row(client, document_id).status == DocumentStatus.ERROR
    assert job.get_job_name() == "Document: Report"
    assert DocumentJob(kwargs={"document_id": 1}).get_job_name() == "Document load"


def test_on_cancel_removes_partial_output(client, tmp_path):
    document_id = _create_row(client, "notes.txt")
    partial = _documents_root(client) / f"partial_{uuid.uuid4().hex[:8]}"
    (partial / "source").mkdir(parents=True)
    with client.app.container["session_factory"]() as db:
        row = db.get(DataDocument, document_id)
        row.file_path = str(partial)
        row.set_status_as_started()
        db.commit()
    temp_dir, _ = _upload(tmp_path, "notes.txt", b"Body.")

    DocumentJob(
        kwargs={"document_id": document_id, "temp_dir": str(temp_dir)}
    ).on_cancel()

    row = _get_row(client, document_id)
    assert row.status == DocumentStatus.ERROR
    assert row.file_path == ""
    assert not partial.exists()
    assert not temp_dir.exists()


def test_document_job_imports_a_file_from_a_hub_download(client, tmp_path):
    download = tmp_path / f"download_{uuid.uuid4().hex[:8]}"
    (download / "docs").mkdir(parents=True)
    (download / "docs" / "notes.txt").write_bytes(b"Hub paragraph.")
    (download / "readme.txt").write_bytes(b"Other.")
    datafile_id = _create_datafile(client, download)
    document_id = _create_row(client, "notes.txt")

    DocumentJob(
        kwargs={
            "document_id": document_id,
            "datafile_id": datafile_id,
            "selected_file": "docs/notes.txt",
        }
    ).run()

    row = _get_row(client, document_id)
    assert row.status == DocumentStatus.FINISHED
    assert row.file_name == "notes.txt"
    assert row.file_type == "txt"
    assert len(row.file_hash) == 64
    root = Path(row.file_path)
    assert (root / "source" / "notes.txt").read_bytes() == b"Hub paragraph."
    assert load_document(str(root / "document"))[Text] == ["Hub paragraph."]
    assert (download / "docs" / "notes.txt").is_file()


def test_document_job_reports_a_hub_download_that_is_not_ready(client, tmp_path):
    datafile_id = _create_datafile(client, tmp_path, DatafileStatus.DOWNLOADING)
    document_id = _create_row(client, "notes.txt")
    before = set(os.listdir(_documents_root(client)))

    with pytest.raises(JobError, match=f"Datafile {datafile_id} is not ready."):
        DocumentJob(
            kwargs={"document_id": document_id, "datafile_id": datafile_id}
        ).run()

    row = _get_row(client, document_id)
    assert row.status == DocumentStatus.ERROR
    assert row.file_path == ""
    assert set(os.listdir(_documents_root(client))) == before


def test_a_hub_document_job_is_enqueued_without_a_file(client, tmp_path):
    download = tmp_path / f"download_{uuid.uuid4().hex[:8]}"
    download.mkdir()
    (download / "notes.txt").write_bytes(b"Queued paragraph.")
    datafile_id = _create_datafile(client, download)
    document_id = _create_row(client, "notes.txt")

    response = client.post(
        "/api/v1/job/",
        data={
            "job_type": "DocumentJob",
            "kwargs": json.dumps(
                {
                    "document_id": document_id,
                    "name": "Queued",
                    "datafile_id": datafile_id,
                    "selected_file": "notes.txt",
                }
            ),
        },
    )

    assert response.status_code == 201, response.text
    row = _get_row(client, document_id)
    assert row.status == DocumentStatus.FINISHED
    assert load_document(str(Path(row.file_path) / "document"))[Text] == [
        "Queued paragraph."
    ]


def test_document_job_applies_the_pipeline_before_saving(client, tmp_path):
    document_id = _create_row(
        client,
        "notes.txt",
        converter_pipeline=[
            {"converter": "TextSplitter", "params": {"split_by": "Sentences"}}
        ],
    )
    temp_dir, file_path = _upload(tmp_path, "notes.txt", b"One. Two.")

    DocumentJob(
        kwargs={
            "document_id": document_id,
            "file_path": str(file_path),
            "temp_dir": str(temp_dir),
            "filename": "notes.txt",
        }
    ).run()

    row = _get_row(client, document_id)
    assert row.status == DocumentStatus.FINISHED
    assert row.content_counts == {"Text": 2}
    document = load_document(str(Path(row.file_path) / "document"))
    assert document[Text] == ["One.", "Two."]
    assert document.metadata[PIPELINE_METADATA_KEY] == [
        {
            "converter": "TextSplitter",
            "status": "applied",
            "content_types": ["Text"],
        }
    ]


class _ExplodingConverter(DocumentConverter):
    """Fails once it has to convert the selected items."""

    SCHEMA = BaseConverterSchema
    metadata = {"allowed_types": [Text]}

    def transform(self, x, y=None):
        raise RuntimeError("pipeline exploded")


def test_document_job_cleans_up_when_the_pipeline_fails(client, tmp_path):
    registry = client.app.container["component_registry"]
    registry.register_component(_ExplodingConverter)
    before = set(os.listdir(_documents_root(client)))
    try:
        document_id = _create_row(
            client,
            "notes.txt",
            converter_pipeline=[{"converter": "_ExplodingConverter", "params": {}}],
        )
        temp_dir, file_path = _upload(tmp_path, "notes.txt", b"Body.")

        with pytest.raises(JobError, match="pipeline"):
            DocumentJob(
                kwargs={
                    "document_id": document_id,
                    "file_path": str(file_path),
                    "temp_dir": str(temp_dir),
                    "filename": "notes.txt",
                }
            ).run()
    finally:
        registry.unregister_component(_ExplodingConverter)

    row = _get_row(client, document_id)
    assert row.status == DocumentStatus.ERROR
    assert row.file_path == ""
    assert set(os.listdir(_documents_root(client))) == before
    assert not temp_dir.exists()


class _ImageOnlyConverter(DocumentConverter):
    """Only ever handles Image items, so a text document skips it."""

    REQUIRES_DOWNLOAD = False
    SCHEMA = BaseConverterSchema
    metadata = {"allowed_types": [DashAIImage]}

    def transform(self, x, y=None):
        return self.items_result([], [])


def test_document_job_skips_a_pipeline_step_without_items(client, tmp_path):
    registry = client.app.container["component_registry"]
    registry.register_component(_ImageOnlyConverter)
    try:
        document_id = _create_row(
            client,
            "notes.txt",
            converter_pipeline=[{"converter": "_ImageOnlyConverter", "params": {}}],
        )
        temp_dir, file_path = _upload(tmp_path, "notes.txt", b"Only text.")

        DocumentJob(
            kwargs={
                "document_id": document_id,
                "file_path": str(file_path),
                "temp_dir": str(temp_dir),
                "filename": "notes.txt",
            }
        ).run()
    finally:
        registry.unregister_component(_ImageOnlyConverter)

    row = _get_row(client, document_id)
    assert row.status == DocumentStatus.FINISHED
    assert row.content_counts == {"Text": 1}
    document = load_document(str(Path(row.file_path) / "document"))
    assert document.metadata[PIPELINE_METADATA_KEY] == [
        {
            "converter": "_ImageOnlyConverter",
            "status": "skipped",
            "content_types": ["Image"],
            "reason": "The document has no Image items.",
        }
    ]

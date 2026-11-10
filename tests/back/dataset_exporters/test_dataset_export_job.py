"""Tests for DatasetExportJob."""

from unittest.mock import MagicMock, patch

import pytest
from kink import di
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from DashAI.back.core.enums.status import DatasetExportStatus, DatasetStatus
from DashAI.back.dataset_exporters.base_dataset_exporter import (
    BaseDatasetExporter,
    ExportPayload,
    ExportResult,
)
from DashAI.back.dependencies.config_builder import get_initial_components
from DashAI.back.dependencies.database.models import Base, Dataset, DatasetExport
from DashAI.back.job.base_job import JobError
from DashAI.back.job.dataset_export_job import DatasetExportJob, export_temp_dir

PARAMS = {"name": "iris", "description": "Classic iris dataset."}


class _RecordingExporter(BaseDatasetExporter):
    """Exporter that records the export status seen during each phase."""

    seen: list = []
    fail_on_upload = False

    def prepare(self, dataset, params, temp_path):
        _RecordingExporter.seen.append(("prepare", _status_of_last_export()))
        return ExportPayload(files=[temp_path])

    def upload(self, payload, params):
        _RecordingExporter.seen.append(("upload", _status_of_last_export()))
        if _RecordingExporter.fail_on_upload:
            raise RuntimeError("platform rejected the dataset")
        return ExportResult(remote_id="533", url="https://test.openml.org/d/533")


def _status_of_last_export():
    with di["session_factory"]() as db:
        return db.query(DatasetExport).order_by(DatasetExport.id.desc()).first().status


@pytest.fixture(name="factory")
def fixture_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    class _Factory:
        def __call__(self):
            return factory()

    di["session_factory"] = _Factory()
    di["component_registry"] = {
        "RecordingExporter": {"class": _RecordingExporter, "type": "DatasetExporter"},
        "NotAnExporter": {"class": object, "type": "Model"},
    }
    _RecordingExporter.seen = []
    _RecordingExporter.fail_on_upload = False
    with patch(
        "DashAI.back.dataloaders.classes.dashai_dataset.load_dataset",
        return_value=MagicMock(num_rows=150),
    ):
        yield factory
    del di["session_factory"]
    del di["component_registry"]
    engine.dispose()


def _export(factory, exporter="RecordingExporter", status=DatasetStatus.FINISHED):
    with factory() as db:
        dataset = Dataset(name="iris", file_path="/tmp/iris", status=status)
        db.add(dataset)
        db.commit()
        export = DatasetExport(
            dataset_id=dataset.id,
            dataset_name=dataset.name,
            exporter_name=exporter,
            params=PARAMS,
        )
        db.add(export)
        db.commit()
        return export.id


def _row(factory, export_id):
    with factory() as db:
        return db.get(DatasetExport, export_id)


def _run(export_id, **kwargs):
    DatasetExportJob(kwargs={"export_id": export_id, **kwargs}).run()


def test_the_job_implements_every_abstract_method_of_base_job():
    DatasetExportJob(kwargs={"export_id": 1})


def test_the_job_is_registered():
    assert DatasetExportJob in get_initial_components()


def test_a_successful_export_walks_through_every_status(factory):
    export_id = _export(factory)

    _run(export_id, huey_id="task-1")

    assert _RecordingExporter.seen == [
        ("prepare", DatasetExportStatus.PREPARING),
        ("upload", DatasetExportStatus.UPLOADING),
    ]
    row = _row(factory, export_id)
    assert row.status == DatasetExportStatus.PUBLISHED
    assert row.remote_id == "533"
    assert row.remote_url == "https://test.openml.org/d/533"
    assert row.huey_id == "task-1"
    assert row.error_message is None
    assert not export_temp_dir(export_id).exists()


def test_a_failed_upload_marks_the_export_as_error(factory):
    export_id = _export(factory)
    _RecordingExporter.fail_on_upload = True

    with pytest.raises(JobError, match="platform rejected the dataset"):
        _run(export_id)

    row = _row(factory, export_id)
    assert row.status == DatasetExportStatus.ERROR
    assert row.error_message == "platform rejected the dataset"
    assert not export_temp_dir(export_id).exists()


def test_invalid_params_mark_the_export_as_error(factory):
    export_id = _export(factory)
    with factory() as db:
        db.get(DatasetExport, export_id).params = {**PARAMS, "name": "  "}
        db.commit()

    with pytest.raises(JobError, match="name cannot be blank"):
        _run(export_id)

    assert _RecordingExporter.seen == []
    assert _row(factory, export_id).status == DatasetExportStatus.ERROR


@pytest.mark.parametrize(
    ("exporter", "message"),
    [
        ("MissingExporter", "not found"),
        ("NotAnExporter", "is not a DatasetExporter"),
    ],
)
def test_an_unknown_exporter_marks_the_export_as_error(factory, exporter, message):
    export_id = _export(factory, exporter=exporter)

    with pytest.raises(JobError, match=message):
        _run(export_id)

    assert _row(factory, export_id).status == DatasetExportStatus.ERROR


def test_a_dataset_that_is_not_ready_is_refused(factory):
    export_id = _export(factory, status=DatasetStatus.STARTED)

    with pytest.raises(JobError, match="is not ready"):
        _run(export_id)

    assert _row(factory, export_id).status == DatasetExportStatus.ERROR


def test_a_deleted_dataset_is_refused(factory):
    export_id = _export(factory)
    with factory() as db:
        db.delete(db.get(DatasetExport, export_id).dataset)
        db.commit()

    with pytest.raises(JobError, match="no longer exists"):
        _run(export_id)

    assert _row(factory, export_id).status == DatasetExportStatus.ERROR


def test_a_missing_export_row_is_refused(factory):
    with pytest.raises(JobError, match="not found"):
        _run(999)


def test_the_queue_error_hook_keeps_the_worker_message(factory):
    export_id = _export(factory)
    with factory() as db:
        row = db.get(DatasetExport, export_id)
        row.error_message = "platform rejected the dataset"
        db.commit()

    DatasetExportJob(kwargs={"export_id": export_id}).set_status_as_error()

    row = _row(factory, export_id)
    assert row.status == DatasetExportStatus.ERROR
    assert row.error_message == "platform rejected the dataset"


def test_a_published_export_is_never_marked_as_error(factory):
    export_id = _export(factory)
    _run(export_id)

    DatasetExportJob(kwargs={"export_id": export_id}).set_status_as_error()

    assert _row(factory, export_id).status == DatasetExportStatus.PUBLISHED


def test_cancel_removes_the_scratch_directory():
    temp_dir = export_temp_dir(424242)
    temp_dir.mkdir(parents=True, exist_ok=True)
    (temp_dir / "data.arff").write_text("@RELATION iris")

    DatasetExportJob(kwargs={"export_id": 424242}).on_cancel()

    assert not temp_dir.exists()


def test_the_job_name_uses_the_dataset_name():
    job = DatasetExportJob(kwargs={"export_id": 1, "dataset_name": "iris"})
    assert job.get_job_name() == "Dataset export: iris"
    assert DatasetExportJob(kwargs={"export_id": 1}).get_job_name() == (
        "Dataset export"
    )

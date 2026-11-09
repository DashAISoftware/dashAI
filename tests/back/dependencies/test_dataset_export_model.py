import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from DashAI.back.core.enums.status import DatasetExportStatus
from DashAI.back.dependencies.database.models import Base, Dataset, DatasetExport


@pytest.fixture
def db():
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _dataset(db, name="iris"):
    dataset = Dataset(name=name, file_path="/tmp/iris")
    db.add(dataset)
    db.commit()
    return dataset


def _export(dataset, **overrides):
    values = {
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "exporter_name": "OpenMLDatasetExporter",
    }
    values.update(overrides)
    return DatasetExport(**values)


def test_defaults(db):
    export = _export(_dataset(db))
    db.add(export)
    db.commit()

    assert export.status == DatasetExportStatus.PENDING
    assert export.params == {}
    assert export.remote_id is None
    assert export.remote_url is None
    assert export.error_message is None
    assert export.created is not None
    assert export.last_modified is not None


def test_stores_params_and_publication_result(db):
    export = _export(_dataset(db), params={"name": "iris", "licence": "CC0"})
    db.add(export)
    db.commit()

    export.status = DatasetExportStatus.PUBLISHED
    export.remote_id = "533"
    export.remote_url = "https://test.openml.org/d/533"
    db.commit()
    db.expire_all()

    stored = db.get(DatasetExport, export.id)
    assert stored.status == DatasetExportStatus.PUBLISHED
    assert stored.params == {"name": "iris", "licence": "CC0"}
    assert stored.remote_url == "https://test.openml.org/d/533"


def test_dataset_lists_its_exports(db):
    dataset = _dataset(db)
    db.add_all([_export(dataset), _export(dataset)])
    db.commit()

    assert len(dataset.exports) == 2
    assert all(export.dataset is dataset for export in dataset.exports)


def test_export_survives_dataset_deletion(db):
    dataset = _dataset(db)
    export = _export(dataset, remote_url="https://test.openml.org/d/533")
    db.add(export)
    db.commit()

    db.delete(dataset)
    db.commit()
    db.expire_all()

    stored = db.get(DatasetExport, export.id)
    assert stored is not None
    assert stored.dataset_id is None
    assert stored.dataset_name == "iris"
    assert stored.remote_url == "https://test.openml.org/d/533"

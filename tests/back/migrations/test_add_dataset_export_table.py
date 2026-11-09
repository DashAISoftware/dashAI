import sqlalchemy as sa
from alembic.config import Config

from alembic import command

PARENT = "72db19a8ec8d"
REVISION = "7ececb94f26e"
DATASET_EXPORT_COLUMNS = {
    "id",
    "dataset_id",
    "dataset_name",
    "exporter_name",
    "params",
    "status",
    "remote_id",
    "remote_url",
    "error_message",
    "huey_id",
    "created",
    "last_modified",
}


def _config(db_path):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


def test_upgrade_creates_dataset_export_table(tmp_path):
    db_path = tmp_path / "test.db"
    cfg = _config(db_path)
    command.upgrade(cfg, PARENT)

    engine = sa.create_engine(f"sqlite:///{db_path}")
    assert not sa.inspect(engine).has_table("dataset_export")

    command.upgrade(cfg, REVISION)

    inspector = sa.inspect(engine)
    assert inspector.has_table("dataset_export")
    assert {c["name"] for c in inspector.get_columns("dataset_export")} == (
        DATASET_EXPORT_COLUMNS
    )
    assert "ix_dataset_export_dataset_id" in {
        index["name"] for index in inspector.get_indexes("dataset_export")
    }
    (foreign_key,) = inspector.get_foreign_keys("dataset_export")
    assert foreign_key["referred_table"] == "dataset"
    assert foreign_key["options"].get("ondelete") == "SET NULL"


def test_downgrade_drops_dataset_export_table(tmp_path):
    db_path = tmp_path / "test.db"
    cfg = _config(db_path)
    command.upgrade(cfg, REVISION)

    command.downgrade(cfg, PARENT)

    engine = sa.create_engine(f"sqlite:///{db_path}")
    assert not sa.inspect(engine).has_table("dataset_export")

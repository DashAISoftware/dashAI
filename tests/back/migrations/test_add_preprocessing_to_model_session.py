import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def test_migration_adds_preprocessing_columns(tmp_path):
    db_path = tmp_path / "test.db"
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    # Upgrade to the migration under test rather than to ``head``: once this
    # branch is merged into develop the head becomes a merge revision (two
    # parents), which makes the relative ``downgrade("-1")`` below ambiguous.
    # Targeting the revision keeps the downgrade unambiguous and tests exactly
    # this migration's up/down behavior.
    command.upgrade(alembic_cfg, "f4a91c62d8e7")

    engine = sa.create_engine(f"sqlite:///{db_path}")
    inspector = sa.inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("model_session")}

    assert {
        "preprocessing",
        "input_column_refs",
        "preprocessing_status",
        "preprocessing_error",
        "preprocessing_artifacts_path",
        "preprocessing_job_id",
    } <= columns

    command.downgrade(alembic_cfg, "-1")
    columns_after_downgrade = {
        c["name"] for c in sa.inspect(engine).get_columns("model_session")
    }
    assert "preprocessing" not in columns_after_downgrade

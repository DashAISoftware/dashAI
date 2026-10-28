import sqlalchemy as sa
from alembic.config import Config

from alembic import command

PARENT = "e7a2c5f9b1d3"
REVISION = "72db19a8ec8d"
CREDENTIAL_COLUMNS = {
    "id",
    "name",
    "encrypted_key",
    "verified",
    "created",
    "last_modified",
}


def _config(db_path):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


def test_recreates_credential_table_when_missing(tmp_path):
    db_path = tmp_path / "test.db"
    cfg = _config(db_path)
    command.upgrade(cfg, PARENT)

    # A database created on v0.9.7 reached this point without the table:
    # d4e8a2c6f0b1 sits below a revision it had already applied.
    engine = sa.create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(sa.text("DROP TABLE credential"))
    assert not sa.inspect(engine).has_table("credential")

    command.upgrade(cfg, REVISION)

    inspector = sa.inspect(engine)
    assert inspector.has_table("credential")
    assert {c["name"] for c in inspector.get_columns("credential")} == (
        CREDENTIAL_COLUMNS
    )
    assert ["name"] in [
        u["column_names"] for u in inspector.get_unique_constraints("credential")
    ]


def test_keeps_existing_credential_table_and_rows(tmp_path):
    db_path = tmp_path / "test.db"
    cfg = _config(db_path)
    command.upgrade(cfg, PARENT)

    engine = sa.create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO credential"
                " (name, encrypted_key, verified, created, last_modified)"
                " VALUES ('hf', 'secret', 1, '2026-10-27', '2026-10-27')"
            )
        )

    command.upgrade(cfg, REVISION)
    with engine.connect() as conn:
        rows = conn.execute(sa.text("SELECT name FROM credential")).all()
    assert rows == [("hf",)]

    command.downgrade(cfg, PARENT)
    assert sa.inspect(engine).has_table("credential")

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

BEFORE = "49d7035ce11f"


def test_migration_drops_the_plugin_tables_and_downgrade_restores_them(tmp_path):
    db_path = tmp_path / "test.db"
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    engine = sa.create_engine(f"sqlite:///{db_path}")

    command.upgrade(alembic_cfg, BEFORE)
    columns_before = {c["name"] for c in sa.inspect(engine).get_columns("plugin")}
    with engine.begin() as db:  # rows of the old mirror do not block it
        db.execute(
            sa.text(
                "INSERT INTO plugin (id, name, author, installed_version,"
                " lastest_version, status, summary, description,"
                " description_content_type, created, last_modified) VALUES"
                " (1, 'p', 'a', '1', '1', 'INSTALLED', '', '', 'text/plain',"
                " '2026-10-01', '2026-10-01')"
            )
        )
        db.execute(sa.text("INSERT INTO tag (plugin_id, name) VALUES (1, 'Model')"))

    command.upgrade(alembic_cfg, "head")
    assert {"plugin", "tag"}.isdisjoint(sa.inspect(engine).get_table_names())

    command.downgrade(alembic_cfg, BEFORE)
    inspector = sa.inspect(engine)
    assert {c["name"] for c in inspector.get_columns("plugin")} == columns_before
    assert {c["name"] for c in inspector.get_columns("tag")} == {
        "id",
        "plugin_id",
        "name",
    }

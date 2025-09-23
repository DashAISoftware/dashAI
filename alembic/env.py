import os
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from DashAI.back.dependencies.database import Base

config = context.config


def _resolve_url() -> str:
    """Get the database URL from command line arguments or default to a local SQLite database."""
    xargs = context.get_x_argument(as_dictionary=True)
    if "url" in xargs and xargs["url"]:
        return xargs["url"]

    home = Path.home()
    db_path = home / ".DashAI" / "db.sqlite"
    return f"sqlite:///{db_path}"


config.set_main_option("sqlalchemy.url", _resolve_url())

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = _resolve_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    ini = config.get_section(config.config_ini_section)
    ini = dict(ini or {})
    ini["sqlalchemy.url"] = _resolve_url()

    connectable = engine_from_config(
        ini,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

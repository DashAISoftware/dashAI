import os
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from DashAI.back.dependencies.database import Base

config = context.config


def _resolve_url() -> str:
    """
    Prioridad url sql:
      1) alembic -x url=...
      2) env var DATABASE_URL
      3) value already present in alembic.ini (config.get_main_option)
      4) fallback using the same logic as the application (~/.DashAI/db.sqlite)
    """
    # 1) cli -x url
    xargs = context.get_x_argument(as_dictionary=True)
    if xargs and xargs.get("url"):
        return xargs["url"]

    # 2) environment
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    # 3) value from alembic.ini (if any)
    cfg_url = config.get_main_option("sqlalchemy.url")
    if cfg_url and cfg_url != "sqlite:///":
        return cfg_url

    # 4) fallback - same as application config
    # Use the same default path as the application: ~/.DashAI/db.sqlite
    from DashAI.back.config import DefaultSettings
    settings = DefaultSettings()
    local_path = Path(settings.LOCAL_PATH).expanduser().absolute()
    db_path = local_path / settings.SQLITE_DB_PATH
    return f"sqlite:///{db_path}"


config.set_main_option("sqlalchemy.url", _resolve_url())

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
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
    ini = dict(config.get_section(config.config_ini_section) or {})

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

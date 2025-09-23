import logging
import os
import shutil
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from DashAI.back.dependencies.config_builder import build_config_dict

logger = logging.getLogger(__name__)

config = build_config_dict(local_path=Path("~/.DashAI"), logging_level="INFO")


def get_database_url() -> str:
    return f"sqlite:///{config['SQLITE_DB_PATH']}"


def get_sqlite_file_path() -> os.PathLike:
    return config["SQLITE_DB_PATH"]


def get_alembic_ini_path() -> os.PathLike:
    curr_path = Path(__file__).resolve().parents[4]
    return curr_path / "alembic.ini"


def alembic_config() -> Config:
    ini_path = get_alembic_ini_path()
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", get_database_url())
    return cfg


def run_migrations() -> None:
    cfg = alembic_config()
    command.upgrade(cfg, "head")


def backup_and_recreate_db() -> None:
    sqlite_file = get_sqlite_file_path()
    if sqlite_file.exists():
        ts = time.strftime("%Y%m%d-%H%M%S")
        backup = sqlite_file.with_suffix(f".bak-{ts}.sqlite3")
        shutil.copy2(sqlite_file, backup)
        sqlite_file.unlink()

    # Crear desde cero: sube hasta head
    run_migrations()


def migrate_on_startup() -> None:
    try:
        run_migrations()
    except Exception as exc:
        logger.error(
            (
                f"Error during migration: {exc}. "
                "Attempting to backup and recreate the database."
            )
        )
        backup_and_recreate_db()
        raise

import logging
import os
import shutil
import time
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)


def get_alembic_ini_path() -> Path:
    # TODO: this is a bit hacky, but it works for now
    curr_path = Path(__file__).resolve().parents[4]
    return curr_path / "alembic.ini"


def alembic_config(db_url: str) -> Config:
    ini_path = get_alembic_ini_path()
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def run_migrations(db_url: str) -> None:
    cfg = alembic_config(db_url=db_url)
    command.upgrade(cfg, "head")


def _resolve_db_url(sqlite_file_path: Path) -> str:
    """
    Resolve database URL with the same priority as alembic:
      1) env var DATABASE_URL
      2) fallback to sqlite file path

    This is mainly to use in tests, where we set the env var to a temp path.
    """
    # 1) environment variable
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    if not str(sqlite_file_path).startswith("sqlite:///"):
        return f"sqlite:///{sqlite_file_path}"

    # 2) fallback to provided sqlite file path
    return sqlite_file_path


def backup_and_recreate_db(db_url: str, sqlite_file_path: Path) -> None:
    # Only try to backup if it's a local SQLite file and DATABASE_URL env var not set
    env_url = os.getenv("DATABASE_URL")
    if not env_url and sqlite_file_path.exists():
        ts = time.strftime("%Y%m%d-%H%M%S")
        backup = sqlite_file_path.with_suffix(f".bak-{ts}.sqlite3")
        shutil.copy2(sqlite_file_path, backup)
        sqlite_file_path.unlink()

    run_migrations(db_url=db_url)


def migrate_on_startup(sqlite_file_path: Path) -> None:
    try:
        db_url = _resolve_db_url(sqlite_file_path)
        run_migrations(db_url=db_url)
    except Exception as exc:
        logger.error(
            (
                f"Error during migration: {exc}. "
                "Attempting to backup and recreate the database."
            )
        )
        db_url = _resolve_db_url(sqlite_file_path)
        backup_and_recreate_db(db_url=db_url, sqlite_file_path=sqlite_file_path)
        raise

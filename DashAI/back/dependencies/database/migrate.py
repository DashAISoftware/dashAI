import logging
import os
import shutil
import time
from pathlib import Path

from alembic import command
from alembic.config import Config

from DashAI.back.dependencies.database.utils import resolve_db_url

logger = logging.getLogger(__name__)


def alembic_config(db_url: str) -> Config:
    package_root = Path(__file__).absolute().parents[3]
    script_location = package_root / "alembic"

    cfg = Config()

    cfg.set_main_option("script_location", str(script_location))
    cfg.set_main_option("sqlalchemy.url", db_url)
    cfg.set_main_option("prepend_sys_path", str(package_root))
    cfg.set_main_option("version_path_separator", "os")
    return cfg


def run_migrations(db_url: str) -> None:
    cfg = alembic_config(db_url=db_url)
    command.upgrade(cfg, "head")


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
    db_url = resolve_db_url(sqlite_file_path)

    try:
        logger.info(f"Running migrations on database at {db_url}")
        run_migrations(db_url=db_url)
    except Exception as exc:
        logger.error(
            (
                f"Error during migration: {exc}. "
                "Attempting to backup and recreate the database."
            )
        )
        try:
            backup_and_recreate_db(db_url=db_url, sqlite_file_path=sqlite_file_path)
        except Exception as backup_exc:
            logger.error(
                f"Error during backup and recreate: {backup_exc}. "
                f"Original migration error: {exc}."
            )
            raise backup_exc from exc
        raise exc

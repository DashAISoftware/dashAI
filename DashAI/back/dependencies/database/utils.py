import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def find_entity_by_huey_id(huey_id: str) -> dict:
    """
    Find the entity associated with a huey_id and return its details.
    Returns None if no entity is found.
    """
    from kink import di

    from DashAI.back.dependencies.database.models import (
        Converter,
        Dataset,
        Explorer,
        GlobalExplainer,
        LocalExplainer,
        Run,
    )

    session_factory = di["session_factory"]

    with session_factory() as db:
        run = db.query(Run).filter(Run.huey_id == huey_id).first()
        if run:
            return {
                "entity_type": "train_model",
                "entity_id": run.id,
                "entity_name": run.name,
                "created_at": run.created,
                "last_modified": run.last_modified,
                "status": run.status,
            }

        dataset = db.query(Dataset).filter(Dataset.huey_id == huey_id).first()
        if dataset:
            return {
                "entity_type": "dataset",
                "entity_id": dataset.id,
                "entity_name": dataset.name,
                "created_at": dataset.created,
                "last_modified": dataset.last_modified,
                "status": dataset.status,
            }

        explorer = db.query(Explorer).filter(Explorer.huey_id == huey_id).first()
        if explorer:
            return {
                "entity_type": "explorer",
                "entity_id": explorer.id,
                "entity_name": explorer.name,
                "created_at": explorer.created,
                "last_modified": explorer.last_modified,
                "status": explorer.status,
            }

        global_explainer = (
            db.query(GlobalExplainer).filter(GlobalExplainer.huey_id == huey_id).first()
        )
        if global_explainer:
            return {
                "entity_type": "global_explainer",
                "entity_id": global_explainer.id,
                "entity_name": global_explainer.name,
                "created_at": global_explainer.created,
                "last_modified": global_explainer.last_modified,
            }

        local_explainer = (
            db.query(LocalExplainer).filter(LocalExplainer.huey_id == huey_id).first()
        )
        if local_explainer:
            return {
                "entity_type": "local_explainer",
                "entity_id": local_explainer.id,
                "entity_name": local_explainer.name,
                "created_at": local_explainer.created,
                "last_modified": local_explainer.last_modified,
            }

        converter = db.query(Converter).filter(Converter.huey_id == huey_id).first()
        if converter:
            return {
                "entity_type": "converter",
                "entity_id": converter.id,
                "entity_name": converter.name,
                "created_at": converter.created,
                "last_modified": converter.last_modified,
            }

        return None


def resolve_db_url(sqlite_file_path: Path) -> str:
    """
    Resolve database URL with the same priority as alembic:
      1) env var DATABASE_URL
      2) fallback to provided sqlite file path

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

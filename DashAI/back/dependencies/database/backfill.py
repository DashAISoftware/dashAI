import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

log = logging.getLogger(__name__)


def backfill_dataset_counts(session_factory: "sessionmaker") -> None:
    """Populate total_rows/total_columns for FINISHED datasets with NULL counts.

    Parameters
    ----------
    session_factory : sessionmaker
        SQLAlchemy session factory from the DI container.
    """
    from DashAI.back.core.enums.status import DatasetStatus
    from DashAI.back.dataloaders.classes.dashai_dataset import get_dataset_info
    from DashAI.back.dependencies.database.models import Dataset

    with session_factory() as db:
        pending = (
            db.query(Dataset)
            .filter(
                Dataset.status == DatasetStatus.FINISHED,
                Dataset.total_rows == None,  # noqa: E711 — SQLAlchemy ORM requires == for column IS NULL
            )
            .all()
        )
        updated = 0
        for ds in pending:
            try:
                info = get_dataset_info(f"{ds.file_path}/dataset")
                ds.total_rows = info["total_rows"]
                ds.total_columns = info["total_columns"]
                updated += 1
            except Exception as e:
                log.warning("Failed to backfill dataset %d: %s", ds.id, e)
        if updated:
            db.commit()
            log.debug("Backfilled counts for %d dataset(s).", updated)

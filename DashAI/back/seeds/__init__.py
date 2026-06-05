import json
import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from kink import di

from DashAI.back.dependencies.database.models import Dataset

logger = logging.getLogger(__name__)

_SEED_ZIP = Path(__file__).parent / "seed_datasets.zip"
_MANIFEST = Path(__file__).parent / "manifest.json"


def seed_datasets_if_first_run() -> None:
    """Copy pre-processed seed datasets into the local store on first run."""
    config = di["config"]
    session_factory = di["session_factory"]

    sentinel = Path(config["LOCAL_PATH"]) / ".seeded"
    if sentinel.exists():
        return

    if not _SEED_ZIP.exists():
        logger.warning(
            "Seed zip not found at %s - skipping seeding.", _SEED_ZIP
        )
        return

    if not _MANIFEST.exists():
        logger.error(
            "manifest.json not found at %s - aborting seeding.", _MANIFEST
        )
        return

    with _MANIFEST.open() as f:
        manifest: dict = json.load(f)

    logger.info(
        "First run detected - seeding datasets from %s.", _SEED_ZIP
    )

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        with zipfile.ZipFile(_SEED_ZIP) as zf:
            zf.extractall(tmp_dir)

        datasets_path = Path(config["DATASETS_PATH"])
        for dataset_name, meta in manifest.items():
            dataset_dir = tmp_dir / dataset_name
            if not dataset_dir.is_dir():
                logger.warning(
                    "Folder '%s' not found in zip - skipping.", dataset_name
                )
                continue
            _seed_one(
                dataset_dir,
                dataset_name,
                meta.get("total_rows"),
                meta.get("total_columns"),
                datasets_path,
                session_factory,
            )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    sentinel.touch()
    logger.info("Dataset seeding complete.")


def _seed_one(
    src_dir: Path,
    dataset_name: str,
    total_rows: int,
    total_columns: int,
    datasets_path: Path,
    session_factory,
) -> None:
    """Copy a single pre-processed dataset folder and register it in the DB."""
    try:
        with session_factory() as db:
            if db.query(Dataset).filter(Dataset.name == dataset_name).first():
                logger.debug(
                    "Dataset '%s' already in DB - skipping.", dataset_name
                )
                return
    except Exception:
        logger.exception(
            "DB check failed for dataset '%s'.", dataset_name
        )
        return

    dest = datasets_path / dataset_name
    try:
        shutil.copytree(src_dir, dest)
    except FileExistsError:
        logger.debug(
            "Dataset folder '%s' already exists - skipping.", dataset_name
        )
        return
    except Exception:
        logger.exception("Failed to copy dataset '%s'.", dataset_name)
        return

    try:
        with session_factory() as db:
            entry = Dataset(
                name=dataset_name,
                file_path=os.path.realpath(dest),
                total_rows=total_rows,
                total_columns=total_columns,
            )
            entry.set_status_as_finished()
            db.add(entry)
            db.commit()
            logger.info("Seeded dataset '%s'.", dataset_name)
    except Exception:
        shutil.rmtree(dest, ignore_errors=True)
        logger.exception(
            "DB insert failed for dataset '%s'.", dataset_name
        )

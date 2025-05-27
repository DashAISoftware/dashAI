import gc
import json
import logging
import os
import shutil
from typing import Any, Dict

from kink import inject
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker

from DashAI.back.api.api_v1.schemas.datasets_params import DatasetParams
from DashAI.back.api.utils import parse_params
from DashAI.back.dataloaders.classes.dashai_dataset import save_dataset
from DashAI.back.dependencies.database.models import Dataset
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.job.base_job import BaseJob, JobError

log = logging.getLogger(__name__)


class DatasetJob(BaseJob):
    """
    Job for processing and uploading datasets using streaming data processing.

    Parameters
    ----------
    kwargs : Dict[str, Any]
        A dictionary containing the parameters for the job, including:
        - name: Name of the dataset
        - datatype_name: Name of the datatype
        - params: Parameters for the datatype
        - file_path: Path to the temporarily saved file
        - temp_dir: Directory containing the temporary file
        - filename: Name of the uploaded file
        - db: Database session
    """

    def set_status_as_delivered(self) -> None:
        """Set the job status as delivered in the database."""
        log.debug("DatasetJob marked as delivered")

    @inject
    async def run(
        self,
        component_registry: ComponentRegistry = lambda di: di["component_registry"],
        session_factory: sessionmaker = lambda di: di["session_factory"],
        config: Dict[str, Any] = lambda di: di["config"],
    ) -> None:
        log.debug("Starting dataset creation process.")

        try:
            params = self.kwargs.get("params", {})
            file_path = self.kwargs.get("file_path")
            temp_dir = self.kwargs.get("temp_dir")
            url = self.kwargs.get("url", "")

            parsed_params = parse_params(DatasetParams, json.dumps(params))
            dataloader = component_registry[parsed_params.dataloader]["class"]()
            folder_path = config["DATASETS_PATH"] / parsed_params.name

            try:
                log.debug("Trying to create a new dataset path: %s", folder_path)
                folder_path.mkdir(parents=True)
            except FileExistsError as e:
                log.exception(e)
                raise JobError(
                    f"A dataset with the name {parsed_params.name} already exists."
                ) from e

            try:
                log.debug("Storing dataset in %s", folder_path)
                new_dataset = dataloader.load_data(
                    filepath_or_buffer=str(file_path) if file_path is not None else url,
                    temp_path=str(temp_dir),
                    params=parsed_params.model_dump(),
                )
                gc.collect()
                dataset_save_path = folder_path / "dataset"
                log.debug("Saving dataset in %s", str(dataset_save_path))
                save_dataset(new_dataset, dataset_save_path)
            except Exception as e:
                log.exception(e)
                shutil.rmtree(folder_path, ignore_errors=True)
                raise JobError(f"Error loading dataset: {str(e)}") from e

            # Add dataset to database
            with session_factory() as db:
                log.debug("Storing dataset metadata in database.")
                try:
                    folder_path = os.path.realpath(folder_path)
                    new_dataset = Dataset(
                        name=parsed_params.name,
                        file_path=folder_path,
                    )
                    db.add(new_dataset)
                    db.commit()
                    db.refresh(new_dataset)

                except exc.SQLAlchemyError as e:
                    log.exception(e)
                    shutil.rmtree(folder_path, ignore_errors=True)
                    raise JobError("Internal database error") from e

            log.debug("Dataset creation successfully finished.")

        finally:
            gc.collect()
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception as e:
                    log.exception(f"Error cleaning up temporary directory: {e}")

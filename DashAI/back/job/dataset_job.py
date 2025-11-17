import gc
import json
import logging
import os
import shutil
import uuid
from pathlib import Path

from kink import inject
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker

from DashAI.back.api.api_v1.schemas.datasets_params import DatasetParams
from DashAI.back.api.utils import parse_params
from DashAI.back.dataloaders.classes.dashai_dataset import load_dataset, save_dataset
from DashAI.back.dependencies.database.models import Dataset, Notebook
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

    @inject
    def set_status_as_delivered(
        self, session_factory: sessionmaker = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the dataset as delivered."""
        dataset_id: int = self.kwargs["dataset_id"]
        with session_factory() as db:
            dataset: Dataset = db.get(Dataset, dataset_id)

            if dataset is None:
                raise JobError(f"Dataset with id {dataset_id} not found.")

            try:
                dataset.set_status_as_delivered()
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise JobError(
                    "Error while setting the status of the dataset as delivered."
                ) from e

    @inject
    def set_status_as_error(
        self, session_factory: sessionmaker = lambda di: di["session_factory"]
    ) -> None:
        """Set the job status as error."""
        dataset_id: int = self.kwargs["dataset_id"]
        with session_factory() as db:
            dataset: Dataset = db.get(Dataset, dataset_id)

            if dataset is None:
                raise JobError(f"Dataset with id {dataset_id} not found.")

            try:
                dataset.set_status_as_error()
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise JobError(
                    "Error while setting the status of the dataset as error."
                ) from e

    def get_job_name(self) -> str:
        """Get a descriptive name for the job."""
        name = self.kwargs.get("name", "")
        if name:
            return f"Dataset: {name}"

        params = self.kwargs.get("params", {})
        if params and isinstance(params, dict) and "name" in params:
            return f"Dataset: {params['name']}"
        return "Dataset load"

    @inject
    def run(
        self,
    ) -> None:
        from kink import di

        component_registry = di["component_registry"]
        session_factory = di["session_factory"]
        config = di["config"]

        dataset_id = self.kwargs.get("dataset_id")
        notebook_id = self.kwargs.get("notebook_id", None)
        params = self.kwargs.get("params", {})
        n_sample = self.kwargs.get("n_sample", None)
        file_path = self.kwargs.get("file_path")
        temp_dir = self.kwargs.get("temp_dir")
        url = self.kwargs.get("url", "")

        try:
            with session_factory() as db:
                dataset = db.get(Dataset, dataset_id)
                if not dataset:
                    raise JobError(f"Dataset with ID {dataset_id} not found.")

                dataset.set_status_as_started()
                db.commit()
                db.refresh(dataset)

            if n_sample and dataset.file_path != "":
                folder_path = Path(dataset.file_path)
            else:
                random_name = str(uuid.uuid4())
                folder_path: Path = config["DATASETS_PATH"] / random_name

                try:
                    log.debug("Trying to create a new dataset path: %s", folder_path)
                    folder_path.mkdir(parents=True)
                except FileExistsError as e:
                    log.exception(e)
                    raise JobError(
                        f"A dataset with the name {random_name} already exists."
                    ) from e

            try:
                if notebook_id is not None:
                    log.debug(f"Copying dataset from notebook id {notebook_id}.")
                    with session_factory() as db:
                        notebook_dataset = (
                            db.query(Notebook)
                            .filter(Notebook.id == notebook_id)
                            .first()
                        )
                        if not notebook_dataset:
                            msg = (
                                "Notebook with ID "
                                f"{notebook_id}"
                                " has no associated dataset."
                            )
                            raise JobError(msg)
                        new_dataset = load_dataset(
                            os.path.join(notebook_dataset.file_path, "dataset")
                        )

                else:
                    parsed_params = parse_params(DatasetParams, json.dumps(params))
                    dataloader = component_registry[parsed_params.dataloader]["class"]()
                    log.debug("Storing dataset in %s", folder_path)
                    new_dataset = dataloader.load_data(
                        filepath_or_buffer=(
                            str(file_path) if file_path is not None else url
                        ),
                        temp_path=str(temp_dir),
                        params=parsed_params.model_dump(),
                        n_sample=n_sample,
                    )

                # Calculate metadata
                new_dataset.compute_metadata()
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
                    dataset = db.get(Dataset, dataset_id)
                    dataset.file_path = folder_path
                    dataset.set_status_as_finished()
                    db.commit()
                    db.refresh(dataset)

                except exc.SQLAlchemyError as e:
                    log.exception(e)
                    shutil.rmtree(folder_path, ignore_errors=True)
                    raise JobError("Internal database error") from e

            log.debug("Dataset creation successfully finished.")

        except JobError as e:
            log.error(f"Dataset creation failed: {e}")
            with session_factory() as db:
                dataset = db.get(Dataset, dataset_id)
                if dataset:
                    dataset.set_status_as_error()
                    db.commit()
                    db.refresh(dataset)
            raise e

        finally:
            gc.collect()
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception as e:
                    log.exception(f"Error cleaning up temporary directory: {e}")

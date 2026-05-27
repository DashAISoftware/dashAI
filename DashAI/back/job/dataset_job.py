import logging
from typing import TYPE_CHECKING

from kink import di, inject
from sqlalchemy import exc

from DashAI.back.api.api_v1.schemas.datasets_params import DatasetParams
from DashAI.back.api.utils import parse_params
from DashAI.back.dependencies.database.models import Dataset, Notebook
from DashAI.back.job.base_job import BaseJob, JobError

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker


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
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
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
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
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
        import gc
        import json
        import os
        import shutil
        import uuid
        from pathlib import Path

        from DashAI.back.dataloaders.classes.dashai_dataset import (
            load_dataset,
            save_dataset,
            transform_dataset_with_schema,
        )
        from DashAI.back.types.inf.type_inference import infer_types

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
                    source_name = self.kwargs.get("source_name")

                    if source_name:
                        # --- Hub import path ---
                        from DashAI.back.core.enums.status import DatafileStatus
                        from DashAI.back.dependencies.database.models import (
                            Datafile,
                        )

                        datafile_id = params.get("datafile_id")
                        selected_file = params.get("selected_file")

                        if datafile_id is None:
                            raise JobError("datafile_id is required for hub imports.")

                        with session_factory() as db:
                            hub_row = db.get(Datafile, datafile_id)
                        if hub_row is None or hub_row.status != DatafileStatus.READY:
                            raise JobError(f"Datafile {datafile_id} is not ready.")
                        hub_work_dir = hub_row.local_path
                        if selected_file:
                            file_path_hub = str(Path(hub_work_dir) / selected_file)
                        else:
                            files = sorted(
                                str(p)
                                for p in Path(hub_work_dir).rglob("*")
                                if p.is_file()
                                and not any(part.startswith(".") for part in p.parts)
                            )
                            if not files:
                                raise JobError("Hub download directory is empty.")
                            file_path_hub = files[0]

                        selected_dataloader = params.get("dataloader", "")
                        _reg = component_registry._registry
                        dl_registry = _reg.get("DataLoader", {})
                        if selected_dataloader not in dl_registry:
                            raise JobError(
                                f"DataLoader '{selected_dataloader}'"
                                " not found in registry."
                            )
                        dataloader = dl_registry[selected_dataloader]["class"]()
                        log.debug(
                            "Loading hub dataset from %s using %s",
                            file_path_hub,
                            selected_dataloader,
                        )
                        hub_loader_params = params.get("dataloader_params", {})
                        new_dataset = dataloader.load_data(
                            filepath_or_buffer=file_path_hub,
                            temp_path=hub_work_dir,
                            params=hub_loader_params,
                            n_sample=None,
                        )
                    else:
                        # --- File / URL upload path (unchanged) ---
                        parsed_params = parse_params(DatasetParams, json.dumps(params))
                        dataloader = component_registry[parsed_params.dataloader][
                            "class"
                        ]()
                        log.debug("Storing dataset in %s", folder_path)
                        new_dataset = dataloader.load_data(
                            filepath_or_buffer=(
                                str(file_path) if file_path is not None else url
                            ),
                            temp_path=str(temp_dir),
                            params=parsed_params.model_dump(),
                            n_sample=n_sample,
                        )

                    if params.get("inferred_types"):
                        schema = params["inferred_types"]
                    elif new_dataset.types:
                        schema = {
                            col: typ.to_string()
                            for col, typ in new_dataset.types.items()
                        }
                    else:
                        schema = infer_types(
                            new_dataset.to_pandas(), method="DashAIPtype"
                        )
                    if "column_renames" in params:
                        renames = params["column_renames"]
                        original_names = new_dataset.arrow_table.schema.names
                        new_names = [renames.get(col, col) for col in original_names]

                        if len(new_names) != len(set(new_names)):
                            duplicate_names = set()
                            seen = set()
                            for name in new_names:
                                if name in seen:
                                    duplicate_names.add(name)
                                else:
                                    seen.add(name)
                            msg = (
                                "Invalid column_renames: resulting column names "
                                "contain duplicates: "
                                f"{sorted(duplicate_names)}"
                            )
                            raise JobError(msg)

                        arrow_table = new_dataset.arrow_table.rename_columns(new_names)
                        new_dataset = new_dataset.__class__(
                            arrow_table,
                            splits=new_dataset.splits,
                            types=new_dataset.types,
                        )
                        schema = {renames.get(col, col): schema[col] for col in schema}

                    new_dataset = transform_dataset_with_schema(new_dataset, schema)

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
                    dataset.total_rows = new_dataset.splits.get("total_rows")
                    dataset.total_columns = len(
                        new_dataset.splits.get("column_names", [])
                    )
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

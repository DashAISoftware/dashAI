import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from kink import di, inject
from sqlalchemy.orm import sessionmaker

from DashAI.back.api.api_v1.schemas.predict_params import (
    FilterDatasetParams,
    RenameRequest,
)
from DashAI.back.dataloaders.classes.dashai_dataset import get_columns_spec
from DashAI.back.dependencies.database.models import Dataset, Experiment, Run

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/metadata_json/")
@inject
async def get_metadata_prediction_json(
    config: dict = Depends(lambda: di["config"]), path: Path = Path("")
):
    """
    Fetches prediction metadata from JSON files.

    Parameters
    ----------
    config : dict
        Configuration dictionary injected automatically.

    Returns
    -------
    List[dict]
        A list of metadata dictionaries from prediction JSON files.

    Raises
    ------
    HTTPException
        If the directory or files cannot be accessed.
    """
    if path == Path(""):
        path = Path(f"{config['DATASETS_PATH']}/predictions/")
    try:
        path.mkdir(parents=True, exist_ok=True)
        files = os.listdir(path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    json_files = [f for f in files if f.endswith(".json")]
    if not json_files:
        return []

    prediction_data = []
    # Read and collect metadata from each JSON file
    for json_file in json_files:
        file_path = path / json_file
        with open(file_path, "r") as f:
            data = json.load(f)["metadata"]
            prediction_data.append(data)
    return prediction_data


@router.get("/prediction_table")
@inject
async def get_prediction_table(
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """
    Fetches a table of prediction metadata from the database.

    Parameters
    ----------
    session_factory : sessionmaker
        SQLAlchemy session factory injected automatically.

    Returns
    -------
    List[dict]
        A list of dictionaries containing prediction metadata.

    Raises
    ------
    HTTPException
        If no data is found.
    """

    with session_factory() as db:
        query_results = db.query(
            Experiment.task_name,
            Run.model_name.label("run_type"),
            Dataset.name.label("dataset_name"),
            Dataset.id.label("dataset_id"),
            Run.name.label("model_name"),
            Dataset.last_modified,
        ).all()

        if not query_results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data found",
            )

        prediction_data = [
            {
                "id": result.dataset_id,
                "last_modified": result.last_modified,
                "run_name": result.run_type,
                "model_name": result.model_name,
                "dataset_name": result.dataset_name,
                "task_name": result.task_name,
            }
            for result in query_results
        ]
        return prediction_data


@router.get("/model_table")
@inject
async def get_model_table(
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """
    Fetches a table of model metadata from the database.

    Parameters
    ----------
    session_factory : sessionmaker
        SQLAlchemy session factory injected automatically.

    Returns
    -------
    List[dict]
        A list of dictionaries containing model metadata.

    Raises
    ------
    HTTPException
        If no data is found.
    """
    with session_factory() as db:
        query_results = (
            db.query(
                Run.id.label("run_id"),
                Experiment.name.label("experiment_name"),
                Experiment.created,
                Experiment.task_name,
                Run.name.label("run_name"),
                Run.model_name,
                Dataset.name.label("dataset_name"),
                Dataset.id.label("dataset_id"),
            )
            .join(Experiment, Experiment.id == Run.experiment_id)
            .join(Dataset, Experiment.dataset_id == Dataset.id)
            .all()
        )
        if not query_results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data found",
            )

        prediction_data = [
            {
                "id": result.run_id,
                "experiment_name": result.experiment_name,
                "created": result.created,
                "run_name": result.run_name,
                "task_name": result.task_name,
                "model_name": result.model_name,
                "dataset_name": result.dataset_name,
                "dataset_id": result.dataset_id,
            }
            for result in query_results
        ]
        return prediction_data


@router.get("/predict_summary")
@inject
async def get_predict_summary(
    pred_name: str, config: dict = Depends(lambda: di["config"])
):
    path = Path(f"{config['DATASETS_PATH']}/predictions/{pred_name}")
    summary = {}
    try:
        with open(path, "r") as f:
            try:
                data = json.load(f)["prediction"]
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=400, detail="Invalid JSON format"
                ) from e

            summary["total_data_points"] = len(data)

            # Verificar si los datos son strings
            if isinstance(data[0], str):
                summary["data_type"] = "string"
            else:
                summary["data_type"] = "numeric"
                class_set = set(data)
                classes = [str(item) for item in class_set]
                summary["Unique_classes"] = len(classes)
                class_distribution = []
                id = 1
                for class_name in classes:
                    try:
                        occurrences = data.count(int(class_name))
                    except ValueError as e:
                        raise HTTPException(
                            status_code=400, detail=f"Invalid class value: {class_name}"
                        ) from e
                    distribution = {
                        "id": id,
                        "Class": class_name,
                        "Ocurrences": occurrences,
                        "Percentage": round(occurrences / len(data) * 100, 2),
                    }
                    id += 1
                    class_distribution.append(distribution)
                summary["class_distribution"] = class_distribution

            sample_data = [
                {"id": idx, "value": value} for idx, value in enumerate(data[:50], 1)
            ]
            summary["sample_data"] = sample_data
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Prediction not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return summary


@router.post("/filter_datasets")
async def filter_datasets_endpoint(
    params: FilterDatasetParams,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """
    Filter datasets that match the column specifications of the train dataset.

    Parameters
    ----------
    train_dataset_id : int
        The ID of the train dataset.
    datasets : List[str]
        List of datasets paths to filter.

    Returns
    -------
    List[Dataset]
        List of datasets that match the column specifications of the train dataset.
    """
    try:
        with session_factory() as db:
            train_dataset_id = params.train_dataset_id
            datasets_paths = params.datasets
            filtered_list = []
            file_path = Path(db.get(Dataset, train_dataset_id).file_path, "dataset")
            if not file_path:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dataset not found",
                )
            train_dataset_spec = get_columns_spec(str(file_path))
            for dataset_path in datasets_paths:
                dataset_spec = get_columns_spec(str(Path(dataset_path, "dataset")))
                if train_dataset_spec == dataset_spec:
                    dataset = (
                        db.query(Dataset)
                        .filter(Dataset.file_path == dataset_path)
                        .first()
                    )
                    filtered_list.append(dataset)
            return filtered_list
    except Exception as e:
        logger.exception("Error filtering datasets: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while filtering datasets",
        ) from e


@router.get("/download/{predict_name}")
@inject
async def download_prediction(
    predict_name: str,
    config: dict = Depends(lambda: di["config"]),
):
    """
    Downloads a prediction file based on the provided predict_name.

    Parameters
    ----------
    predict_name : str
        The name of the prediction file to download.

    Raises
    ------
    HTTPException
        If the file cannot be found.
    """
    logger.debug("Downloading prediction file with name %s", predict_name)
    predict_path = os.path.join(config["DATASETS_PATH"], "predictions", predict_name)
    try:
        if os.path.exists(predict_path):
            with open(predict_path, "r") as json_file:
                data = json.load(json_file)
                return data["prediction"]
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )
    except Exception as e:
        logger.exception("Error downloading file %s: %s", predict_name, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while downloading the prediction file",
        ) from e


@router.delete("/{predict_name}")
@inject
async def delete_prediction(
    predict_name: str,
    config: dict = Depends(lambda: di["config"]),
):
    """
    Deletes a prediction file based on the provided predict_name.

    Parameters
    ----------
    predict_name : str
        The name of the prediction file to delete.

    Raises
    ------
    HTTPException
        If the file cannot be found or deleted.
    """
    logger.debug("Deleting prediction file with name %s", predict_name)
    predict_path = os.path.join(config["DATASETS_PATH"], "predictions", predict_name)
    try:
        if os.path.exists(predict_path):
            os.remove(predict_path)
            logger.debug("File %s deleted successfully", predict_path)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception("Error deleting file %s: %s", predict_name, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the prediction file",
        ) from e


@router.patch("/{predict_name}")
@inject
async def rename_prediction(
    predict_name: str,
    request: RenameRequest,
    config: dict = Depends(lambda: di["config"]),
):
    """
    Renames a prediction file based on the provided predict_name.

    Parameters
    ----------
    predict_name : str
        The current name of the prediction file.
    new_name : str
        The new name for the prediction file.

    Raises
    ------
    HTTPException
        If the file cannot be found or renamed.
    """
    new_name = f"{request.new_name}.json"
    logger.debug("Renaming prediction file from %s to %s", predict_name, new_name)
    predict_path = os.path.join(config["DATASETS_PATH"], "predictions", predict_name)
    new_path = os.path.join(config["DATASETS_PATH"], "predictions", new_name)

    try:
        if os.path.exists(predict_path):
            with open(predict_path, "r") as json_file:
                data = json.load(json_file)
            data["metadata"]["pred_name"] = new_name
            with open(predict_path, "w") as json_file:
                json.dump(data, json_file, indent=4)
            os.rename(predict_path, new_path)
            logger.debug(
                "File renamed from %s to %s successfully", predict_path, new_path
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(
            "Error renaming file %s to %s: %s", predict_name, new_name, str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while renaming the prediction file",
        ) from e

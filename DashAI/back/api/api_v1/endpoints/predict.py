import csv
import io
import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, Query, status
from fastapi.exceptions import HTTPException
from fastapi.responses import PlainTextResponse
from kink import di, inject
from sqlalchemy.orm import Session, sessionmaker

from DashAI.back.api.api_v1.schemas import prediction_params
from DashAI.back.dataloaders.classes.dashai_dataset import get_columns_spec
from DashAI.back.dependencies.database.models import (
    Dataset,
    Experiment,
    Prediction,
    Run,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/")
@inject
async def create_prediction(
    params: prediction_params.PredictionCreationParams,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """
    Creates a prediction for a given trained model/run.

    Parameters
    ----------
    run_id : int
        The ID of the trained model/run.

    Returns
    -------
    dict
        A dictionary containing the prediction result.

    Raises
    ------
    HTTPException
        If the run or experiment is not found.
    """
    db: Session
    with session_factory() as db:
        run: Run = db.get(Run, params.run_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
            )

        prediction = Prediction(
            run_id=run.id,
        )
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        return prediction


@router.get("/")
@inject
async def get_all_predictions(
    run_id: int = Query(None, description="The ID of the trained model/run"),
    prediction_id: int = Query(None, description="The ID of the prediction"),
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """
    Fetches all predictions, optionally filtered by run_id.

    Parameters
    ----------
    run_id : int, optional
        The ID of the trained model/run to filter predictions.
    session_factory : sessionmaker
        SQLAlchemy session factory injected automatically.

    Returns
    -------
    List[Prediction]
        A list of Prediction objects.
    """
    print("Fetching predictions with run_id:", run_id)

    db: Session
    with session_factory() as db:
        query = db.query(Prediction)
        if run_id is not None:
            query = query.filter(Prediction.run_id == run_id)
        if prediction_id is not None:
            query = query.filter(Prediction.id == prediction_id)

        predictions = query.all()
        return predictions


@router.get("/summary")
@inject
async def get_predict(
    prediction_id: int = Query(..., description="The ID of the prediction"),
    config: dict = Depends(lambda: di["config"]),
    component_registry: dict = Depends(lambda: di["component_registry"]),
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """
    Fetches prediction summary from JSON files.

    Parameters
    ----------
    prediction_id : int
        The ID of the prediction.

    Returns
    -------
    dict
        A dictionary containing the prediction summary.

    Raises
    ------
    HTTPException
        If the prediction file cannot be found or read.
    """

    # 1. Get prediction from DB
    with session_factory() as session:
        prediction: Prediction | None = session.get(Prediction, prediction_id)

        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")

        if not prediction.results_path:
            raise HTTPException(
                status_code=400, detail="Prediction exists but has no results_path"
            )

        path = Path(prediction.results_path)

    # 2. Read the JSON file
    try:
        with open(path, "r") as f:
            json_file = json.load(f)
            data = json_file.get("prediction", [])
            inputs = json_file.get("input", {})
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Results file not found") from e
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid JSON format") from e

    # 3. Build sample data (max 50 rows)
    max_samples = min(50, len(data))

    # Convert column-based input dict → row-based list
    # inputs = {"col1": [...], "col2": [...]} → [{"col1": x, "col2": y}, ...]
    input_rows = []
    if inputs:
        input_rows = [
            {key: values[i] for key, values in inputs.items()} for i in range(len(data))
        ]
    else:
        # No input data exists
        input_rows = [{} for _ in range(len(data))]

    sample_data = [
        {
            "id": i + 1,
            "value": data[i],
            "input": input_rows[i],
        }
        for i in range(max_samples)
    ]

    return {"sample_data": sample_data}


@router.get("/filter_datasets")
async def filter_datasets_endpoint(
    run_id: int = Query(..., description="The ID of the trained model/run"),
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """
    Filter datasets that match the column specifications of the train dataset.

    Parameters
    ----------
    run_id : int
        The ID of the trained model/run.

    Returns
    -------
    List[Dataset]
        List of datasets that match the column specifications of the train dataset.
    """
    try:
        with session_factory() as db:
            run: Run = db.get(Run, run_id)
            if not run:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
                )

            exp: Experiment = db.get(Experiment, run.experiment_id)
            if not exp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found"
                )
            input_columns = list(exp.input_columns)

            datasets = db.query(Dataset).all()
            datasets_filtered = []
            for dataset in datasets:
                dataset_path = Path(f"{dataset.file_path}/dataset/")
                if dataset_path.exists():
                    columns_spec = get_columns_spec(str(dataset_path))
                    if all(col in columns_spec for col in input_columns):
                        datasets_filtered.append(dataset)
                else:
                    logger.warning("Dataset path does not exist: %s", dataset_path)
            return datasets_filtered
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        logger.exception("Error filtering datasets: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while filtering datasets",
        ) from e


@router.get("/download/{prediction_id}")
@inject
async def download_prediction(
    prediction_id: str,
    config: dict = Depends(lambda: di["config"]),
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """
    Downloads a prediction file based on the provided predict_name.

    Parameters
    ----------
    prediction_id : str
        The ID of the prediction file to download.

    Raises
    ------
    HTTPException
        If the file cannot be found.
    """

    # Load prediction row from DB
    with session_factory() as db:
        prediction: Prediction | None = db.get(Prediction, int(prediction_id))

        if not prediction or not prediction.results_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prediction not found",
            )

        file_path = prediction.results_path

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction file not found",
        )

    # Read JSON content
    with open(file_path, "r") as f:
        data = json.load(f)

    input_data = data.get("input", {})
    predictions = data.get("prediction", [])

    # Extract input columns
    input_columns = list(input_data.keys())

    # Number of rows (same length for all values)
    row_count = len(predictions)

    # Prepare CSV buffer
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(input_columns + ["prediction"])

    # Write rows
    for i in range(row_count):
        row_inputs = [input_data[col][i] for col in input_columns]
        row_pred = predictions[i]
        writer.writerow(row_inputs + [row_pred])

    return PlainTextResponse(output.getvalue())


@router.delete("/{prediction_id}")
@inject
async def delete_prediction(
    prediction_id: str,
    config: dict = Depends(lambda: di["config"]),
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """
    Deletes a prediction file based on the provided predict_name.

    Parameters
    ----------
    prediction_id : str
        The ID of the prediction file to delete.

    Raises
    ------
    HTTPException
        If the file cannot be found or deleted.
    """
    logger.debug("Deleting prediction file with ID %s", prediction_id)

    with session_factory() as db:
        prediction: Prediction | None = db.get(Prediction, int(prediction_id))

        if not prediction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prediction not found",
            )

        predict_path = prediction.results_path
        db.delete(prediction)
        db.commit()

    try:
        if predict_path and os.path.exists(predict_path):
            os.remove(predict_path)
            logger.debug("File %s deleted successfully", predict_path)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception("Error deleting file %s: %s", predict_path, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the prediction file",
        ) from e

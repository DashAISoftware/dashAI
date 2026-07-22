import json
import logging
from typing import TYPE_CHECKING, Dict, List

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import HTTPException
from kink import di, inject

from DashAI.back.api.api_v1.schemas.prediction_params import PredictionCreationParams
from DashAI.back.dependencies.database.models import (
    Dataset,
    ModelSession,
    Prediction,
    Run,
)
from DashAI.back.job.predict_job import run_manual_prediction

if TYPE_CHECKING:
    from sqlalchemy.orm import Session, sessionmaker

    from DashAI.back.dependencies.registry.component_registry import ComponentRegistry

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


router = APIRouter()


@router.post("/")
@inject
async def create_prediction(
    params: PredictionCreationParams,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
):
    """
    Creates a prediction for a given trained model/run.

    Parameters
    ----------
    run_id : int
        The ID of the trained model/run.
    dataset_id : int | None
        The ID of the dataset to use for prediction (optional).
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary containing the prediction result.

    Raises
    ------
    HTTPException
        If the run or model session is not found.
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
            dataset_id=params.dataset_id,
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
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """
    Fetches all predictions, optionally filtered by run_id.

    Parameters
    ----------
    run_id : int, optional
        The ID of the trained model/run to filter predictions.
    prediction_id : int, optional
        The ID of the prediction to fetch.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

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

        datasets = (
            db.query(Dataset)
            .filter(Dataset.id.in_([p.dataset_id for p in predictions if p.dataset_id]))
            .all()
        )

        # Concatenate datasets to predictions
        dataset_dict = {dataset.id: dataset for dataset in datasets}
        for prediction in predictions:
            prediction.dataset = dataset_dict.get(prediction.dataset_id)

        return predictions


@router.get("/filter_datasets")
async def filter_datasets_endpoint(
    run_id: int = Query(..., description="The ID of the trained model/run"),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """
    Filter datasets that match the column specifications of the train dataset.

    Parameters
    ----------
    run_id : int
        The ID of the trained model/run.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    List[Dataset]
        List of datasets that match the column specifications of the train dataset.
    """
    from pathlib import Path

    from DashAI.back.dataloaders.classes.dashai_dataset import get_columns_spec

    try:
        with session_factory() as db:
            run: Run = db.get(Run, run_id)
            if not run:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
                )

            model_session: ModelSession = db.get(ModelSession, run.model_session_id)
            if not model_session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Model session not found",
                )
            input_columns = list(model_session.input_columns)

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


@router.delete("/{prediction_id}")
@inject
async def delete_prediction(
    prediction_id: str,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """
    Deletes a prediction file based on the provided predict_name.

    Parameters
    ----------
    prediction_id : str
        The ID of the prediction file to delete.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Raises
    ------
    HTTPException
        If the file cannot be found or deleted.
    """
    logger.debug("Deleting prediction file with ID %s", prediction_id)
    import os
    import shutil

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
            shutil.rmtree(predict_path)
            logger.debug("File %s deleted successfully", predict_path)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception("Error deleting file %s: %s", predict_path, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the prediction file",
        ) from e


@router.post("/preview")
@inject
async def preview_manual_prediction(
    request: Request,
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Run a synchronous manual prediction and return results without persisting.

    Parameters
    ----------
    run_id : int
        The ID of the trained model/run.
    manual_input_data : str
        JSON-encoded list of row dicts (one dict per input row, keyed by column name).

    Returns
    -------
    dict
        ``{"columns": [...], "rows": [[...], ...]}``
    """
    import re

    from starlette.datastructures import UploadFile

    form = await request.form()

    run_id = form.get("run_id")
    manual_input_data = form.get("manual_input_data")
    if run_id is None or manual_input_data is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing run_id or manual_input_data",
        )

    try:
        run_id_int = int(run_id)
    except (TypeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid run_id: {run_id}",
        ) from e

    try:
        rows_data: List[Dict] = json.loads(manual_input_data)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid manual_input_data JSON: {e}",
        ) from e

    if not isinstance(rows_data, list) or not rows_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "manual_input_data must be a non-empty JSON array "
                "of objects (list[dict])."
            ),
        )

    if not all(isinstance(item, dict) for item in rows_data):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Each item in manual_input_data must be a JSON object (dict).",
        )

    file_key_regex = re.compile(r"^file_(\d+)_(.+)$")
    for field_name, value in form.multi_items():
        if not isinstance(value, UploadFile):
            continue

        match = file_key_regex.match(field_name)
        if not match:
            continue

        row_index = int(match.group(1))
        column_name = match.group(2)
        if row_index < 0 or row_index >= len(rows_data):
            continue

        if rows_data[row_index].get(column_name) == field_name:
            rows_data[row_index][column_name] = value

    columns, rows = await run_in_threadpool(
        run_manual_prediction,
        run_id=run_id_int,
        manual_input_data=rows_data,
        component_registry=component_registry,
        session_factory=session_factory,
    )
    return {"columns": columns, "rows": rows}

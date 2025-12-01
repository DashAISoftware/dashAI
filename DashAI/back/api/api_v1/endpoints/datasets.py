import io
import logging
import os
import shutil
from typing import Any, Dict

import pyarrow as pa
import pyarrow.csv as csv
import pyarrow.ipc as ipc
from fastapi import APIRouter, Depends, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from kink import di, inject
from sqlalchemy import exc, select
from sqlalchemy.orm.session import sessionmaker

from DashAI.back.api.api_v1.schemas import datasets_params as schemas
from DashAI.back.core.enums.status import DatasetStatus
from DashAI.back.dataloaders.classes.dashai_dataset import (
    get_columns_spec,
    get_dataset_info,
)
from DashAI.back.dependencies.database.models import Dataset, Experiment

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=schemas.Dataset, status_code=status.HTTP_201_CREATED)
@inject
async def create_dataset(
    params: schemas.DatasetCreateParams,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Create a new dataset entry in the database with NOT_STARTED status.

    Parameters
    ----------
    params : DatasetCreateParams
        A schema containing the dataset creation parameters.
    session_factory : sessionmaker
        A factory that creates a context manager that handles a SQLAlchemy session.

    Returns
    -------
    Dataset
        The newly created dataset with NOT_STARTED status.
    """
    logger.debug("Creating new dataset entry.")
    with session_factory() as db:
        try:
            dataset = Dataset(
                name=params.name,
                file_path="",
            )
            db.add(dataset)
            db.commit()
            db.refresh(dataset)
            return dataset

        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/")
@inject
async def get_datasets(
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Retrieve a list of the stored datasets in the database.

    Parameters
    ----------
    session_factory : sessionmaker
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    List[dict]
        A list of dictionaries representing the found datasets.
        Each dictionary contains information about the dataset, including its name,
        type, description, and creation date.
        If no datasets are found, an empty list will be returned.
    """
    logger.debug("Retrieving all datasets.")
    with session_factory() as db:
        try:
            datasets = db.query(Dataset).all()

        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

    return datasets


@router.get("/{dataset_id}")
@inject
async def get_dataset(
    dataset_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Retrieve the dataset associated with the provided ID.

    Parameters
    ----------
    dataset_id : int
        ID of the dataset to retrieve.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    Dict
        A Dict containing the requested dataset details.
    """
    logger.debug("Retrieving dataset with id %s", dataset_id)
    with session_factory() as db:
        try:
            dataset = db.get(Dataset, dataset_id)

            if not dataset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dataset not found",
                )

        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

    return dataset


@router.get("/{dataset_id}/sample")
@inject
async def get_sample(
    dataset_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Return a sample of 10 rows from the dataset with id dataset_id from the
    database.

    If a column is not JSON serializable, it will be converted to a list of
    strings.

    Parameters
    ----------
    dataset_id : int
        id of the dataset to query.

    Returns
    -------
    Dict
        A Dict with a sample of 10 rows
    """
    with session_factory() as db:
        try:
            dataset = db.get(Dataset, dataset_id)
            if not dataset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dataset not found",
                )
            if dataset.status != DatasetStatus.FINISHED:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Dataset is not in finished state",
                )
            file_path = dataset.file_path

            arrow_path = os.path.join(file_path, "dataset", "data.arrow")

            with pa.OSFile(arrow_path, "rb") as source:
                reader = ipc.open_file(source)
                batch = reader.get_batch(0)
                sample_size = min(10, batch.num_rows)
                sample_batch = batch.slice(0, sample_size)
                sample = sample_batch.to_pydict()

        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
        try:
            jsonable_encoder(sample)
        except ValueError:
            for key, value in sample.items():
                try:
                    jsonable_encoder({key: value})
                except ValueError:
                    value = list(map(str, value))
                sample[key] = value
    return sample


@router.get("/sample/file")
@inject
async def get_sample_by_file(
    path: str,
):
    """Return a sample of 10 rows from the dataset file

    If a column is not JSON serializable, it will be converted to a list of
    strings.

    Parameters
    ----------
    params : dict
        A dictionary containing the parameters for the request.

    Returns
    -------
    Dict
        A Dict with a sample of 10 rows
    """
    try:
        if not path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )

        arrow_path = os.path.join(path, "dataset", "data.arrow")

        with pa.OSFile(arrow_path, "rb") as source:
            reader = ipc.open_file(source)
            batch = reader.get_batch(0)
            sample_size = min(10, batch.num_rows)
            sample_batch = batch.slice(0, sample_size)
            sample = sample_batch.to_pydict()

    except exc.SQLAlchemyError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal database error",
        ) from e
    try:
        jsonable_encoder(sample)
    except ValueError:
        for key, value in sample.items():
            try:
                jsonable_encoder({key: value})
            except ValueError:
                value = list(map(str, value))
            sample[key] = value
    return sample


@router.get("/file/info")
@inject
async def get_info_by_file(
    path: str,
):
    """Return the dataset with id dataset_id from the database.

    Parameters
    ----------
    path : str
        The file path of the dataset.

    Returns
    -------
    JSON
        JSON with the specified dataset id.
    """
    try:
        info = get_dataset_info(f"{path}/dataset")
    except exc.SQLAlchemyError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error",
        ) from e
    return info


@router.get("/{dataset_id}/info")
@inject
async def get_info(
    dataset_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Return the dataset with id dataset_id from the database.

    Parameters
    ----------
    dataset_id : int
        id of the dataset to query.

    Returns
    -------
    JSON
        JSON with the specified dataset id.
    """
    with session_factory() as db:
        try:
            dataset = db.get(Dataset, dataset_id)
            if not dataset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dataset not found",
                )

            if dataset.status != DatasetStatus.FINISHED:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Dataset is not in finished state",
                )

            info = get_dataset_info(f"{dataset.file_path}/dataset")
        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
    return info


@router.get("/{dataset_id}/temporal-info")
@inject
async def get_temporal_info(
    dataset_id: int,
    timestamp_column: str,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get temporal information about a dataset for forecasting tasks.

    This endpoint analyzes a timestamp column to detect frequency, date range,
    and other temporal characteristics useful for time series forecasting.

    Parameters
    ----------
    dataset_id : int
        ID of the dataset to analyze.
    timestamp_column : str
        Name of the column containing timestamps.

    Returns
    -------
    dict
        Dictionary with temporal information including:
        - frequency_code: Short code (D, H, M, W, A, T)
        - frequency_label: Human-readable label
        - frequency_description: Detailed description
        - start_date: First timestamp in the series
        - end_date: Last timestamp in the series
        - total_periods: Number of data points
        - detected_gaps: Number of missing periods detected
    """
    import pandas as pd

    with session_factory() as db:
        try:
            dataset = db.get(Dataset, dataset_id)
            if not dataset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dataset not found",
                )

            if dataset.status != DatasetStatus.FINISHED:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Dataset is not in finished state",
                )

            # Load the dataset
            dataset_path = f"{dataset.file_path}/dataset"
            data_filepath = os.path.join(dataset_path, "data.arrow")

            with pa.OSFile(data_filepath, "rb") as source:
                reader = ipc.open_file(source)
                table = reader.read_all()

            data_frame = table.to_pandas()

            if timestamp_column not in data_frame.columns:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Column '{timestamp_column}' not found in dataset",
                )

            # Convert to datetime
            try:
                timestamps = pd.to_datetime(data_frame[timestamp_column])
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot parse '{timestamp_column}' as datetime: {str(e)}",
                ) from e

            # Sort and analyze
            sorted_ts = timestamps.sort_values()
            diffs = sorted_ts.diff().dropna()

            if len(diffs) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Not enough data points to detect frequency",
                )

            # Get most common difference (mode)
            mode_diff = (
                diffs.mode().iloc[0] if len(diffs.mode()) > 0 else diffs.median()
            )

            # Frequency mapping with detailed info
            frequency_map = {
                "T": {
                    "code": "T",
                    "label": "Minutely",
                    "description": "Each row represents one minute",
                    "example": "e.g., 10:00, 10:01, 10:02...",
                },
                "H": {
                    "code": "H",
                    "label": "Hourly",
                    "description": "Each row represents one hour",
                    "example": "e.g., 10:00, 11:00, 12:00...",
                },
                "D": {
                    "code": "D",
                    "label": "Daily",
                    "description": "Each row represents one day",
                    "example": "e.g., Jan 1, Jan 2, Jan 3...",
                },
                "W": {
                    "code": "W",
                    "label": "Weekly",
                    "description": "Each row represents one week",
                    "example": "e.g., Week 1, Week 2, Week 3...",
                },
                "M": {
                    "code": "M",
                    "label": "Monthly",
                    "description": "Each row represents one month",
                    "example": "e.g., Jan, Feb, Mar...",
                },
                "A": {
                    "code": "A",
                    "label": "Yearly",
                    "description": "Each row represents one year",
                    "example": "e.g., 2022, 2023, 2024...",
                },
            }

            # Detect frequency
            if mode_diff >= pd.Timedelta(days=365):
                freq_code = "A"
            elif mode_diff >= pd.Timedelta(days=28):
                freq_code = "M"
            elif mode_diff >= pd.Timedelta(days=7):
                freq_code = "W"
            elif mode_diff >= pd.Timedelta(days=1):
                freq_code = "D"
            elif mode_diff >= pd.Timedelta(hours=1):
                freq_code = "H"
            else:
                freq_code = "T"

            freq_info = frequency_map[freq_code]

            # Calculate average difference in human-readable format
            avg_diff = diffs.mean()
            if avg_diff >= pd.Timedelta(days=1):
                avg_diff_str = f"{avg_diff.days} days"
            elif avg_diff >= pd.Timedelta(hours=1):
                avg_diff_str = f"{avg_diff.seconds // 3600} hours"
            else:
                avg_diff_str = f"{avg_diff.seconds // 60} minutes"

            # Detect gaps (periods where diff is significantly larger than mode)
            gap_threshold = mode_diff * 1.5
            gaps = (diffs > gap_threshold).sum()

            return {
                "frequency_code": freq_info["code"],
                "frequency_label": freq_info["label"],
                "frequency_description": freq_info["description"],
                "frequency_example": freq_info["example"],
                "average_interval": avg_diff_str,
                "start_date": sorted_ts.min().isoformat(),
                "end_date": sorted_ts.max().isoformat(),
                "total_periods": len(data_frame),
                "detected_gaps": int(gaps),
                "timestamp_column": timestamp_column,
            }

        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/{dataset_id}/experiments-exist")
@inject
async def get_experiments_exist(
    dataset_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get a boolean indicating if there are experiments associated with the dataset.

    Parameters
    ----------
    dataset_id : int
        id of the dataset to query.

    Returns
    -------
    bool
        True if there are experiments associated with the dataset, False otherwise.
    """
    with session_factory() as db:
        try:
            dataset = db.get(Dataset, dataset_id)
            if not dataset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dataset not found",
                )

            if dataset.status != DatasetStatus.FINISHED:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Dataset is not in finished state",
                )

            # Check if there are any experiments associated with the dataset
            experiments_exist = (
                db.query(Experiment).filter(Experiment.dataset_id == dataset_id).first()
                is not None
            )

            return experiments_exist

        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/{dataset_id}/types")
@inject
async def get_types(
    dataset_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Return the dataset with id dataset_id from the database.

    Parameters
    ----------
    dataset_id : int
        id of the dataset to query.

    Returns
    -------
    Dict
        Dict containing column names and types.
    """
    with session_factory() as db:
        try:
            dataset = db.get(Dataset, dataset_id)
            if not dataset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dataset not found",
                )
            if dataset.status != DatasetStatus.FINISHED:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Dataset is not in finished state",
                )
            columns_spec = get_columns_spec(f"{dataset.file_path}/dataset")
            if not columns_spec:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Error while loading column types.",
                )
        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
    return columns_spec


@router.get("/types/file")
@inject
async def get_types_by_file_path(
    path: str,
):
    """Return the dataset with the specified file path.

    Parameters
    ----------
    path : str
        Path to the dataset file.

    Returns
    -------
    Dict
        Dict containing column names and types.
    """
    try:
        if not path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )
        columns_spec = get_columns_spec(f"{path}/dataset")
        if not columns_spec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Error while loading column types.",
            )
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error",
        ) from e
    return columns_spec


@router.post("/copy", status_code=status.HTTP_201_CREATED)
@inject
async def copy_dataset(
    dataset: Dict[str, int],
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    config: Dict[str, Any] = Depends(lambda: di["config"]),
):
    """Copy an existing dataset to create a new one.

    Parameters
    ----------
    dataset_id : int
        ID of the dataset to copy.

    Returns
    -------
    Dataset
        The newly created dataset.
    """
    dataset_id = dataset["dataset_id"]
    logger.debug(f"Copying dataset with ID {dataset_id}.")

    with session_factory() as db:
        # Retrieve the existing dataset
        original_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not original_dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original dataset not found.",
            )
        if original_dataset.status != DatasetStatus.FINISHED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Original dataset is not in finished state",
            )

        # Create a new folder for the copied dataset
        new_name = f"{original_dataset.name}_copy"
        new_folder_path = config["DATASETS_PATH"] / new_name
        try:
            shutil.copytree(original_dataset.file_path, new_folder_path)
        except FileExistsError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A dataset with the name '{new_name}' already exists.",
            ) from None
        except Exception as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to copy dataset files.",
            ) from e

        # Save metadata for the new dataset
        try:
            new_dataset = Dataset(
                name=new_name,
                file_path=str(new_folder_path),
            )
            db.add(new_dataset)
            db.commit()
            db.refresh(new_dataset)
        except exc.SQLAlchemyError as e:
            logger.exception(e)
            shutil.rmtree(new_folder_path, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error.",
            ) from e

    logger.debug(f"Dataset copied successfully to '{new_name}'.")
    return new_dataset


@router.delete("/{dataset_id}")
@inject
async def delete_dataset(
    dataset_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Delete the dataset associated with the provided ID from the database.

    Parameters
    ----------
    dataset_id : int
        ID of the dataset to be deleted.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    Response with code 204 NO_CONTENT
    """
    logger.debug("Deleting dataset with id %s", dataset_id)
    with session_factory() as db:
        try:
            dataset = db.get(Dataset, dataset_id)
            if not dataset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dataset not found",
                )

            db.delete(dataset)
            db.commit()

        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

    try:
        shutil.rmtree(dataset.file_path, ignore_errors=True)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except OSError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete directory",
        ) from e


@router.patch("/{dataset_id}")
@inject
async def update_dataset(
    dataset_id: int,
    params: schemas.DatasetUpdateParams,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    config: Dict[str, Any] = Depends(lambda: di["config"]),
):
    """Updates the name of a dataset with the provided ID.

    Parameters
    ----------
    dataset_id : int
        ID of the dataset to update.
    params : DatasetUpdateParams
        A dictionary containing the new values for the dataset.
        name : str
            New name for the dataset.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    Dict
        A dictionary containing the updated dataset record.
    """
    with session_factory() as db:
        dataset = db.get(Dataset, dataset_id)
        if dataset is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found"
            )

        if not params.name or not params.name.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Name cannot be empty",
            )

        new_name = params.name.strip()

        if new_name == dataset.name:
            return dataset

        exists = db.execute(
            select(Dataset.id).where(Dataset.name == new_name, Dataset.id != dataset_id)
        ).scalar()
        if exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Dataset name already exists",
            )

        dataset.name = new_name
        try:
            db.commit()
            db.refresh(dataset)
            return dataset
        except exc.IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Dataset name already exists",
            ) from e
        except exc.SQLAlchemyError as e:
            db.rollback()
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/file/")
async def get_dataset_file(
    path: str,
    page: int = 0,
    page_size: int = 10,
):
    """Fetch the dataset file associated with the provided file path.

    Parameters
    ----------
    path : str
        The folder path of the dataset to retrieve.
    page: int
        The page number to retrieve.
    page_size: int
        The number of items per page.

    Returns
    -------
    JSONResponse
        A JSON response containing the dataset rows and total row count.
    """

    arrow_file_path = f"{path}/dataset/data.arrow"
    rows = []

    start = page * page_size
    end = start + page_size
    rows_collected = 0

    with pa.memory_map(arrow_file_path, "r") as source:
        reader = ipc.RecordBatchFileReader(source)

        current_index = 0
        for i in range(reader.num_record_batches):
            batch = reader.get_batch(i)
            batch_start = current_index
            batch_end = current_index + batch.num_rows
            current_index = batch_end

            # Skip batches before the page start
            if batch_end <= start:
                continue
            if batch_start >= end:
                break  # already got all needed rows

            slice_start = max(0, start - batch_start)
            slice_end = min(batch.num_rows, end - batch_start)
            sliced_batch = batch.slice(slice_start, slice_end - slice_start)

            for j in range(sliced_batch.num_rows):
                row = {
                    col: sliced_batch[col][j].as_py()
                    for col in sliced_batch.schema.names
                }
                # Use jsonable_encoder to handle Timestamp and other
                # non-JSON-serializable types
                row = jsonable_encoder(row)
                rows.append(row)
                rows_collected += 1
                if rows_collected >= page_size:
                    break

            if rows_collected >= page_size:
                break

    total_rows = get_dataset_info(f"{path}/dataset")["total_rows"]

    return JSONResponse(content={"rows": rows, "total": total_rows})


@router.get("/export/csv")
async def export_dataset_as_csv(
    path: str,
):
    """Export the complete dataset as CSV file.

    Parameters
    ----------
    path : str
        The folder path of the dataset to export.

    Returns
    -------
    StreamingResponse
        A streaming response with the complete dataset in CSV format.
    """
    try:
        arrow_file_path = f"{path}/dataset/data.arrow"

        if not os.path.exists(arrow_file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset file not found",
            )

        # Read the complete Arrow file
        with pa.memory_map(arrow_file_path, "r") as source:
            reader = ipc.RecordBatchFileReader(source)

            # Read all batches and combine them into a single table
            batches = []
            for i in range(reader.num_record_batches):
                batch = reader.get_batch(i)
                batches.append(batch)

            if not batches:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No data found in dataset",
                )

            table = pa.Table.from_batches(batches)

            # Convert to CSV
            output = io.BytesIO()
            csv.write_csv(table, output)
            output.seek(0)

            # Get dataset name from path for filename
            dataset_name = os.path.basename(path.rstrip("/"))
            filename = f"{dataset_name}.csv"

            return StreamingResponse(
                io.BytesIO(output.getvalue()),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset file not found",
        ) from e
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error exporting dataset to CSV",
        ) from e


@router.get("/{dataset_id}/export/csv")
@inject
async def export_dataset_csv_by_id(
    dataset_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Export the entire dataset as a CSV file by dataset ID.

    Parameters
    ----------
    dataset_id : int
        ID of the dataset to export.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    StreamingResponse
        A streaming response that provides the CSV file content.
    """
    logger.debug("Exporting dataset with id %s to CSV", dataset_id)
    with session_factory() as db:
        try:
            dataset = db.get(Dataset, dataset_id)

            if not dataset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dataset not found",
                )
            if dataset.status != DatasetStatus.FINISHED:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Dataset is not in finished state",
                )

            file_path = dataset.file_path
            arrow_file_path = f"{file_path}/dataset/data.arrow"

            if not os.path.exists(arrow_file_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dataset file not found",
                )

            # Read the complete Arrow file
            with pa.memory_map(arrow_file_path, "r") as source:
                reader = ipc.RecordBatchFileReader(source)

                # Read all batches and combine them into a single table
                batches = []
                for i in range(reader.num_record_batches):
                    batch = reader.get_batch(i)
                    batches.append(batch)

                if not batches:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="No data found in dataset",
                    )

                table = pa.Table.from_batches(batches)

                # Convert to CSV
                output = io.BytesIO()
                csv.write_csv(table, output)
                output.seek(0)

                # Use dataset name for filename
                filename = f"{dataset.name}.csv"

                return StreamingResponse(
                    io.BytesIO(output.getvalue()),
                    media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"},
                )

        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
        except Exception as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error exporting dataset as CSV",
            ) from e

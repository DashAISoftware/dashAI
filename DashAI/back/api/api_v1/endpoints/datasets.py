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
from sqlalchemy import exc
from sqlalchemy.orm.session import sessionmaker

from DashAI.back.api.api_v1.schemas.datasets_params import DatasetUpdateParams
from DashAI.back.dataloaders.classes.dashai_dataset import (
    get_columns_spec,
    get_dataset_info,
    update_columns_spec,
)
from DashAI.back.dependencies.database.models import Dataset, Experiment

logger = logging.getLogger(__name__)
router = APIRouter()


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
            file_path = db.get(Dataset, dataset_id).file_path
            if not file_path:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dataset not found",
                )

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
            info = get_dataset_info(f"{dataset.file_path}/dataset")
        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
    return info


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
            file_path = db.get(Dataset, dataset_id).file_path
            if not file_path:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dataset not found",
                )
            columns_spec = get_columns_spec(f"{file_path}/dataset")
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
    params: DatasetUpdateParams,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    config: Dict[str, Any] = Depends(lambda: di["config"]),
):
    """Updates the name and/or task name of a dataset with the provided ID.

    Parameters
    ----------
    dataset_id : int
        ID of the dataset to update.
    params : DatasetUpdateParams
        A dictionary containing the new values for the dataset.
        name : str, optional
            New name for the dataset.
        task_name : str, optional
            New task name for the dataset.
        columns : Dict[str, ColumnSpecItemParams], optional
            New column specification for the dataset.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    Dict
        A dictionary containing the updated dataset record.
    """
    with session_factory() as db:
        try:
            dataset = db.get(Dataset, dataset_id)
            if params.columns:
                update_columns_spec(f"{dataset.file_path}/dataset", params.columns)
            elif params.name:
                setattr(dataset, "name", params.name)
                new_folder_path = config["DATASETS_PATH"] / params.name
                os.rename(dataset.file_path, new_folder_path)
                db.commit()
                db.refresh(dataset)
                return dataset
            else:
                raise HTTPException(
                    status_code=status.HTTP_304_NOT_MODIFIED,
                    detail="Record not modified",
                )
        except exc.SQLAlchemyError as e:
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

import io
import json
import logging
import os
import shutil
from typing import Any, Dict

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as csv
import pyarrow.ipc as ipc
from fastapi import APIRouter, Depends, Query, Response, status
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


# Server-side filtering and pagination
@router.get("/filter/")
async def filter_dataset_file(
    path: str,
    page: int = 0,
    page_size: int = 10,
    filter_model: str = Query(None, alias="filterModel"),
):
    """
    Fetch filtered and paginated dataset rows based on the provided
    filterModel from the frontend.
    """
    arrow_file_path = f"{path}/dataset/data.arrow"
    rows = []
    table = None
    with pa.memory_map(arrow_file_path, "r") as source:
        reader = ipc.RecordBatchFileReader(source)
        batches = [reader.get_batch(i) for i in range(reader.num_record_batches)]
        table = pa.Table.from_batches(batches)

    # Parse filter_model if present
    filter_dict = None
    if filter_model:
        logger.info(f"[FILTER DEBUG] filter_model param: {filter_model}")
        try:
            filter_dict = json.loads(filter_model)
            logger.info(f"[FILTER DEBUG] filter_dict parsed: {filter_dict}")
        except Exception as e:
            logger.error(f"[FILTER DEBUG] Error parsing filter_model: {e}")
            filter_dict = None

    # Apply filters if filter_model and items are provided
    if filter_dict and "items" in filter_dict:
        for item in filter_dict["items"]:
            col = item.get("field") or item.get("columnField")
            op = item.get("operator") or item.get("operatorValue")
            val = item.get("value")
            if col and op:
                col_type = table[col].type

                def cast_value(v, col_type=col_type):
                    if pa.types.is_integer(col_type):
                        try:
                            return int(v)
                        except Exception:
                            return v
                    elif pa.types.is_floating(col_type):
                        try:
                            return float(v)
                        except Exception:
                            return v
                    elif pa.types.is_boolean(col_type):
                        if isinstance(v, bool):
                            return v
                        if str(v).lower() in ["true", "1"]:
                            return True
                        if str(v).lower() in ["false", "0"]:
                            return False
                        return v
                    return v

                if op == "contains" and val is not None:
                    # Case-insensitive contains
                    if not pa.types.is_string(col_type):
                        as_str = pc.utf8_lower(pc.cast(table[col], pa.string()))
                    else:
                        as_str = pc.utf8_lower(table[col])
                    mask = pc.match_substring(as_str, str(val).lower())
                    table = table.filter(mask)
                elif op == "doesNotContain" and val is not None:
                    # Case-insensitive doesNotContain
                    if not pa.types.is_string(col_type):
                        as_str = pc.utf8_lower(pc.cast(table[col], pa.string()))
                    else:
                        as_str = pc.utf8_lower(table[col])
                    mask = pc.invert(pc.match_substring(as_str, str(val).lower()))
                    table = table.filter(mask)
                elif op == "startsWith" and val is not None:
                    # Case-insensitive startsWith
                    if not pa.types.is_string(col_type):
                        as_str = pc.utf8_lower(pc.cast(table[col], pa.string()))
                    else:
                        as_str = pc.utf8_lower(table[col])
                    mask = pc.match_substring_regex(as_str, f"^{str(val).lower()}")
                    table = table.filter(mask)
                elif op == "endsWith" and val is not None:
                    # Case-insensitive endsWith
                    if not pa.types.is_string(col_type):
                        as_str = pc.utf8_lower(pc.cast(table[col], pa.string()))
                    else:
                        as_str = pc.utf8_lower(table[col])
                    mask = pc.match_substring_regex(as_str, f"{str(val).lower()}$")
                    table = table.filter(mask)
                    table = table.filter(mask)
                elif op == "endsWith" and val is not None:
                    if not pa.types.is_string(col_type):
                        as_str = pc.cast(table[col], pa.string())
                        mask = pc.match_substring_regex(as_str, f"{val}$")
                    else:
                        mask = pc.match_substring_regex(table[col], f"{val}$")
                    table = table.filter(mask)
                elif op == "isEmpty":
                    if pa.types.is_string(col_type):
                        mask = pc.or_(pc.equal(table[col], ""), pc.is_null(table[col]))
                    else:
                        mask = pc.is_null(table[col])
                    table = table.filter(mask)
                elif op == "isNotEmpty":
                    if pa.types.is_string(col_type):
                        mask = pc.and_(
                            pc.invert(pc.equal(table[col], "")),
                            pc.invert(pc.is_null(table[col])),
                        )
                    else:
                        mask = pc.invert(pc.is_null(table[col]))
                    table = table.filter(mask)
                elif op == "isAnyOf" and val is not None:
                    values = (
                        val
                        if isinstance(val, list)
                        else [v.strip() for v in str(val).split(",")]
                    )
                    casted_values = [cast_value(v) for v in values]
                    mask = pc.in_list(table[col], pa.array(casted_values))
                    table = table.filter(mask)

    filtered = (
        filter_dict and filter_dict.get("items") and len(filter_dict["items"]) > 0
    )
    start = page * page_size
    paged_table = table.slice(start, page_size)
    rows = [
        {col: paged_table[col][i].as_py() for col in paged_table.schema.names}
        for i in range(paged_table.num_rows)
    ]
    if filtered:
        total_for_pagination = table.num_rows
    else:
        try:
            info = get_dataset_info(path)
            total_for_pagination = info["total_rows"]
        except Exception:
            total_for_pagination = table.num_rows

    return JSONResponse(content={"rows": rows, "total": total_for_pagination})


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
    with session_factory() as db:
        try:
            existing = db.query(Dataset).filter(Dataset.name == params.name).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A dataset with the name '{params.name}' already exists",
                )

            dataset = Dataset(
                name=params.name,
                file_path="",
            )
            db.add(dataset)
            db.commit()
            db.refresh(dataset)
            return dataset

        except HTTPException:
            raise
        except exc.IntegrityError as e:
            logger.exception(e)
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A dataset with the name '{params.name}' already exists",
            ) from e
        except exc.SQLAlchemyError as e:
            logger.exception(e)
            db.rollback()
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

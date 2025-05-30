import logging
import os
import shutil
from typing import Any, Dict

from fastapi import APIRouter, Depends, Response, status, File, UploadFile
from fastapi.exceptions import HTTPException
from kink import di, inject
from sqlalchemy import exc
from sqlalchemy.orm.session import sessionmaker

from DashAI.back.api.api_v1.schemas.datasets_params import DatasetUpdateParams
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    get_columns_spec,
    get_dataset_info,
    load_dataset,
    update_columns_spec,
)
from DashAI.back.dependencies.database.models import Dataset
import pandas as pd
import pyarrow as pa
from DashAI.back.types.utils import arrow_to_dashai_schema, PTYPE_TO_DASHAI
from DashAI.back.types.inf.ptype.PtypeCat import PtypeCat

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
    """Return the dataset with id dataset_id from the database.

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
            dataset: DashAIDataset = load_dataset(f"{file_path}/dataset")
            sample = dataset.sample(n=10)
        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
    return sample


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
    name : str, optional
        New name for the dataset.
    task_name : str, optional
        New task name for the dataset.
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
                update_columns_spec(os.path.join(dataset.file_path, "dataset"), params.columns)
            if params.name:
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

@router.post("/load_preview")
async def load_preview(
    file: UploadFile = File(...),
    ):
    """Load a small preview of the dataset from a file, without saving it to the database.

    Parameters
    ----------
    file : UploadFile
        The file uploaded by the user.
        This file is expected to be a dataset file (e.g., CSV, Excel, json, etc.).
    
    Returns
    -------
    Dict
        A dictionary containing a preview of the dataset, including the first 10 rows and column types.
    """
    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file.file, nrows=100)
        elif file.filename.endswith(".xlsx"):
            df = pd.read_excel(file.file, nrows=100)
        elif file.filename.endswith(".json"):
            try:
                df = pd.read_json(file.file, lines=True, nrows=100)
            except ValueError:
                # If the JSON is not in lines format, try loading it as a regular JSON
                file.file.seek(0)
                #Hay que mirar el json dataloaderrrrr porque carga a partir de una key dada por el user

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type. Only CSV, Excel, and JSON files are supported.",
            )
        if len(df) > 100:
            df = df.head(100)
        
        table = pa.Table.from_pandas(df)
        print("table:", table.schema)
        schema = arrow_to_dashai_schema(table)
        sample = df.to_dict(orient="records")
        print("dashai schema:", schema)
        #print("struct:", {"sample": sample, "schema": schema})
        return {
            "sample": sample,
            "schema": schema,
        }
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load preview",
        ) from e


@router.post("/infer_datatypes")
async def infer_datatypes(
    file: UploadFile = File(...),
    ):
    """Infer the datatypes of the dataset.

    Parameters
    ----------
    file : UploadFile
        The Dataset from load_preview, as a json.
    
    Returns
    -------
    Dict
        A dictionary containing the inferred datatypes of the dataset columns.
    """
    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file.file)
        elif file.filename.endswith(".xlsx"):
            df = pd.read_excel(file.file)
        elif file.filename.endswith(".json"):
            df = pd.read_json(file.file, lines=True)
        #print("df:", df.head())
        if len(df)>100:
            df = df.head(100)
        ptype_cat = PtypeCat()
        schema = ptype_cat.schema_fit(df)
        first_row = schema.show().iloc[0]
        #print("ptypecat schema:", first_row)
        processed_schema = {}

        for col_name, column_object in schema.cols.items():
            dashai_type = PTYPE_TO_DASHAI.get(max(column_object.p_t, key=column_object.p_t.get))
            processed_schema[col_name] = {
                **dashai_type,
                "probabilities": column_object.p_t,
                "unique_vals_count": len(column_object.unique_vals),
            }
        #print("processed schema:", processed_schema)
        return processed_schema

    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to infer datatypes",
        ) from e
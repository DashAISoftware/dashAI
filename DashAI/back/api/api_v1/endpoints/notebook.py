import logging
import os
import shutil
import uuid

from fastapi import APIRouter, Depends, Response, status
from fastapi.exceptions import HTTPException
from kink import di, inject
from sqlalchemy import exc
from sqlalchemy.orm import Session, sessionmaker

import DashAI.back.api.api_v1.schemas.datasets_params as dataset_params
from DashAI.back.api.api_v1.schemas import notebook_params as schemas
from DashAI.back.dependencies.database.models import (
    ConverterList,
    Dataset,
    Explorer,
    Notebook,
)

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=schemas.Notebook, status_code=status.HTTP_201_CREATED)
@inject
def create_notebook(
    params: schemas.NotebookCreate,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    config: dict = Depends(lambda: di["config"]),
):
    """Create a new notebook entry in the database.

    Parameters
    ----------
    params : schemas.NotebookCreate
        The parameters for creating a notebook.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    schemas.Notebook
        The newly created notebook object.

    Raises
    ------
    HTTPException
        If there is an error creating the notebook, returns a 500 Internal Server Error.
    """
    db: Session
    with session_factory() as db:
        try:
            dataset_id = params.dataset_id
            # Get the dataset
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

            # Copy the dataset
            dataset_folder = dataset.file_path
            random_name = uuid.uuid4().hex[:8]
            new_folder_path = os.path.join(
                config["DATASETS_PATH"],
                random_name,
            )
            os.makedirs(new_folder_path, exist_ok=True)
            shutil.copytree(dataset_folder, new_folder_path, dirs_exist_ok=True)

            notebook_data = params.model_dump()
            notebook_data["file_path"] = new_folder_path
            notebook_model = Notebook(**notebook_data)
            db.add(notebook_model)
            db.commit()
            db.refresh(notebook_model)

            return notebook_model
        except Exception as e:
            log.error(f"Error creating notebook: {e}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create notebook",
            ) from e


@router.get("/", response_model=list[schemas.Notebook])
@inject
def get_notebooks(
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get all notebooks from the database.

    Parameters
    ----------
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.

    Returns
    -------
    list[schemas.Notebook]
        A list of all notebooks in the database.

    Raises
    ------
    HTTPException
        If there is an error retrieving notebooks, returns a 500 Internal Server Error.
    """
    db: Session
    with session_factory() as db:
        try:
            notebooks = db.query(Notebook).all()

        except Exception as e:
            log.error(f"Error retrieving notebooks: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve notebooks",
            ) from e

    return notebooks


@router.get("/{notebook_id}", response_model=schemas.Notebook)
@inject
def get_notebook(
    notebook_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get a notebook by its ID.

    Parameters
    ----------
    notebook_id : int
        ID of the notebook to retrieve.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    schemas.Notebook
        The notebook object with the specified ID.

    Raises
    ------
    HTTPException
        If the notebook is not found, returns a 404 Not Found error.
    """
    db: Session
    with session_factory() as db:
        notebook = db.query(Notebook).filter(Notebook.id == notebook_id).first()
        if not notebook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notebook not found",
            ) from None

        return notebook


@router.get("/{notebook_id}/explorers")
@inject
def get_notebook_explorer_list(
    notebook_id: int,
    skip: int = 0,
    limit: int = 0,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get all explorers associated with a notebook.

    Parameters
    ----------
    notebook_id : int
        ID of the notebook.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    explorers : List[explorer_schemas.Explorer]
        List of explorers associated with the notebook.

    Raises
    ------
    HTTPException
        If there is an error retrieving explorers, returns a 500 Internal Server Error.
    """
    db: Session
    with session_factory() as db:
        explorers = db.query(Explorer).filter(Explorer.notebook_id == notebook_id)

        if skip > 0:
            explorers = explorers.offset(skip)
        if limit > 0:
            explorers = explorers.limit(limit)

        return explorers.all()


@router.get("/{notebook_id}/converters")
@inject
async def get_notebook_converter_list(
    notebook_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get all converters associated with a notebook.

    Parameters
    ----------
    notebook_id : int
        ID of the notebook.
    session_factory : Callable[..., ContextManager[Session]]
        Dependency-injected SQLAlchemy session factory.

    Returns
    -------
    ConverterList
        The converter list associated with the notebook.

    Raises
    ------
        HTTPException: If there is an error retrieving the converter list,
        returns a 500 Internal Server Error.
    """
    with session_factory() as db:
        try:
            converter_list = (
                db.query(ConverterList)
                .filter(ConverterList.notebook_id == notebook_id)
                .all()
            )

            return converter_list
        except Exception as e:
            log.error(
                f"Error retrieving converter list for notebook {notebook_id}: {e}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve converter from notebook {notebook_id}",
            ) from e


@router.delete("/{notebook_id}")
@inject
async def delete_notebook(
    notebook_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Delete the notebook associated with the provided ID from the database.

    Parameters
    ----------
    notebook_id : int
        ID of the notebook to be deleted.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    Response with code 204 NO_CONTENT

    Raises
    ------
    HTTPException
        If the notebook is not registered in the DB.
    """
    log.debug("Deleting notebook with id %s", notebook_id)
    with session_factory() as db:
        try:
            notebook = db.get(Notebook, notebook_id)
            if not notebook:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Notebook not found",
                )

            shutil.rmtree(notebook.file_path, ignore_errors=True)

            db.delete(notebook)
            db.commit()

        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

    try:
        shutil.rmtree(notebook.file_path, ignore_errors=True)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except OSError as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete directory",
        ) from e


@router.post("/{notebook_id}/dataset", response_model=dataset_params.Dataset)
async def create_dataset_from_notebook(
    notebook_id: int,
    params: dataset_params.DatasetUploadFromNotebookParams,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    config: dict = Depends(lambda: di["config"]),
):
    with session_factory() as db:
        try:
            notebook = db.get(Notebook, notebook_id)
            if not notebook:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found"
                )
            dataset_folder = notebook.file_path
            random_name = uuid.uuid4().hex[:8]
            new_folder_path = os.path.join(
                config["DATASETS_PATH"],
                random_name,
            )
            os.makedirs(new_folder_path, exist_ok=True)
            shutil.copytree(dataset_folder, new_folder_path, dirs_exist_ok=True)

            dataset = Dataset(name=params.name, file_path=new_folder_path)
            db.add(dataset)
            db.commit()
            db.refresh(dataset)
        except Exception as e:
            log.error(f"Error creating dataset from notebook {notebook_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create dataset",
            ) from e

    return dataset

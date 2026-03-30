import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from kink import di, inject
from sqlalchemy import exc

from DashAI.back.api.api_v1.schemas import converter_params as schemas

if TYPE_CHECKING:
    from sqlalchemy.orm.session import sessionmaker

    from DashAI.back.dependencies.job_queues import BaseJobQueue

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
@inject
async def post_notebook_converter_list(
    params: schemas.ConverterParams,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Save a list of converters to apply to the notebook.

    Parameters
    ----------
    notebook_id : int
        ID of the notebook.
    converters : Dict[str, ConverterParams]
        A dictionary with the converters to apply to the notebook.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary with the ID of the converter list.

    Raises
    ------
    HTTPException
        If the notebook is not found or if there is an internal database error.
    """
    from DashAI.back.dependencies.database.models import Converter, Notebook

    with session_factory() as db:
        try:
            notebook = db.get(Notebook, params.notebook_id)
            if not notebook:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Notebook not found",
                )

            converter_name = params.converter
            converter_parameters = params.parameters.serialize()

            converter_list = Converter(
                notebook_id=params.notebook_id,
                converter=converter_name,
                parameters=converter_parameters,
            )

            db.add(converter_list)
            db.commit()
            db.refresh(converter_list)

            return converter_list

        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/{converter_list_id}")
@inject
async def get_converter_list(
    converter_list_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Get a converter list from the database.

    Parameters
    ----------
    converter_list_id : int
        ID of the converter list.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    Converter
        The converter list.

    Raises
    ------
    HTTPException
        If the converter list is not found or if there is an internal database error.
    """
    from DashAI.back.dependencies.database.models import Converter

    with session_factory() as db:
        try:
            converter_list = db.get(Converter, converter_list_id)
            if not converter_list:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Converter list not found",
                )

            return converter_list

        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/notebook/{notebook_id}")
@inject
async def get_converters_by_notebook(
    notebook_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Get a list of finished converters from the database by notebook ID.

    Parameters
    ----------
    notebook_id : int
        ID of the notebook.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    List[Converter]
        A list of converter lists.

    Raises
    ------
    HTTPException
        If there is an internal database error.
    """
    from DashAI.back.core.enums.status import ConverterStatus
    from DashAI.back.dependencies.database.models import Converter

    with session_factory() as db:
        try:
            converter_lists = (
                db.query(Converter)
                .filter(Converter.notebook_id == notebook_id)
                .filter(Converter.status == ConverterStatus.FINISHED)
                .all()
            )
            return converter_lists

        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.delete("/{converter_list_id}")
@inject
async def delete_converter_list(
    converter_list_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    job_queue: "BaseJobQueue" = Depends(lambda: di["job_queue"]),
):
    """Delete a converter list from the database."""
    import shutil

    from DashAI.back.dependencies.database.models import Converter, Explorer
    from DashAI.back.job.converter_job import ConverterJob

    with session_factory() as db:
        try:
            converter_list = db.get(Converter, converter_list_id)
            if not converter_list:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Converter list not found",
                )
            notebook = converter_list.notebook

            previous_converters = (
                db.query(Converter)
                .filter(
                    Converter.notebook_id == converter_list.notebook_id,
                    Converter.created < converter_list.created,
                )
                .all()
            )

            next_converters = (
                db.query(Converter)
                .filter(
                    Converter.notebook_id == converter_list.notebook_id,
                    Converter.created >= converter_list.created,
                )
                .all()
            )

            next_explorers = (
                db.query(Explorer)
                .filter(
                    Explorer.notebook_id == converter_list.notebook_id,
                    Explorer.created >= converter_list.created,
                )
                .all()
            )

            # Replace dataset from notebook with the original dataset
            shutil.copytree(
                notebook.dataset.file_path,
                notebook.file_path,
                dirs_exist_ok=True,
            )

            # Enqueue all previous converters
            job_ids = []
            for converter in previous_converters:
                # Crear instancia de ConverterJob y encolarlo directamente
                job = ConverterJob(converter_list_id=converter.id)
                job_queue.put(job)
                if hasattr(job, "id"):
                    job_ids.append(job.id)

            # Delete all the converters after the current one
            for converter in next_converters:
                db.delete(converter)

            # Delete all the explorers after the current converter
            for explorer in next_explorers:
                db.delete(explorer)

            # Delete the current converter
            db.delete(converter_list)
            db.commit()

            last_job_id = job_ids[-1] if job_ids else None
            return {"jobId": last_job_id}

        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

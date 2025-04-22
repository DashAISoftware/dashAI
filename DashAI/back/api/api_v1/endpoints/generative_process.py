import logging

from fastapi import APIRouter, Depends, HTTPException, status
from kink import di
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker

from DashAI.back.api.api_v1.schemas.generative_process_params import (
    GenerativeProcessParams,
)
from DashAI.back.dependencies.database.models import (
    GenerativeProcess,
    GenerativeSession,
)
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.tasks import BaseGenerativeTask

router = APIRouter()
log = logging.getLogger(__name__)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_generative_process(
    params: GenerativeProcessParams,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Create a new generative session.

    Parameters
    ----------
    params : GenerativeProcessParams
        The parameters of the new generative process, which includes the model name,
        task name, parameters, process name and description.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary with the new generative session on the database

    Raises
    ------
    HTTPException
        If there's an internal database error.
    """

    with session_factory() as db:
        try:
            process = GenerativeProcess(
                input=params.input,
                session_id=params.session_id,
            )
            db.add(process)
            db.commit()
            db.refresh(process)
            return process
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/{process_id}", status_code=status.HTTP_200_OK, response_model=None)
async def get_generative_process(
    process_id: str,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
):
    """Get a generative process by its session ID.

    Parameters
    ----------
    process_id : str
        The ID of the generative process to retrieve.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary with the generative process data.

    Raises
    ------
    HTTPException
        If the generative process is not found or if there's an internal database error.
    """
    with session_factory() as db:
        try:
            process = db.query(GenerativeProcess).filter_by(id=process_id).all()
            generative_session: GenerativeSession = db.get(
                GenerativeSession, process[0].session_id
            )

            task: BaseGenerativeTask = component_registry[generative_session.task_name][
                "class"
            ]()

            process = [p.__dict__ for p in process]

            process = [
                {
                    **p,
                    "output": task.process_output_from_database(p["output"]),
                }
                for p in process
            ]

            return process[0]
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get(
    "/session/{session_id}", status_code=status.HTTP_200_OK, response_model=None
)
async def get_generative_process(
    session_id: str,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
):
    """Get a generative process by its session ID.

    Parameters
    ----------
    session_id : str
        The ID of the generative process to retrieve.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary with the generative process data.

    Raises
    ------
    HTTPException
        If the generative process is not found or if there's an internal database error.
    """

    with session_factory() as db:
        try:
            process = db.query(GenerativeProcess).filter_by(session_id=session_id).all()
            generative_session: GenerativeSession = db.get(
                GenerativeSession, session_id
            )

            task: BaseGenerativeTask = component_registry[generative_session.task_name][
                "class"
            ]()

            process = [p.__dict__ for p in process]

            process = [
                {
                    **p,
                    "output": task.process_output_from_database(p["output"]),
                }
                for p in process
            ]

            return process
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

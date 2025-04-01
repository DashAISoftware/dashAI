import logging

from fastapi import APIRouter, Depends, HTTPException, status
from kink import di
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker

from DashAI.back.api.api_v1.schemas.generative_session_params import (
    GenerativeSessionParams,
)
from DashAI.back.dependencies.database.models import GenerativeSession

router = APIRouter()
log = logging.getLogger(__name__)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_generative_session(
    params: GenerativeSessionParams,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Create a new generative session.

    Parameters
    ----------
    params : GenerativesessionParams
        The parameters of the new generative session, which includes the model name,
        task name, parameters, session name and description.
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
            session = GenerativeSession(
                model_name=params.model_name,
                task_name=params.task_name,
                parameters=params.parameters,
                name=params.name,
                description=params.description,
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            return session
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/{session_id}", status_code=status.HTTP_200_OK)
async def get_generative_session(
    session_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get a generative session by its ID.

    Parameters
    ----------
    session_id : int
        The ID of the generative session to retrieve.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary with the generative session on the database

    Raises
    ------
    HTTPException
        If the generative session does not exist or if there's an internal database error.
    """

    with session_factory() as db:
        try:
            session = db.get(GenerativeSession, session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Generative session {session_id} does not exist in DB.",
                )
            return session
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/", status_code=status.HTTP_200_OK)
async def get_all_generative_sessions(
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get all generative sessions.

    Parameters
    ----------
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    list
        A list of dictionaries with all generative sessions on the database

    Raises
    ------
    HTTPException
        If there's an internal database error.
    """

    with session_factory() as db:
        try:
            sessions = db.query(GenerativeSession).all()
            return sessions
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generative_session(
    session_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Delete a generative session by its ID.

    Parameters
    ----------
    session_id : int
        The ID of the generative session to delete.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Raises
    ------
    HTTPException
        If the generative session does not exist or if there's an internal database error.
    """

    with session_factory() as db:
        try:
            session = db.get(GenerativeSession, session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Generative session {session_id} does not exist in DB.",
                )
            db.delete(session)
            db.commit()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
        except Exception as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            ) from e
        finally:
            db.rollback()
            db.close()

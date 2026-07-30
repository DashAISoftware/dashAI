"""REST endpoints for evaluation diagnostics."""

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from kink import di, inject
from sqlalchemy import exc, select

from DashAI.back.api.api_v1.schemas.diagnostics_params import DiagnosticParams
from DashAI.back.dependencies.database.models import Diagnostic, Run

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
@inject
async def get_diagnostics(
    run_id: int = None,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Return the diagnostics stored for a run.

    Parameters
    ----------
    run_id : int, optional
        Run whose diagnostics are requested. All diagnostics when omitted.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy
        session.

    Returns
    -------
    List[Diagnostic]
        The matching diagnostic rows.

    Raises
    ------
    HTTPException
        If the database cannot be read.
    """
    with session_factory() as db:
        try:
            statement = select(Diagnostic)
            if run_id is not None:
                statement = statement.where(Diagnostic.run_id == run_id)
            return db.scalars(statement).all()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/{diagnostic_id}/artifacts")
@inject
async def get_diagnostic_artifacts(
    diagnostic_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Return the computed artifacts of a diagnostic.

    Parameters
    ----------
    diagnostic_id : int
        Id of the diagnostic whose artifacts are requested.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy
        session.

    Returns
    -------
    List[dict]
        Artifact wire dicts, empty when the diagnostic has not run yet.

    Raises
    ------
    HTTPException
        If the diagnostic does not exist or its file cannot be read.
    """
    import pickle

    from DashAI.back.core.artifacts import normalize_artifacts

    with session_factory() as db:
        try:
            diagnostic = db.get(Diagnostic, diagnostic_id)
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

        if not diagnostic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Diagnostic not found",
            )

        if not diagnostic.artifacts_path:
            return []

        try:
            with open(diagnostic.artifacts_path, "rb") as file:
                stored = pickle.load(file)
        except OSError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Diagnostic artifacts file not found",
            ) from e

    # Re-normalized on read for the same reason the explainer plot endpoints
    # do it: artifacts pickled by an older version still come back current.
    return normalize_artifacts(stored)


@router.post("/", status_code=status.HTTP_201_CREATED)
@inject
async def upload_diagnostic(
    params: DiagnosticParams,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Create a diagnostic row for a run.

    Parameters
    ----------
    params : DiagnosticParams
        Run id, diagnostic component name, parameters and split.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy
        session.

    Returns
    -------
    Diagnostic
        The created row.

    Raises
    ------
    HTTPException
        If the run does not exist or the row cannot be stored.
    """
    with session_factory() as db:
        try:
            run: Run = db.get(Run, params.run_id)
            if not run:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
                )

            diagnostic = Diagnostic(
                run_id=params.run_id,
                diagnostic_name=params.diagnostic_name,
                parameters=params.parameters,
                split=params.split,
                name=params.name,
            )
            db.add(diagnostic)
            db.commit()
            db.refresh(diagnostic)
            return diagnostic

        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.delete("/{diagnostic_id}")
@inject
async def delete_diagnostic(
    diagnostic_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Delete a diagnostic and its stored artifacts.

    Parameters
    ----------
    diagnostic_id : int
        Id of the diagnostic to delete.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy
        session.

    Raises
    ------
    HTTPException
        If the diagnostic does not exist or the deletion fails.
    """
    import os

    with session_factory() as db:
        try:
            diagnostic = db.get(Diagnostic, diagnostic_id)
            if not diagnostic:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Diagnostic not found",
                )

            if diagnostic.artifacts_path and os.path.exists(diagnostic.artifacts_path):
                os.remove(diagnostic.artifacts_path)

            db.delete(diagnostic)
            db.commit()

        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

"""REST endpoints for evaluation reports."""

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from kink import di, inject
from sqlalchemy import exc, select

from DashAI.back.api.api_v1.schemas.reports_params import ReportParams
from DashAI.back.dependencies.database.models import Report, Run

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
@inject
async def get_reports(
    run_id: int = None,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Return the reports stored for a run.

    Parameters
    ----------
    run_id : int, optional
        Run whose reports are requested. All reports when omitted.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy
        session.

    Returns
    -------
    List[Report]
        The matching report rows.

    Raises
    ------
    HTTPException
        If the database cannot be read.
    """
    with session_factory() as db:
        try:
            statement = select(Report)
            if run_id is not None:
                statement = statement.where(Report.run_id == run_id)
            return db.scalars(statement).all()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/{report_id}/artifacts")
@inject
async def get_report_artifacts(
    report_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Return the computed artifacts of a report.

    Parameters
    ----------
    report_id : int
        Id of the report whose artifacts are requested.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy
        session.

    Returns
    -------
    List[dict]
        Artifact wire dicts, empty when the report has not run yet.

    Raises
    ------
    HTTPException
        If the report does not exist or its file cannot be read.
    """
    import pickle

    from DashAI.back.core.artifacts import normalize_artifacts

    with session_factory() as db:
        try:
            report = db.get(Report, report_id)
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found",
            )

        if not report.artifacts_path:
            return []

        try:
            with open(report.artifacts_path, "rb") as file:
                stored = pickle.load(file)
        except OSError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report artifacts file not found",
            ) from e

    # Re-normalized on read for the same reason the explainer plot endpoints
    # do it: artifacts pickled by an older version still come back current.
    return normalize_artifacts(stored)


@router.post("/", status_code=status.HTTP_201_CREATED)
@inject
async def upload_report(
    params: ReportParams,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Create a report row for a run.

    Parameters
    ----------
    params : ReportParams
        Run id, report component name, parameters and split.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy
        session.

    Returns
    -------
    Report
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

            report = Report(
                run_id=params.run_id,
                report_name=params.report_name,
                parameters=params.parameters,
                split=params.split,
            )
            db.add(report)
            db.commit()
            db.refresh(report)
            return report

        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.delete("/{report_id}")
@inject
async def delete_report(
    report_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Delete a report and its stored artifacts.

    Parameters
    ----------
    report_id : int
        Id of the report to delete.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy
        session.

    Raises
    ------
    HTTPException
        If the report does not exist or the deletion fails.
    """
    import os

    with session_factory() as db:
        try:
            report = db.get(Report, report_id)
            if not report:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Report not found",
                )

            if report.artifacts_path and os.path.exists(report.artifacts_path):
                os.remove(report.artifacts_path)

            db.delete(report)
            db.commit()

        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

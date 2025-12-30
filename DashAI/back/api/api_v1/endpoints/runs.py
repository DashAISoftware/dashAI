import logging
import os
import pickle
import shutil
from typing import Union

from fastapi import APIRouter, Depends, Response, status
from fastapi.exceptions import HTTPException
from kink import di, inject
from sqlalchemy import exc, select
from sqlalchemy.orm import sessionmaker

from DashAI.back.api.api_v1.schemas.runs_params import RunParams, UpdateRunParams
from DashAI.back.core.enums.metrics import LevelEnum
from DashAI.back.dependencies.database.models import Experiment, Metric, Run, RunStatus

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

router = APIRouter()


def get_metrics_for_run(db, run_id: int):
    """Retrieve metrics associated with a specific run.

    Parameters
    ----------
    db : Session
        SQLAlchemy session to interact with the database.
    run_id : int
        ID of the run for which to retrieve metrics.

    Returns
    -------
    dict
        A dictionary containing train, validation, and test metrics for the run.
    """
    metrics = (
        db.query(Metric)
        .filter(Metric.run_id == run_id, Metric.level == LevelEnum.LAST)
        .all()
    )

    # Initialize the response structure
    response = {
        "train_metrics": None,
        "validation_metrics": None,
        "test_metrics": None,
    }

    # Group metrics by split
    for metric in metrics:
        # Determine the key in the response dictionary
        split_key = f"{metric.split.name.lower()}_metrics"

        if response[split_key] is None:
            response[split_key] = {}

        # In the new schema, we store 'value'.
        # For 'LAST' level, we just want the latest name: value pair.
        response[split_key][metric.name] = metric.value

    return response


@router.get("/")
@inject
async def get_runs(
    experiment_id: Union[int, None] = None,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Retrieve a list of the stored experiment runs in the database.

    The runs can be filtered by experiment_id if the parameter is passed.

    Parameters
    ----------
    experiment_id: Union[int, None], optional
        If specified, the function will return all the runs associated with
        the experiment, by default None.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    List[dict]
        A list with all selected runs.

    Raises
    ------
    HTTPException
        If the experiment is not registered in the DB.
    """
    with session_factory() as db:
        try:
            if experiment_id is not None:
                runs = db.scalars(
                    select(Run).where(Run.experiment_id == experiment_id)
                ).all()
                if not runs:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Runs associated with Experiment not found",
                    )

                # Add metrics to each run
                for run in runs:
                    metrics = get_metrics_for_run(db, run.id)
                    run.train_metrics = metrics["train_metrics"]
                    run.validation_metrics = metrics["validation_metrics"]
                    run.test_metrics = metrics["test_metrics"]
            else:
                runs = db.query(Run).all()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
        return runs


@router.get("/{run_id}")
@inject
async def get_run_by_id(
    run_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Retrieve the run associated with the provided ID.

    Parameters
    ----------
    run_id : int
        ID of the dataset to retrieve.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        All the information of the selected run.

    Raises
    ------
    HTTPException
        If the run is not registered in the DB.
    """
    with session_factory() as db:
        try:
            run = db.get(Run, run_id)
            if not run:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Run not found",
                )
            # Add metrics to the run
            metrics = get_metrics_for_run(db, run_id)
            run.train_metrics = metrics["train_metrics"]
            run.validation_metrics = metrics["validation_metrics"]
            run.test_metrics = metrics["test_metrics"]

        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
        return run


@router.get("/plot/{run_id}/{plot_type}")
@inject
async def get_hyperparameter_optimization_plot(
    run_id: int,
    plot_type: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    with session_factory() as db:
        try:
            run_model = db.scalars(select(Run).where(Run.id == run_id)).all()

            if not run_model:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Run not found",
                )

            if run_model[0].status != RunStatus.FINISHED:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Run hyperaparameter plot not found",
                )

            if plot_type == 1:
                plot_path = run_model[0].plot_history_path
            elif plot_type == 2:
                plot_path = run_model[0].plot_slice_path
            elif plot_type == 3:
                plot_path = run_model[0].plot_contour_path
            else:
                plot_path = run_model[0].plot_importance_path

            with open(plot_path, "rb") as file:
                plot = pickle.load(file)

        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

    return plot


@router.post("/", status_code=status.HTTP_201_CREATED)
@inject
async def upload_run(
    params: RunParams,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Create a new run.

    Parameters
    ----------
    params : int
        The parameters of the new run, which includes the experiment, model name, run
        name and description, among others.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary with the new run on the database

    Raises
    ------
    HTTPException
        If the experiment with id experiment_id is not registered in the DB.
    """
    with session_factory() as db:
        try:
            experiment = db.get(Experiment, params.experiment_id)
            if not experiment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found"
                )
            run = Run(
                experiment_id=params.experiment_id,
                model_name=params.model_name,
                parameters=params.parameters,
                optimizer_name=params.optimizer_name,
                optimizer_parameters=params.optimizer_parameters,
                plot_history_path=params.plot_history_path,
                plot_slice_path=params.plot_slice_path,
                plot_contour_path=params.plot_contour_path,
                plot_importance_path=params.plot_importance_path,
                goal_metric=params.goal_metric,
                name=params.name,
                description=params.description,
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            return run
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.delete("/{run_id}")
@inject
async def delete_run(
    run_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Delete the run associated with the provided ID from the database.

    Parameters
    ----------
    run_id : int
        ID of the run to be deleted.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    Response with code 204 NO_CONTENT

    Raises
    ------
    HTTPException
        If the run is not registered in the DB.
    HTTPException
        If the run was trained but the run_path does not exists.
    """
    with session_factory() as db:
        try:
            run = db.get(Run, run_id)
            if not run:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
                )
            db.delete(run)
            if run.status == RunStatus.FINISHED:
                os.remove(run.run_path)
            db.commit()
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
        except OSError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete directory",
            ) from e


@router.patch("/{run_id}")
@inject
async def update_run(
    run_id: int,
    params: UpdateRunParams,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Updates the run with the provided ID.

    Parameters
    ----------
    run_id : int
        ID of the run to update.
    run_name : Union[str, None], optional
        The new name of the run, by default None.
    run_description : Union[str, None], optional
        The new description of the run, by default None.
    parameters : Union[dict, None], optional
        The new parameters of the run, by default None.
    optimizer: Union[str, None], optional
        The new optimizer of the run, by default None.
    optimizer_parameters: Union[dict, None], optional
        The new optimizer parameters of the run, by default None.
    goal_metric: Union[str, None], optional
        The new goal metric of the run, by default None.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    Dict
        A dictionary containing the updated run record.

    Raises
    ------
    HTTPException
        If no parameters passed.
    """
    with session_factory() as db:
        try:
            run = db.get(Run, run_id)
            if not run:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
                )

            # apply updates
            if params.run_name is not None:
                run.name = params.run_name
            if params.run_description is not None:
                run.description = params.run_description
            if params.parameters is not None:
                run.parameters = params.parameters
                reset_run(run)
            if params.optimizer is not None:
                run.optimizer_name = params.optimizer
                reset_run(run)
            if params.optimizer_parameters is not None:
                run.optimizer_parameters = params.optimizer_parameters
                reset_run(run)
            if params.goal_metric is not None:
                run.goal_metric = params.goal_metric

            if any(
                [
                    params.run_name,
                    params.run_description,
                    params.parameters,
                    params.optimizer,
                    params.optimizer_parameters,
                    params.goal_metric,
                ]
            ):
                db.commit()
                db.refresh(run)
                return run
            else:
                raise HTTPException(
                    status_code=status.HTTP_304_NOT_MODIFIED,
                    detail="Record not modified",
                )
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.patch("/{run_id}/reset")
@inject
async def reset_run_by_id(
    run_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    with session_factory() as db:
        try:
            run = db.get(Run, run_id)
            if not run:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
                )
            reset_run(run)
            db.commit()
            db.refresh(run)
            return run
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


def reset_run(run):
    """
    Reset a run to NOT_STARTED status and delete associated files.

    Parameters
    ----------
    run : Run
        The run object to reset.
    """
    setattr(run, "status", RunStatus.NOT_STARTED)
    setattr(run, "train_metrics", None)
    setattr(run, "validation_metrics", None)
    setattr(run, "test_metrics", None)
    setattr(run, "start_time", None)
    setattr(run, "delivery_time", None)
    setattr(run, "end_time", None)

    # Delete metrics from DB
    with di["session_factory"]() as db:
        db.query(Metric).filter(Metric.run_id == run.id).delete()
        db.commit()

    # Delete files
    if run.run_path and os.path.exists(run.run_path):
        remove_path(run.run_path)
        setattr(run, "run_path", None)
    if run.plot_history_path and os.path.exists(run.plot_history_path):
        remove_path(run.plot_history_path)
        setattr(run, "plot_history_path", None)
    if run.plot_slice_path and os.path.exists(run.plot_slice_path):
        remove_path(run.plot_slice_path)
        setattr(run, "plot_slice_path", None)
    if run.plot_contour_path and os.path.exists(run.plot_contour_path):
        remove_path(run.plot_contour_path)
        setattr(run, "plot_contour_path", None)
    if run.plot_importance_path and os.path.exists(run.plot_importance_path):
        remove_path(run.plot_importance_path)
        setattr(run, "plot_importance_path", None)


def remove_path(path):
    """Removes a file or directory

    Parameters
    ----------
    path : str
        The path to the file or directory to remove.

    Raises
    ------
    ValueError
        Raised if the path is not a file, directory, or symbolic link.
    """
    if os.path.isfile(path) or os.path.islink(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)
    else:
        raise ValueError("file {} is not a file or dir.".format(path))

import logging
from typing import TYPE_CHECKING, Union

from fastapi import APIRouter, Depends, Response, status
from fastapi.exceptions import HTTPException
from kink import di, inject
from sqlalchemy import exc, select

from DashAI.back.api.api_v1.schemas.runs_params import RunParams, UpdateRunParams
from DashAI.back.core.enums.metrics import LevelEnum
from DashAI.back.dependencies.database.models import (
    GlobalExplainer,
    LocalExplainer,
    Metric,
    ModelSession,
    Prediction,
    Run,
    RunStatus,
)
from DashAI.back.dependencies.downloads.nested import missing_downloads

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker


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
    model_session_id: Union[int, None] = None,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Retrieve a list of the stored model session runs in the database.

    The runs can be filtered by model_session_id if the parameter is passed.

    Parameters
    ----------
    model_session_id: Union[int, None], optional
        If specified, the function will return all the runs associated with
        the model session, by default None.
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
        If the model session is not registered in the DB.
    """
    with session_factory() as db:
        try:
            if model_session_id is not None:
                model_session = db.get(ModelSession, model_session_id)
                if not model_session:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Model session not found",
                    )
                runs = db.scalars(
                    select(Run).where(Run.model_session_id == model_session_id)
                ).all()
                if not runs:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Runs associated with Model Session not found",
                    )
            else:
                runs = db.query(Run).all()

            # Add metrics to each run
            for run in runs:
                metrics = get_metrics_for_run(db, run.id)
                run.train_metrics = metrics["train_metrics"]
                run.validation_metrics = metrics["validation_metrics"]
                run.test_metrics = metrics["test_metrics"]

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
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
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
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    import pickle

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

    from DashAI.back.core.artifacts import normalize_artifacts

    # Re-normalized on every read (not just on save) so plots pickled before
    # this endpoint returned typed artifacts (plain plotly JSON strings)
    # still come back in the same {type, payload, title} shape.
    return normalize_artifacts(plot)[0]


@router.get("/{run_id}/model_artifacts")
@inject
async def get_run_model_artifacts(
    run_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Return the stored visualizations of a run's trained model.

    Parameters
    ----------
    run_id : int
        Id of the run whose model artifacts are requested.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy
        session. The generated session can be used to access and query the
        database.

    Returns
    -------
    dict
        ``{"status": Optional[str], "artifacts": List[dict]}``. The status is
        None and the list empty when generation has never run for this run.

    Raises
    ------
    HTTPException
        If the run does not exist or its stored artifacts cannot be read.
    """
    import pickle

    from DashAI.back.core.artifacts import normalize_artifacts

    with session_factory() as db:
        try:
            run = db.get(Run, run_id)
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Run not found",
            )

        artifacts_status = (
            run.model_artifacts_status.name if run.model_artifacts_status else None
        )
        if not run.model_artifacts_path:
            return {"status": artifacts_status, "artifacts": []}

        try:
            with open(run.model_artifacts_path, "rb") as file:
                stored = pickle.load(file)
        except OSError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model artifacts file not found",
            ) from e

    # Re-normalized on read for the same reason the hyperparameter plot
    # endpoint does it: artifacts pickled by an older version still come back
    # in the current wire shape.
    return {"status": artifacts_status, "artifacts": normalize_artifacts(stored)}


@router.post("/", status_code=status.HTTP_201_CREATED)
@inject
async def upload_run(
    params: RunParams,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry=Depends(lambda: di["component_registry"]),
):
    """Create a new run.

    Parameters
    ----------
    params : RunParams
        The parameters of the new run, which includes the model session, model name, run
        name and description, among others.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.
    component_registry : ComponentRegistry
        The application component registry, used to check whether the requested
        model has been downloaded.

    Returns
    -------
    dict
        A dictionary with the new run on the database

    Raises
    ------
    HTTPException
        If the model session with id model_session_id is not registered in the DB.
    HTTPException
        If the model requires a download but has not been downloaded yet (HTTP 409).
    """
    with session_factory() as db:
        try:
            model_session = db.get(ModelSession, params.model_session_id)
            if not model_session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Model session not found",
                )
            # REQUIRES_DOWNLOAD is the static contract; the download state is
            # reconciled against the filesystem so a model downloaded after
            # startup (in the worker process) is recognised without a restart.
            if params.model_name not in component_registry:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unknown model '{params.model_name}'",
                )
            entry = component_registry[params.model_name]
            if getattr(
                entry["class"], "REQUIRES_DOWNLOAD", False
            ) and not component_registry.refresh_download_status(params.model_name):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Model {params.model_name} must be downloaded before use."
                    ),
                )
            # A parameter may select another component (e.g. a classifier) that
            # itself needs downloading; block until every nested one is present.
            nested_missing = missing_downloads(params.parameters, component_registry)
            if nested_missing:
                names = ", ".join(m["name"] for m in nested_missing)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"These components must be downloaded before use: {names}."
                    ),
                )
            run = Run(
                model_session_id=params.model_session_id,
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
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
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
    import os

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
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
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
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
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


@router.get("/{run_id}/operations/count")
@inject
async def get_run_operations_count(
    run_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Get the count of operations (explainers and predictions) for a run.

    Parameters
    ----------
    run_id : int
        ID of the run to count operations for.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary with 'explainers' and 'predictions' counts.

    Raises
    ------
    HTTPException
        If the run is not found or there's a database error.
    """
    with session_factory() as db:
        try:
            run = db.get(Run, run_id)
            if not run:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
                )

            # Count global explainers
            global_explainers_count = (
                db.query(GlobalExplainer)
                .filter(GlobalExplainer.run_id == run_id)
                .count()
            )

            # Count local explainers
            local_explainers_count = (
                db.query(LocalExplainer).filter(LocalExplainer.run_id == run_id).count()
            )

            # Count predictions
            predictions_count = (
                db.query(Prediction).filter(Prediction.run_id == run_id).count()
            )

            return {
                "explainers": global_explainers_count + local_explainers_count,
                "predictions": predictions_count,
            }
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.delete("/{run_id}/operations")
@inject
async def delete_run_operations(
    run_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Delete all operations (explainers and predictions) associated with a run.

    Parameters
    ----------
    run_id : int
        ID of the run whose operations should be deleted.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary indicating the number of deleted items.

    Raises
    ------
    HTTPException
        If the run is not found or there's a database error.
    """
    import os

    with session_factory() as db:
        try:
            run = db.get(Run, run_id)
            if not run:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
                )

            deleted_count = {
                "global_explainers": 0,
                "local_explainers": 0,
                "predictions": 0,
            }

            # Delete global explainers
            global_explainers = (
                db.query(GlobalExplainer).filter(GlobalExplainer.run_id == run_id).all()
            )
            for explainer in global_explainers:
                # Delete associated files
                if explainer.plot_path and os.path.exists(explainer.plot_path):
                    try:
                        remove_path(explainer.plot_path)
                    except Exception as e:
                        log.warning(f"Failed to delete plot file: {e}")
                if explainer.explanation_path and os.path.exists(
                    explainer.explanation_path
                ):
                    try:
                        remove_path(explainer.explanation_path)
                    except Exception as e:
                        log.warning(f"Failed to delete explanation file: {e}")
                db.delete(explainer)
                deleted_count["global_explainers"] += 1

            # Delete local explainers
            local_explainers = (
                db.query(LocalExplainer).filter(LocalExplainer.run_id == run_id).all()
            )
            for explainer in local_explainers:
                # Delete associated files
                if explainer.plots_path and os.path.exists(explainer.plots_path):
                    try:
                        remove_path(explainer.plots_path)
                    except Exception as e:
                        log.warning(f"Failed to delete plots directory: {e}")
                if explainer.explanation_path and os.path.exists(
                    explainer.explanation_path
                ):
                    try:
                        remove_path(explainer.explanation_path)
                    except Exception as e:
                        log.warning(f"Failed to delete explanation file: {e}")
                db.delete(explainer)
                deleted_count["local_explainers"] += 1

            # Delete predictions
            predictions = db.query(Prediction).filter(Prediction.run_id == run_id).all()
            for prediction in predictions:
                # Delete associated files
                if prediction.results_path and os.path.exists(prediction.results_path):
                    try:
                        remove_path(prediction.results_path)
                    except Exception as e:
                        log.warning(f"Failed to delete prediction results: {e}")
                db.delete(prediction)
                deleted_count["predictions"] += 1

            db.commit()

            return {
                "deleted": True,
                "count": deleted_count,
                "total": sum(deleted_count.values()),
            }
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
    import os

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
    import os
    import shutil

    if os.path.isfile(path) or os.path.islink(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)
    else:
        raise ValueError("file {} is not a file or dir.".format(path))

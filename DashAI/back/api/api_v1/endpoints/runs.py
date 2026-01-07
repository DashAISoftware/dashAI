import json
import logging
import os
import pickle
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Union

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Response,
    UploadFile,
    status,
)
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse
from kink import di, inject
from sqlalchemy import exc, select
from sqlalchemy.orm import sessionmaker

from DashAI.back.api.api_v1.endpoints.utils.run_utils import (
    create_run_from_export,
    get_metrics_for_run,
    parse_metrics,
    reset_run,
    serialize_metrics,
    serialize_run,
    validate_import_structure,
    zip_directory,
)
from DashAI.back.api.api_v1.schemas.runs_params import RunParams, UpdateRunParams
from DashAI.back.dependencies.database.models import Experiment, Run, RunStatus

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

router = APIRouter()


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


@router.get("/{run_id}/export_model")
@inject
async def export_model(
    run_id: int,
    background_tasks: BackgroundTasks,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Export the trained model associated with the provided run ID.

    Parameters
    ----------
    run_id : int
        ID of the run whose model is to be exported.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    FileResponse
        A zip file containing the model and associated metadata.

    Raises
    ------
    HTTPException
        If the run is not found or if the model file does not exist.
    """
    with session_factory() as db:
        run = db.get(Run, run_id)
        if not run:
            raise HTTPException(404, "Run not found")

        if not run.run_path or not os.path.exists(run.run_path):
            raise HTTPException(404, "Model file not found")

        # Create temp dir
        tmp_dir = Path(tempfile.mkdtemp())

        export_dir = tmp_dir / f"run_{run_id}"
        export_dir.mkdir()

        # Metadata for run and metrics
        (export_dir / "run.json").write_text(json.dumps(serialize_run(run), indent=2))

        (export_dir / "metrics.json").write_text(
            json.dumps(serialize_metrics(run.metrics), indent=2)
        )

        # Copy model files
        model_dir = export_dir / "model"
        model_dir.mkdir()

        model_path = Path(run.run_path)
        if model_path.is_dir():
            shutil.copytree(model_path, model_dir, dirs_exist_ok=True)
        else:
            shutil.copy2(model_path, model_dir / model_path.name)

        # Copy HPO plot files if they exist
        hpo_plots = {
            "plot_history": run.plot_history_path,
            "plot_slice": run.plot_slice_path,
            "plot_contour": run.plot_contour_path,
            "plot_importance": run.plot_importance_path,
        }
        for _, plot_path in hpo_plots.items():
            if plot_path and os.path.exists(plot_path):
                shutil.copy2(plot_path, export_dir / Path(plot_path).name)

        # Create zip file
        zip_path = tmp_dir / f"run_{run_id}_export.zip"
        zip_directory(export_dir, zip_path)

        # Schedule temp dir removal after response
        background_tasks.add_task(shutil.rmtree, tmp_dir, ignore_errors=True)

        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename=zip_path.name,
            background=background_tasks,
        )


@router.post("/import_run", status_code=status.HTTP_201_CREATED)
@inject
async def import_run(
    experiment_id: int,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    config: dict = Depends(lambda: di["config"]),
):
    """
    Import a run from a ZIP file containing the model and associated metadata.

    Parameters
    ----------
    experiment_id : int
        ID of the experiment to which the imported run will be associated.
    file : UploadFile
        A ZIP file containing the run data and model files.

    Returns
    -------
    dict
        A dictionary containing the imported run ID, experiment ID, and status.

    """

    if file.content_type != "application/zip":
        raise HTTPException(400, "Expected a ZIP file")

    # Create temp dir
    tmp_dir = Path(tempfile.mkdtemp())

    try:
        zip_path = tmp_dir / "upload.zip"
        extract_dir = tmp_dir / "extracted"

        zip_path.write_bytes(await file.read())

        with zipfile.ZipFile(zip_path) as zipf:
            zipf.extractall(extract_dir)

        try:
            validate_import_structure(extract_dir)
        except ValueError as e:
            raise HTTPException(400, str(e)) from e

        run_data = json.loads((extract_dir / "run.json").read_text())
        metrics_path = extract_dir / "metrics.json"

        with session_factory() as db:
            experiment = db.get(Experiment, experiment_id)
            if not experiment:
                raise HTTPException(404, "Experiment not found")

            # Create run record
            run = create_run_from_export(run_data, experiment_id)
            db.add(run)
            db.flush()  # get run.id

            # Copy model files
            model_src = extract_dir / "model"

            run_dir = Path(config["RUNS_PATH"]) / str(run.id)
            run_dir.mkdir(parents=True, exist_ok=True)

            # List contents of model/
            entries = list(model_src.iterdir())

            if len(entries) == 1 and entries[0].is_file():
                # Single file model
                dst = run_dir / entries[0].name
                shutil.copy2(entries[0], dst)
                run.run_path = str(dst)

            else:
                # Directory model
                shutil.copytree(
                    model_src,
                    run_dir,
                    dirs_exist_ok=True,
                )
                run.run_path = str(run_dir)

            # Add HPO plot paths if available
            hpo_plots = {
                "plot_history": run_data.get("plot_history_path"),
                "plot_slice": run_data.get("plot_slice_path"),
                "plot_contour": run_data.get("plot_contour_path"),
                "plot_importance": run_data.get("plot_importance_path"),
            }
            for plot_name, plot_path in hpo_plots.items():
                if plot_path:
                    src_path = extract_dir / Path(plot_path).name
                    if src_path.exists():
                        dst_path = Path(config["RUNS_PATH"]) / (
                            plot_name + "_" + str(run.id) + src_path.suffix
                        )
                        shutil.copy2(src_path, dst_path)
                        setattr(run, plot_name + "_path", str(dst_path))

            # Add metrics if available
            if metrics_path.exists():
                metrics_json = json.loads(metrics_path.read_text())
                db.add_all(parse_metrics(metrics_json, run.id))

            db.commit()

            return {
                "run_id": run.id,
                "experiment_id": experiment_id,
                "status": "imported",
            }

    finally:
        # Schedule temp dir removal after response
        background_tasks.add_task(shutil.rmtree, tmp_dir, ignore_errors=True)

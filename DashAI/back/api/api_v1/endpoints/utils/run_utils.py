import io
import os
import shutil
import zipfile
from pathlib import Path

from kink import di

from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.dependencies.database.models import Metric, Run, RunStatus


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


def serialize_run(run: Run) -> dict:
    """
    Serializes a Run object into a dictionary suitable for JSON responses.

    Parameters
    ----------
    run : Run
        The Run object to serialize.

    Returns
    -------
    dict
        A dictionary representation of the Run object.
    """
    return {
        "id": run.id,
        "experiment_id": run.experiment_id,
        "name": run.name,
        "description": run.description,
        "model_name": run.model_name,
        "parameters": run.parameters,
        # optimizer
        "optimizer_name": run.optimizer_name,
        "optimizer_parameters": run.optimizer_parameters,
        "goal_metric": run.goal_metric,
        "plot_history_path": (
            Path(run.plot_history_path).name if run.plot_history_path else None
        ),
        "plot_slice_path": (
            Path(run.plot_slice_path).name if run.plot_slice_path else None
        ),
        "plot_contour_path": (
            Path(run.plot_contour_path).name if run.plot_contour_path else None
        ),
        "plot_importance_path": (
            Path(run.plot_importance_path).name if run.plot_importance_path else None
        ),
        # status and timestamps
        "status": run.status.value,
        "created": run.created.isoformat(),
        "last_modified": run.last_modified.isoformat() if run.last_modified else None,
        "delivery_time": run.delivery_time.isoformat() if run.delivery_time else None,
        "start_time": run.start_time.isoformat() if run.start_time else None,
        "end_time": run.end_time.isoformat() if run.end_time else None,
    }


def serialize_metrics(metrics: list[Metric]) -> dict:
    """
    Serializes a list of Metric objects into a nested dictionary.

    Parameters
    ----------
    metrics : list[Metric]
        The list of Metric objects to serialize.

    Returns
    -------
    dict
        A nested dictionary representation of the metrics.
    """

    out = {}
    for m in metrics:
        out.setdefault(m.split.value, {}).setdefault(m.level.value, {}).setdefault(
            m.name, []
        ).append({"step": m.step, "value": m.value})
    return out


def zip_directory_generator(base_path: Path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in base_path.rglob("*"):
            zipf.write(file, file.relative_to(base_path))
    buffer.seek(0)
    yield from buffer


def zip_directory(source: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in source.rglob("*"):
            if file.is_file():
                zipf.write(file, file.relative_to(source))


def validate_import_structure(root: Path):
    if not (root / "run.json").exists():
        raise ValueError("Missing run.json")

    if not (root / "model").exists():
        raise ValueError("Missing model directory")


def create_run_from_export(run_data: dict, experiment_id: int) -> Run:
    return Run(
        experiment_id=experiment_id,
        model_name=run_data["model_name"],
        parameters=run_data["parameters"],
        optimizer_name=run_data["optimizer_name"],
        optimizer_parameters=run_data["optimizer_parameters"],
        goal_metric=run_data["goal_metric"],
        name=f"imported-{run_data.get('name')}",
        description=run_data.get("description"),
        status=RunStatus.FINISHED,
    )


def parse_metrics(metrics_json: dict, run_id: int) -> list[Metric]:
    metrics = []

    for split, levels in metrics_json.items():
        for level, names in levels.items():
            for name, values in names.items():
                for entry in values:
                    metrics.append(
                        Metric(
                            run_id=run_id,
                            split=SplitEnum(split),
                            level=LevelEnum(level),
                            name=name,
                            step=entry["step"],
                            value=entry["value"],
                        )
                    )
    return metrics

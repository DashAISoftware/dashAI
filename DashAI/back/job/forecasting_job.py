"""Forecasting-specific job for time series model training."""

import gc
import json
import logging
import os
import pickle
from typing import List

from kink import inject
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker

from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    load_dataset,
    prepare_for_forecasting_experiment,
    select_columns,
    split_dataset,
)
from DashAI.back.dependencies.database.models import Dataset, ModelSession, Run
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.metrics import BaseMetric
from DashAI.back.models import BaseModel
from DashAI.back.models.model_factory import ModelFactory
from DashAI.back.optimizers import BaseOptimizer
from DashAI.back.tasks import BaseTask

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class ForecastingJob(BaseJob):
    """ForecastingJob class for time series model training with temporal splitting."""

    @inject
    def set_status_as_delivered(
        self, session_factory: sessionmaker = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the job as delivered."""
        run_id: int = self.kwargs["run_id"]

        with session_factory() as db:
            run: Run = db.get(Run, run_id)
            if not run:
                raise JobError(f"Run {run_id} does not exist in DB.")
            try:
                run.set_status_as_delivered()
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise JobError(
                    "Internal database error",
                ) from e

    @inject
    def set_status_as_error(
        self, session_factory: sessionmaker = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the job as error."""
        run_id: int = self.kwargs.get("run_id")
        if run_id is None:
            return

        with session_factory() as db:
            run: Run = db.get(Run, run_id)
            if not run:
                return
            try:
                run.set_status_as_error()
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)

    @inject
    def get_job_name(self) -> str:
        """Get a descriptive name for the job."""
        run_id = self.kwargs.get("run_id")
        if not run_id:
            return "Forecasting Training"

        from kink import di

        session_factory = di["session_factory"]

        try:
            with session_factory() as db:
                run: Run = db.get(Run, run_id)
                if run and run.name:
                    return f"Forecast: {run.name}"
        except Exception:
            pass

        return f"Forecasting Training ({run_id})"

    @inject
    def run(self) -> None:
        from kink import di

        from DashAI.back.api.api_v1.endpoints.components import (
            _intersect_component_lists,
        )

        component_registry = di["component_registry"]
        session_factory = di["session_factory"]
        config = di["config"]

        # Get the necessary parameters
        run_id: int = self.kwargs["run_id"]

        with session_factory() as db:
            run: Run = db.get(Run, run_id)
            run.huey_id = self.kwargs.get("huey_id", None)
            db.commit()
            try:
                # Get the model session, dataset, task, metrics and splits
                model_session: ModelSession = db.get(ModelSession, run.model_session_id)
                if not model_session:
                    raise JobError(
                        f"Model session {run.model_session_id} does not exist in DB."
                    )
                dataset: Dataset = db.get(Dataset, model_session.dataset_id)
                if not dataset:
                    raise JobError(
                        f"Dataset {model_session.dataset_id} does not exist in DB."
                    )

                try:
                    loaded_dataset: DashAIDataset = load_dataset(
                        f"{dataset.file_path}/dataset"
                    )
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Can not load dataset from path {dataset.file_path}",
                    ) from e

                try:
                    task: BaseTask = component_registry[model_session.task_name][
                        "class"
                    ]()
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        (
                            f"Unable to find Task with name {model_session.task_name} "
                            "in registry"
                        ),
                    ) from e

                # Validate this is a forecasting task
                if model_session.task_name != "ForecastingTask":
                    raise JobError(
                        f"ForecastingJob can only be used with ForecastingTask, "
                        f"got {model_session.task_name}"
                    )

                try:
                    # Get all the metrics
                    components_by_type = component_registry.get_components_by_types(
                        select="Metric"
                    )
                    all_metrics = {
                        component_dict["name"]: component_dict
                        for component_dict in components_by_type
                    }
                    # Get the intersection between the metrics and the task
                    # related components
                    selected_metrics = _intersect_component_lists(
                        all_metrics,
                        component_registry.get_related_components(
                            model_session.task_name
                        ),
                    )
                    metrics: List[BaseMetric] = [
                        metric["class"] for metric in selected_metrics.values()
                    ]
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        "Unable to find metrics associated with"
                        f"Task {model_session.task_name} in registry",
                    ) from e

                try:
                    # Prepare dataset for forecasting task with auto-detection
                    prepared_dataset = task.prepare_for_task(
                        loaded_dataset,
                        outputs_columns=model_session.output_columns,
                        inputs_columns=model_session.input_columns,
                        # Optional: Override auto-detection if specified
                        timestamp_column=getattr(
                            model_session, "timestamp_column", None
                        ),
                        frequency=getattr(model_session, "frequency", "auto"),
                    )

                    # Get temporal metadata for logging
                    temporal_metadata = task.get_temporal_metadata()
                    log.info(f"Temporal metadata: {temporal_metadata}")

                    splits = json.loads(model_session.splits)

                    # Use forecasting-specific preparation with temporal splitting
                    prepared_dataset, splits = prepare_for_forecasting_experiment(
                        dataset=prepared_dataset,
                        splits=splits,
                        timestamp_col=temporal_metadata.get("timestamp_col", "ds"),
                        output_columns=model_session.output_columns,
                    )

                    run.split_indexes = json.dumps(
                        {
                            "train_indexes": splits["train_indexes"],
                            "test_indexes": splits["test_indexes"],
                            "val_indexes": splits["val_indexes"],
                        }
                    )

                    x, y = select_columns(
                        prepared_dataset,
                        model_session.input_columns,
                        model_session.output_columns,
                    )

                    x = split_dataset(x)
                    y = split_dataset(y)

                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"""Can not prepare Dataset {dataset.id}
                        for ForecastingTask {model_session.task_name}""",
                    ) from e

                try:
                    run_model_class = component_registry[run.model_name]["class"]
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Unable to find Model with name {run.model_name} in registry.",
                    ) from e

                # Validate model is compatible with forecasting
                if not hasattr(run_model_class, "_compatible_tasks"):
                    log.warning(
                        f"Model {run.model_name} does not specify task compatibility"
                    )
                elif "ForecastingTask" not in getattr(
                    run_model_class, "_compatible_tasks", []
                ):
                    raise JobError(
                        f"Model {run.model_name} is not compatible with ForecastingTask"
                    )

                try:
                    factory = ModelFactory(
                        run_model_class,
                        run.parameters,
                        # No n_labels for forecasting tasks
                        n_labels=None,
                    )
                    model: BaseModel = factory.model
                    run_optimizable_parameters = factory.optimizable_parameters

                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Unable to instantiate forecasting model using run {run_id}",
                    ) from e

                # Handle hyperparameter optimization for forecasting
                if run_optimizable_parameters:
                    try:
                        # Optimizer configuration
                        run_optimizer_class = component_registry[run.optimizer_name][
                            "class"
                        ]
                    except Exception as e:
                        log.exception(e)
                        raise JobError(
                            f"Unable to find Optimizer with name "
                            f"{run.optimizer_name} in registry.",
                        ) from e

                    if run.goal_metric != "":
                        try:
                            goal_metric = selected_metrics[run.goal_metric]
                        except Exception as e:
                            log.exception(e)
                            raise JobError(
                                "Metric is not compatible with the ForecastingTask",
                            ) from e
                        try:
                            optimizer: BaseOptimizer = run_optimizer_class(
                                **run.optimizer_parameters
                            )
                        except Exception as e:
                            log.exception(e)
                            raise JobError(
                                (
                                    "Optimizer parameters not compatible "
                                    "with the optimizer"
                                ),
                            ) from e

                try:
                    run.set_status_as_started()
                    db.commit()
                except exc.SQLAlchemyError as e:
                    log.exception(e)
                    raise JobError(
                        "Connection with the database failed",
                    ) from e

                try:
                    # Forecasting model training
                    if not run_optimizable_parameters:
                        # Simple fit with forecasting-specific parameters
                        # Pass temporal metadata to model for column information
                        if hasattr(model, "fit") and hasattr(model, "_task_type"):
                            model.fit(
                                x["train"],
                                y["train"],
                                temporal_metadata=temporal_metadata,
                            )
                        else:
                            model.fit(x["train"], y["train"])
                    else:
                        # Hyperparameter optimization for forecasting
                        optimizer.optimize(
                            model,
                            x,
                            y,
                            run_optimizable_parameters,
                            goal_metric,
                            model_session.task_name,
                        )
                        model = optimizer.get_model()
                        # Generate hyperparameter plot
                        trials = optimizer.get_trials_values()
                        plot_filenames, plots = optimizer.create_plots(
                            trials, run_id, n_params=len(run_optimizable_parameters)
                        )
                        plot_paths = []
                        for filename, plot in zip(plot_filenames, plots, strict=True):
                            plot_path = os.path.join(config["RUNS_PATH"], filename)
                            with open(plot_path, "wb") as file:
                                pickle.dump(plot, file)
                                plot_paths.append(plot_path)

                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        "Forecasting model training failed",
                    ) from e

                # Save hyperparameter plots if optimization was used
                if run_optimizable_parameters != {}:
                    if len(run_optimizable_parameters) >= 2:
                        try:
                            run.plot_history_path = plot_paths[0]
                            run.plot_slice_path = plot_paths[1]
                            run.plot_contour_path = plot_paths[2]
                            run.plot_importance_path = plot_paths[3]
                            db.commit()
                        except Exception as e:
                            log.exception(e)
                            raise JobError(
                                "Hyperparameter plot path saving failed",
                            ) from e
                    else:
                        try:
                            run.plot_history_path = plot_paths[0]
                            run.plot_slice_path = plot_paths[1]
                            db.commit()
                        except Exception as e:
                            log.exception(e)
                            raise JobError(
                                "Hyperparameter plot path saving failed",
                            ) from e

                try:
                    run.set_status_as_finished()
                    db.commit()
                except exc.SQLAlchemyError as e:
                    log.exception(e)
                    raise JobError(
                        "Connection with the database failed",
                    ) from e

                try:
                    # Evaluate with forecasting-specific metrics
                    model_metrics = factory.evaluate(x, y, metrics)

                    # Add forecasting-specific metadata to metrics
                    for split in ["train", "validation", "test"]:
                        if split in model_metrics:
                            model_metrics[split]["temporal_metadata"] = {
                                "frequency": temporal_metadata.get("frequency"),
                                "n_periods": temporal_metadata.get("n_periods"),
                                "start_date": str(temporal_metadata.get("start_date")),
                                "end_date": str(temporal_metadata.get("end_date")),
                            }

                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        "Forecasting metrics calculation failed",
                    ) from e

                run.train_metrics = model_metrics["train"]
                run.validation_metrics = model_metrics["validation"]
                run.test_metrics = model_metrics["test"]

                try:
                    run_path = os.path.join(config["RUNS_PATH"], str(run.id))
                    model.save(run_path)

                    # Save forecasting-specific artifacts
                    if hasattr(model, "get_forecast_components"):
                        try:
                            # Save forecast components for interpretation
                            components = model.get_forecast_components(horizon=30)
                            components_path = os.path.join(
                                run_path, "forecast_components.csv"
                            )
                            components.to_csv(components_path, index=False)
                            log.info(f"Saved forecast components to {components_path}")
                        except Exception as e:
                            log.warning(f"Could not save forecast components: {e}")

                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        "Forecasting model saving failed",
                    ) from e

                try:
                    run.run_path = run_path
                    db.commit()
                    log.info(
                        f"✅ ForecastingJob completed successfully for run {run_id}"
                    )
                except exc.SQLAlchemyError as e:
                    log.exception(e)
                    run.set_status_as_error()
                    db.commit()
                    raise JobError(
                        "Connection with the database failed",
                    ) from e
            except Exception as e:
                run.set_status_as_error()
                db.commit()
                raise e
            finally:
                gc.collect()

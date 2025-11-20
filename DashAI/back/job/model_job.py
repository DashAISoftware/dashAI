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
    prepare_for_experiment,
    select_columns,
    split_dataset,
)
from DashAI.back.dependencies.database.models import Dataset, Experiment, Run
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.metrics import BaseMetric
from DashAI.back.models import BaseModel
from DashAI.back.models.model_factory import ModelFactory
from DashAI.back.optimizers import BaseOptimizer
from DashAI.back.tasks import BaseTask

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class ModelJob(BaseJob):
    """ModelJob class to run the model training."""

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
            return "Model Training"

        from kink import di

        session_factory = di["session_factory"]

        try:
            with session_factory() as db:
                run: Run = db.get(Run, run_id)
                if run and run.name:
                    return f"Train: {run.name}"
        except Exception:
            pass

        return f"Model Training ({run_id})"

    @inject
    def run(
        self,
    ) -> None:
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
                # Get the experiment, dataset, task, metrics and splits
                experiment: Experiment = db.get(Experiment, run.experiment_id)
                if not experiment:
                    raise JobError(
                        f"Experiment {run.experiment_id} does not exist in DB."
                    )
                dataset: Dataset = db.get(Dataset, experiment.dataset_id)
                if not dataset:
                    raise JobError(
                        f"Dataset {experiment.dataset_id} does not exist in DB."
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
                    task: BaseTask = component_registry[experiment.task_name]["class"]()
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        (
                            f"Unable to find Task with name {experiment.task_name} "
                            "in registry"
                        ),
                    ) from e

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
                        component_registry.get_related_components(experiment.task_name),
                    )
                    metrics: List[BaseMetric] = [
                        metric["class"] for metric in selected_metrics.values()
                    ]
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        "Unable to find metrics associated with"
                        f"Task {experiment.task_name} in registry",
                    ) from e

                try:
                    prepared_dataset = task.prepare_for_task(
                        loaded_dataset, experiment.output_columns
                    )
                    n_labels = task.num_labels(
                        prepared_dataset, experiment.output_columns[0]
                    )

                    splits = json.loads(experiment.splits)
                    prepared_dataset, splits = prepare_for_experiment(
                        dataset=prepared_dataset,
                        splits=splits,
                        output_columns=experiment.output_columns,
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
                        experiment.input_columns,
                        experiment.output_columns,
                    )

                    x = split_dataset(x)
                    y = split_dataset(y)

                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"""Can not prepare Dataset {dataset.id}
                        for Task {experiment.task_name}""",
                    ) from e

                try:
                    run_model_class = component_registry[run.model_name]["class"]
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Unable to find Model with name {run.model_name} in registry.",
                    ) from e
                try:
                    factory = ModelFactory(
                        run_model_class, run.parameters, n_labels=n_labels
                    )
                    model: BaseModel = factory.model
                    run_optimizable_parameters = factory.optimizable_parameters

                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Unable to instantiate model using run {run_id}",
                    ) from e
                try:
                    if run_optimizable_parameters:
                        goal_metric = selected_metrics[run.goal_metric]
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Metric is not compatible with the Task. {e}",
                    ) from e
                try:
                    # Optimizer configuration
                    if run_optimizable_parameters:
                        run_optimizer_class = component_registry[run.optimizer_name][
                            "class"
                        ]
                        optimizer: BaseOptimizer = run_optimizer_class(
                            **run.optimizer_parameters
                        )
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Error instantiating optimizer {run.optimizer_name}, {e}",
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
                    # Hyperparameter Tunning
                    plot_paths = []
                    if not run_optimizable_parameters:
                        model.fit(x["train"], y["train"])
                    else:
                        optimizer.optimize(
                            model,
                            x,
                            y,
                            run_optimizable_parameters,
                            goal_metric,
                            task,
                        )
                        model = optimizer.get_model()
                        # Generate hyperparameter plot
                        trials = optimizer.get_trials_values()
                        plot_filenames, plots = optimizer.create_plots(
                            trials,
                            run_id,
                            n_params=len(run_optimizable_parameters),
                            goal_metric=goal_metric,
                        )
                        for filename, plot in zip(plot_filenames, plots):
                            plot_path = os.path.join(config["RUNS_PATH"], filename)
                            with open(plot_path, "wb") as file:
                                pickle.dump(plot, file)
                                plot_paths.append(plot_path)
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Model training failed {e}",
                    ) from e
                try:
                    paths = plot_paths + [None] * (4 - len(plot_paths))
                    (
                        run.plot_history_path,
                        run.plot_slice_path,
                        run.plot_contour_path,
                        run.plot_importance_path,
                    ) = paths[:4]
                    db.commit()
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Hyperparameter plot path saving failed {e}",
                    ) from e

                try:
                    model_metrics = factory.evaluate(x, y, metrics)
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        "Metrics calculation failed",
                    ) from e

                run.train_metrics = model_metrics["train"]
                run.validation_metrics = model_metrics["validation"]
                run.test_metrics = model_metrics["test"]

                try:
                    run_path = os.path.join(config["RUNS_PATH"], str(run.id))
                    model.save(run_path)
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        "Model saving failed",
                    ) from e

                try:
                    run.run_path = run_path
                    db.commit()
                except exc.SQLAlchemyError as e:
                    log.exception(e)
                    run.set_status_as_error()
                    db.commit()
                    raise JobError(
                        "Connection with the database failed",
                    ) from e
                try:
                    run.set_status_as_finished()
                    db.commit()
                except exc.SQLAlchemyError as e:
                    log.exception(e)
                    raise JobError(
                        "Connection with the database failed",
                    ) from e
            except Exception as e:
                run.set_status_as_error()
                db.commit()
                raise e
            finally:
                gc.collect()

import gc
import json
import logging
import os
import pickle
from typing import List

from kink import inject
from sqlalchemy import exc
from sqlalchemy.orm import Session

from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    load_dataset,
    prepare_for_experiment,
    select_columns,
    split_dataset,
)
from DashAI.back.dependencies.database.models import Dataset, Experiment, Run
from DashAI.back.dependencies.registry import ComponentRegistry
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

    def set_status_as_delivered(self) -> None:
        """Set the status of the job as delivered."""
        run_id: int = self.kwargs["run_id"]
        db: Session = self.kwargs["db"]

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
    async def run(
        self,
        component_registry: ComponentRegistry = lambda di: di["component_registry"],
        config=lambda di: di["config"],
    ) -> None:
        from DashAI.back.api.api_v1.endpoints.components import (
            _intersect_component_lists,
        )

        # Get the necessary parameters
        run_id: int = self.kwargs["run_id"]
        db: Session = self.kwargs["db"]

        run: Run = db.get(Run, run_id)
        try:
            # Get the experiment, dataset, task, metrics and splits
            experiment: Experiment = db.get(Experiment, run.experiment_id)
            if not experiment:
                raise JobError(f"Experiment {run.experiment_id} does not exist in DB.")
            dataset: Dataset = db.get(Dataset, experiment.dataset_id)
            if not dataset:
                raise JobError(f"Dataset {experiment.dataset_id} does not exist in DB.")

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
                    f"Unable to find Task with name {experiment.task_name} in registry",
                ) from e

            try:
                # Get all the metrics
                all_metrics = {
                    component_dict["name"]: component_dict
                    for component_dict in component_registry.get_components_by_types(
                        select="Metric"
                    )
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
                n_labels = None
                if experiment.task_name in [
                    "TextClassificationTask",
                    "TabularClassificationTask",
                    "ImageClassificationTask",
                ]:
                    all_classes = prepared_dataset.unique(experiment.output_columns[0])
                    n_labels = len(all_classes)

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
            if experiment.task_name in [
                "TextClassificationTask",
                "TabularClassificationTask",
                "RegressionTask",
            ]:
                try:
                    # Optimizer configuration
                    run_optimizer_class = component_registry[run.optimizer_name][
                        "class"
                    ]
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Unable to find Model with name {run.optimizer_name} in "
                        "registry.",
                    ) from e
                if run.goal_metric != "":
                    try:
                        goal_metric = selected_metrics[run.goal_metric]
                    except Exception as e:
                        log.exception(e)
                        raise JobError(
                            "Metric is not compatible with the Task",
                        ) from e
                    try:
                        optimizer: BaseOptimizer = run_optimizer_class(
                            **run.optimizer_parameters
                        )
                    except Exception as e:
                        log.exception(e)
                        raise JobError(
                            "Optimizer parameters not compatible with the optimizer",
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
                if not run_optimizable_parameters:
                    model.fit(x["train"], y["train"])
                else:
                    optimizer.optimize(
                        model,
                        x,
                        y,
                        run_optimizable_parameters,
                        goal_metric,
                        experiment.task_name,
                    )
                    model = optimizer.get_model()
                    # Generate hyperparameter plot
                    trials = optimizer.get_trials_values()
                    plot_filenames, plots = optimizer.create_plots(
                        trials, run_id, n_params=len(run_optimizable_parameters)
                    )
                    plot_paths = []
                    for filename, plot in zip(plot_filenames, plots):
                        plot_path = os.path.join(config["RUNS_PATH"], filename)
                        with open(plot_path, "wb") as file:
                            pickle.dump(plot, file)
                            plot_paths.append(plot_path)
            except Exception as e:
                log.exception(e)
                raise JobError(
                    "Model training failed",
                ) from e
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
        except Exception as e:
            run.set_status_as_error()
            db.commit()
            raise e
        finally:
            gc.collect()

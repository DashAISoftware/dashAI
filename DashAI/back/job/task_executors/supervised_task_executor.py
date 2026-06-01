"""Executor for the current supervised X/y model flow."""

import json
import logging
import os
import pickle

from sqlalchemy.orm.attributes import flag_modified

from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.dataloaders.classes.dashai_dataset import (
    prepare_for_model_session,
    select_columns,
    split_dataset,
)
from DashAI.back.dependencies.database.models import Metric
from DashAI.back.job.base_job import JobError
from DashAI.back.job.model_job_context import ModelJobContext
from DashAI.back.job.task_executors.base_task_executor import BaseTaskExecutor
from DashAI.back.metrics.base_metric import BaseMetric
from DashAI.back.models.base_model import BaseModel
from DashAI.back.models.model_factory import ModelFactory
from DashAI.back.optimizers.base_optimizer import BaseOptimizer

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class SupervisedTaskExecutor(BaseTaskExecutor):
    """Execute the existing supervised training/evaluation flow."""

    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "RegressionTask",
        "TranslationTask",
    ]

    def execute(self, context: ModelJobContext) -> BaseModel:
        """Run the supervised X/y flow currently used by ModelJob."""

        component_registry = context.component_registry
        db = context.db
        run = context.run
        model_session = context.model_session
        task = context.task
        dataset_record = context.dataset_record
        loaded_dataset = context.dataset
        config = context.config

        try:
            train_metrics: list[type[BaseMetric]] = [
                component_registry[m]["class"] for m in model_session.train_metrics
            ]
            validation_metrics: list[type[BaseMetric]] = [
                component_registry[m]["class"] for m in model_session.validation_metrics
            ]
            test_metrics: list[type[BaseMetric]] = [
                component_registry[m]["class"] for m in model_session.test_metrics
            ]
        except Exception as e:
            log.exception(e)
            raise JobError(
                "Unable to find metrics associated with "
                f"Task {model_session.task_name} in registry",
            ) from e

        try:
            prepared_dataset = task.prepare_for_task(
                dataset=loaded_dataset,
                input_columns=model_session.input_columns,
                output_columns=model_session.output_columns,
            )
            n_labels = task.num_labels(
                prepared_dataset, model_session.output_columns[0]
            )

            splits = json.loads(model_session.splits)
            prepared_dataset, splits = prepare_for_model_session(
                dataset=prepared_dataset,
                splits=splits,
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
                f"""Can not prepare Dataset {dataset_record.id}
                for Task {model_session.task_name}""",
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
                run_model_class,
                run.parameters,
                run.id,
                x,
                y,
                train_metrics,
                validation_metrics,
                test_metrics,
                n_labels=n_labels,
            )
            model: BaseModel = factory.model
            run_optimizable_parameters = factory.optimizable_parameters
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Unable to instantiate model using run {run.id}",
            ) from e

        try:
            goal_metric = None
            if run_optimizable_parameters:
                goal_metric = component_registry[run.goal_metric]
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Metric is not compatible with the Task. {e}",
            ) from e

        try:
            optimizer: BaseOptimizer | None = None
            if run_optimizable_parameters:
                run_optimizer_class = component_registry[run.optimizer_name]["class"]
                optimizer = run_optimizer_class(**run.optimizer_parameters)
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Error instantiating optimizer {run.optimizer_name}, {e}",
            ) from e

        try:
            plot_paths = []
            if not run_optimizable_parameters:
                model.train(x["train"], y["train"], x["validation"], y["validation"])
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
                best_params = optimizer.get_best_params()

                old_parameters = run.parameters.copy()
                updated_parameters = factory.update_parameters(
                    old_parameters, best_params
                )

                run.parameters = updated_parameters
                flag_modified(run, "parameters")
                db.commit()

                trials = optimizer.get_trials_values()
                plot_filenames, plots = optimizer.create_plots(
                    trials,
                    run.id,
                    n_params=len(run_optimizable_parameters),
                    goal_metric=goal_metric,
                )
                for filename, plot in zip(plot_filenames, plots, strict=False):
                    plot_path = os.path.join(config["RUNS_PATH"], filename)
                    with open(plot_path, "wb") as file:
                        pickle.dump(plot, file)
                        plot_paths.append(plot_path)
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Model training failed {e}",
            ) from e

        self._save_optimizer_plot_paths(run, plot_paths, db)
        self._calculate_last_metrics(run, model, db)
        return model

    def _save_optimizer_plot_paths(self, run, plot_paths: list[str], db) -> None:
        """Save optimizer plot paths generated by the supervised flow."""
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

    def _calculate_last_metrics(self, run, model: BaseModel, db) -> None:
        """Calculate missing LAST metrics for all supervised splits."""

        try:
            last_train_metric = (
                db.query(Metric)
                .filter_by(run_id=run.id, split="TRAIN", level="LAST")
                .first()
            )
            if not last_train_metric:
                model.calculate_metrics(
                    split=SplitEnum.TRAIN,
                    level=LevelEnum.LAST,
                )
            last_val_metric = (
                db.query(Metric)
                .filter_by(run_id=run.id, split="VALIDATION", level="LAST")
                .first()
            )
            if not last_val_metric:
                model.calculate_metrics(
                    split=SplitEnum.VALIDATION,
                    level=LevelEnum.LAST,
                )
            last_test_metric = (
                db.query(Metric)
                .filter_by(run_id=run.id, split="TEST", level="LAST")
                .first()
            )
            if not last_test_metric:
                model.calculate_metrics(
                    split=SplitEnum.TEST,
                    level=LevelEnum.LAST,
                )
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Metric calculation failed {e}",
            ) from e

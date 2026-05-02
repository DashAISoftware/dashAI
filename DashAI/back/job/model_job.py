import logging
from typing import TYPE_CHECKING, Any, Dict, List

from kink import inject
from sqlalchemy import exc

from DashAI.back.dependencies.database.models import Dataset, ModelSession, Run
from DashAI.back.evaluation.base_evaluation_strategy import BaseEvaluationStrategy
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.metrics.base_metric import BaseMetric
from DashAI.back.models.base_model import BaseModel
from DashAI.back.models.model_factory import ModelFactory
from DashAI.back.optimizers.base_optimizer import BaseOptimizer
from DashAI.back.splitters.base_splitter import BaseSplitter
from DashAI.back.tasks.base_task import BaseTask

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class ModelJob(BaseJob):
    """ModelJob class to run the model training."""

    @inject
    def set_status_as_delivered(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
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
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
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
        import gc
        import json
        import os

        from kink import di

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
                try:
                    # Get the dataset and components prepared for the model training
                    preparation_results = self._prepare_dataset_and_components(
                        run_id=run_id, db=db, component_registry=component_registry
                    )
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Error preparing dataset and components for run {run_id}: {e}",
                    ) from e

                try:
                    # Get splits from the splitter
                    splitter: BaseSplitter = preparation_results["splitter"]
                    print("SPLITTER", splitter)
                    # Get the dataset splits between input columns and output column
                    X, Y = preparation_results["X"], preparation_results["Y"]
                    print("X", X)
                    print("Y", Y)

                    # Get x,y but now splitted with train, validation and test indexes
                    # each one, and the indexes used for the splits
                    x, y, splits = splitter.split(X, Y)
                    print("SPLITS", splits)

                    # save the obtained splits into the database
                    run.split_indexes = json.dumps(splits)
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Error splitting the dataset for run {run_id}: {e}",
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

                    evaluation_estrategy: BaseEvaluationStrategy = preparation_results[
                        "evaluation_strategy"
                    ]
                    factory: ModelFactory = preparation_results["factory"]

                    model, plot_paths = evaluation_estrategy.execute(
                        x=x,
                        y=y,
                        factory=factory,
                        run=run,
                        db=db,
                    )
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Model training and evaluation failed {e}",
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

    def _prepare_dataset_and_components(
        self, run_id: int, db, component_registry
    ) -> Dict[str, Any]:
        """Prepare the dataset and components for the model training."""

        import json

        from DashAI.back.dataloaders.classes.dashai_dataset import (
            load_dataset,
            select_columns,
        )

        run: Run = db.get(Run, run_id)

        # Get the model session and dataset from the database
        model_session: ModelSession = db.get(ModelSession, run.model_session_id)
        if not model_session:
            raise JobError(
                f"Model session {run.model_session_id} does not exist in DB."
            )

        dataset: Dataset = db.get(Dataset, model_session.dataset_id)
        if not dataset:
            raise JobError(f"Dataset {model_session.dataset_id} does not exist in DB.")

        try:
            # Load dataset from the file path
            loaded_dataset: "DashAIDataset" = load_dataset(
                f"{dataset.file_path}/dataset"
            )
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Can not load dataset from path {dataset.file_path}",
            ) from e

        try:
            # Get task from model session
            task: BaseTask = component_registry[model_session.task_name]["class"]()
        except Exception as e:
            log.exception(e)
            raise JobError(
                (
                    f"Unable to find Task with name {model_session.task_name} "
                    "in registry"
                ),
            ) from e

        try:
            # Prepare dataset for the task and get number of labels of the task
            prepared_dataset = task.prepare_for_task(
                dataset=loaded_dataset,
                input_columns=model_session.input_columns,
                output_columns=model_session.output_columns,
            )
            n_labels = task.num_labels(
                prepared_dataset, model_session.output_columns[0]
            )
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"""Can not prepare Dataset {dataset.id}
                for Task {model_session.task_name}""",
            ) from e

        try:
            # Divide the dataset into two datasets:
            # one with the input columns and another with the output column
            X, Y = select_columns(
                loaded_dataset,
                model_session.input_columns,
                model_session.output_columns,
            )
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Error selecting input and output columns from dataset {dataset.id}",
            ) from e

        try:
            # Get splits data from model session
            splits_data = json.loads(model_session.splits)
            if run.split_indexes:
                splits_data["splitted_indexes"] = json.loads(run.split_indexes)
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Can not load splits data from model session {model_session.id}",
            ) from e

        try:
            # Get the splitter class from the registry and split the dataset
            splitter_name = splits_data.get("splitter_name", None)
            splitter: BaseSplitter = component_registry[splitter_name]["class"](
                splits_data=splits_data,
            )
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"""Unable to find Splitter with name
                {splitter_name} in registry.""",
            ) from e

        try:
            # Get the inner splitter if defined for nested cross validation
            inner_splits_data = splits_data.get("inner_splitter_data", None)
            inner_splitter: BaseSplitter = None

            if inner_splits_data:
                inner_splitter_name = inner_splits_data.get("splitter_name", None)
                inner_splitter: BaseSplitter = component_registry[inner_splitter_name][
                    "class"
                ](
                    splits_data=inner_splits_data,
                )
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"""Unable to find inner Splitter with name
                {inner_splitter_name} in registry.""",
            ) from e

        try:
            # Get metrics from model session
            train_metrics: List[BaseMetric] = [
                component_registry[m]["class"] for m in model_session.train_metrics
            ]
            validation_metrics: List[BaseMetric] = [
                component_registry[m]["class"] for m in model_session.validation_metrics
            ]
            test_metrics: List[BaseMetric] = [
                component_registry[m]["class"] for m in model_session.test_metrics
            ]
        except Exception as e:
            log.exception(e)
            raise JobError(
                "Unable to find metrics associated with"
                f"Task {model_session.task_name} in registry",
            ) from e

        try:
            # Get the model class from the registry
            run_model_class = component_registry[run.model_name]["class"]
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Unable to find Model with name {run.model_name} in registry.",
            ) from e

        try:
            # Get the optimizer if defined
            optimizer: BaseOptimizer = None
            goal_metric = None

            if run.optimizer_name:
                run_optimizer_class = component_registry[run.optimizer_name]["class"]
                optimizer: BaseOptimizer = run_optimizer_class(
                    **run.optimizer_parameters
                )
                goal_metric = component_registry[run.goal_metric]
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Error instantiating optimizer {run.optimizer_name}, {e}",
            ) from e

        try:
            # Instantiate the model using the ModelFactory
            # and get the optimizable parameters
            factory = ModelFactory(
                model=run_model_class,
                params=run.parameters,
                run_id=run_id,
                train_metrics=train_metrics,
                validation_metrics=validation_metrics,
                test_metrics=test_metrics,
                n_labels=n_labels,
            )

            model: BaseModel = factory.model
            run_optimizable_parameters = factory.optimizable_parameters
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Unable to instantiate model using run {run_id}",
            ) from e

        try:
            # Get the evaluation strategy for the model session
            evaluation_strategy: BaseEvaluationStrategy = component_registry[
                model_session.evaluation_strategy
            ]["class"](
                model=model,
                optimizer=optimizer,
                run_optimizable_parameters=run_optimizable_parameters,
                goal_metric=goal_metric,
                inner_splitter=inner_splitter,
            )
        except Exception as e:
            log.exception(e)
            raise JobError(
                # string is too long, so it has to be split in two
                f"""Unable to find Evaluation Strategy with name
                {model_session.evaluation_strategy} in registry.""",
            ) from e

        return {
            "X": X,
            "Y": Y,
            "splits_data": splits_data,
            "factory": factory,
            "splitter": splitter,
            "evaluation_strategy": evaluation_strategy,
        }

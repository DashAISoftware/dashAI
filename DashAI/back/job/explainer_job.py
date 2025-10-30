import json
import logging
import os
import pickle
from typing import Any, Dict, Tuple

from datasets import DatasetDict
from kink import inject
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker

from DashAI.back.dataloaders.classes.dashai_dataset import (
    load_dataset,
    prepare_for_experiment,
    select_columns,
    split_dataset,
)
from DashAI.back.dependencies.database.models import (
    Dataset,
    Experiment,
    GlobalExplainer,
    LocalExplainer,
    Run,
)
from DashAI.back.explainability.global_explainer import BaseGlobalExplainer
from DashAI.back.explainability.local_explainer import BaseLocalExplainer
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.models import BaseModel
from DashAI.back.tasks import BaseTask

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class ExplainerJob(BaseJob):
    """ExplainerJob class to calculate explanations."""

    @inject
    def set_status_as_delivered(
        self, session_factory: sessionmaker = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the job as delivered."""
        explainer_id: int = self.kwargs["explainer_id"]
        explainer_scope: str = self.kwargs["explainer_scope"]

        with session_factory() as db:
            if explainer_scope == "global":
                explainer: GlobalExplainer = db.get(GlobalExplainer, explainer_id)
            elif explainer_scope == "local":
                explainer: LocalExplainer = db.get(LocalExplainer, explainer_id)
            else:
                raise JobError(f"{explainer_scope} is an invalid explainer type")

            if not explainer:
                raise JobError(
                    f"Explainer with id {explainer_id} does not exist in DB."
                )
            try:
                explainer.set_status_as_delivered()
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
        """Set the status of the explainer as error."""
        explainer_id: int = self.kwargs.get("explainer_id")
        explainer_scope: str = self.kwargs.get("explainer_scope", "")

        if explainer_id is None:
            return

        with session_factory() as db:
            try:
                if explainer_scope == "global":
                    explainer = db.get(GlobalExplainer, explainer_id)
                elif explainer_scope == "local":
                    explainer = db.get(LocalExplainer, explainer_id)
                else:
                    return

                if explainer:
                    explainer.set_status_as_error()
                    db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)

    @inject
    def get_job_name(self) -> str:
        """Get a descriptive name for the job."""
        explainer_id = self.kwargs.get("explainer_id")
        explainer_scope = self.kwargs.get("explainer_scope", "")

        if not explainer_id:
            return f"{explainer_scope.capitalize()} Explanation"

        from kink import di

        session_factory = di["session_factory"]

        try:
            with session_factory() as db:
                if explainer_scope == "global":
                    explainer = db.get(GlobalExplainer, explainer_id)
                elif explainer_scope == "local":
                    explainer = db.get(LocalExplainer, explainer_id)
                else:
                    return (
                        f"{explainer_scope.capitalize()} Explanation ({explainer_id})"
                    )

                if explainer and explainer.name:
                    return f"Explain: {explainer.name}"
                if explainer and explainer.explainer_name:
                    return f"Explain: {explainer.explainer_name.split('.')[-1]}"
        except Exception:
            pass

        return f"{explainer_scope.capitalize()} Explanation ({explainer_id})"

    @inject
    def _generate_global_explanation(
        self,
        explainer: BaseGlobalExplainer,
        dataset=Tuple[DatasetDict, DatasetDict],
    ) -> None:
        from kink import di

        explainer_id: int = self.kwargs["explainer_id"]
        session_factory = di["session_factory"]
        config = di["config"]
        with session_factory() as db:
            try:
                explanation = explainer.explain(dataset)
                plot = explainer.plot(explanation)
            except Exception as e:
                log.exception(e)
                raise JobError(
                    "Failed to generate the explanation",
                ) from e
            try:
                explanation_filename = f"global_explanation_{explainer_id}.pickle"
                explanation_path = os.path.join(
                    config["EXPLANATIONS_PATH"], explanation_filename
                )
                with open(explanation_path, "wb") as file:
                    pickle.dump(explanation, file)

                plot_filename = f"global_explanation_plot_{explainer_id}.pickle"
                plot_path = os.path.join(config["EXPLANATIONS_PATH"], plot_filename)
                with open(plot_path, "wb") as file:
                    pickle.dump(plot, file)

            except Exception as e:
                log.exception(e)
                raise JobError(
                    "Explanation file saving failed",
                ) from e
            try:
                self.explainer_db.explanation_path = explanation_path
                self.explainer_db.plot_path = plot_path
                db.commit()
            except Exception as e:
                log.exception(e)
                raise JobError(
                    "Explanation path saving failed",
                ) from e

    @inject
    def _generate_local_explanation(
        self,
        explainer: BaseLocalExplainer,
        dataset: Tuple[DatasetDict, DatasetDict],
        splits: Dict[str, Any],
        task: BaseTask,
        same_dataset: bool,
    ) -> None:
        from kink import di

        explainer_id: int = self.kwargs["explainer_id"]
        session_factory = di["session_factory"]
        config = di["config"]

        explainer.fit(dataset, **self.explainer_db.fit_parameters)
        instance_id = self.explainer_db.dataset_id
        with session_factory() as db:
            instance: Dataset = db.get(Dataset, instance_id)
            if not instance:
                raise JobError(
                    f"Dataset {instance_id} to be explained does not exist in DB."
                )
            try:
                loaded_instance = load_dataset(f"{instance.file_path}/dataset")
            except Exception as e:
                log.exception(e)
                raise JobError(
                    f"Can not load instance from path {instance.file_path}",
                ) from e
            try:
                prepared_instance = task.prepare_for_task(
                    loaded_instance, outputs_columns=self.output_columns
                )

                split = self.explainer_db.scope.get("split")
                if split not in ["train", "test", "val", "all"]:
                    raise JobError(f"{split} is not a valid split")

                if split != "all":
                    if not same_dataset:
                        prepared_instance, splits = prepare_for_experiment(
                            dataset=prepared_instance,
                            splits=splits,
                            output_columns=self.output_columns,
                        )

                    prepared_instance = split_dataset(
                        prepared_instance,
                        train_indexes=splits["train_indexes"],
                        test_indexes=splits["test_indexes"],
                        val_indexes=splits["val_indexes"],
                    )[split]

                prepared_instance = prepared_instance.select(
                    range(
                        max(
                            1,
                            int(
                                prepared_instance.num_rows
                                * self.explainer_db.scope.get("percentage")
                                / 100
                            ),
                        ),
                    )
                )

                prepared_instance = DatasetDict({"train": prepared_instance})
                X, _ = select_columns(
                    prepared_instance,
                    self.input_columns,
                    self.output_columns,
                )
            except Exception as e:
                log.exception(e)
                raise JobError(
                    f"""Can not prepare Dataset with {instance_id}
                        to generate the local explanation.""",
                ) from e
            try:
                explanation = explainer.explain_instance(X)
                plots = explainer.plot(explanation)
            except Exception as e:
                log.exception(e)
                raise JobError(
                    "Failed to generate the explanation",
                ) from e
            try:
                explanation_filename = f"local_explanation_{explainer_id}.json"
                explanation_path = os.path.join(
                    config["EXPLANATIONS_PATH"], explanation_filename
                )
                with open(explanation_path, "wb") as file:
                    pickle.dump(explanation, file)

                plots_filename = f"local_explanation_plots_{explainer_id}.pickle"
                plots_path = os.path.join(config["EXPLANATIONS_PATH"], plots_filename)
                with open(plots_path, "wb") as file:
                    pickle.dump(plots, file)

            except Exception as e:
                log.exception(e)
                raise JobError(
                    "Explanation file saving failed",
                ) from e
            try:
                self.explainer_db.explanation_path = explanation_path
                self.explainer_db.plots_path = plots_path
                db.commit()
            except Exception as e:
                log.exception(e)
                raise JobError(
                    "Explanation path saving failed",
                ) from e

    @inject
    def run(
        self,
    ) -> None:
        from kink import di

        component_registry = di["component_registry"]
        session_factory = di["session_factory"]

        explainer_id: int = self.kwargs["explainer_id"]
        explainer_scope: str = self.kwargs["explainer_scope"]
        with session_factory() as db:
            if explainer_scope == "global":
                self.explainer_db: GlobalExplainer = db.get(
                    GlobalExplainer, explainer_id
                )
            elif explainer_scope == "local":
                self.explainer_db: LocalExplainer = db.get(LocalExplainer, explainer_id)
            else:
                raise JobError(f"{explainer_scope} is an invalid explainer type")

            try:
                run: Run = db.get(Run, self.explainer_db.run_id)
                if not run:
                    raise JobError(
                        f"Run {self.explainer_db.run_id} does not exist in DB."
                    )
                experiment: Experiment = db.get(Experiment, run.experiment_id)
                if not experiment:
                    raise JobError(
                        f"Experiment {run.experiment_id} does not exist in DB."
                    )
                dataset: Dataset = db.get(Dataset, experiment.dataset_id)
                if not dataset:
                    raise JobError(
                        f"Dataset {self.explainer_db.dataset_id} does not exist in DB."
                    )

                self.input_columns = experiment.input_columns
                self.output_columns = experiment.output_columns

                try:
                    run_model_class = component_registry[run.model_name]["class"]
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Unable to find Model with name {run.model_name} in registry.",
                    ) from e
                try:
                    model: BaseModel = run_model_class(**run.parameters)
                except Exception as e:
                    log.exception(e)
                    raise JobError("Unable to instantiate model") from e
                try:
                    trained_model = model.load(run.run_path)
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Can not load model from path {run.run_path}"
                    ) from e
                try:
                    explainer_class = component_registry[
                        self.explainer_db.explainer_name
                    ]["class"]
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"""Unable to find the {explainer_scope} explainer with name
                            {self.explainer_db.explainer_name} in registry.""",
                    ) from e

                try:
                    explainer = explainer_class(
                        model=trained_model, **self.explainer_db.parameters
                    )
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Unable to instantiate {explainer_scope} explainer.",
                    ) from e
                try:
                    loaded_dataset: DatasetDict = load_dataset(
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
                    splits = json.loads(run.split_indexes)
                    loaded_dataset = split_dataset(
                        loaded_dataset,
                        train_indexes=splits["train_indexes"],
                        test_indexes=splits["test_indexes"],
                        val_indexes=splits["val_indexes"],
                    )

                    prepared_dataset: DatasetDict = task.prepare_for_task(
                        datasetdict=loaded_dataset,
                        outputs_columns=self.output_columns,
                    )
                    data = select_columns(
                        prepared_dataset,
                        self.input_columns,
                        self.output_columns,
                    )

                    data_x = split_dataset(
                        data[0],
                        train_indexes=splits["train_indexes"],
                        test_indexes=splits["test_indexes"],
                        val_indexes=splits["val_indexes"],
                    )
                    data_y = split_dataset(
                        data[1],
                        train_indexes=splits["train_indexes"],
                        test_indexes=splits["test_indexes"],
                        val_indexes=splits["val_indexes"],
                    )

                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"""Can not prepare dataset {dataset.id} for the explanation""",
                    ) from e
                try:
                    self.explainer_db.set_status_as_started()
                    db.commit()
                except exc.SQLAlchemyError as e:
                    log.exception(e)
                    raise JobError(
                        "Connection with the database failed",
                    ) from e

                if explainer_scope == "global":
                    self._generate_global_explanation(
                        explainer=explainer, dataset=(data_x, data_y)
                    )

                elif explainer_scope == "local":
                    same_dataset = experiment.dataset_id == self.explainer_db.dataset_id
                    if not same_dataset:
                        splits = experiment.splits

                    self._generate_local_explanation(
                        explainer=explainer,
                        dataset=(data_x, data_y),
                        splits=splits,
                        task=task,
                        same_dataset=same_dataset,
                    )
                else:
                    raise JobError(f"{explainer_scope} is an invalid explainer type")

                self.explainer_db.set_status_as_finished()
                db.commit()

            except Exception as e:
                self.explainer_db.set_status_as_error()
                db.commit()
                raise e

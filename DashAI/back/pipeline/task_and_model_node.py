import logging
import os
import shutil
from typing import Any, Dict

from kink import di

from DashAI.back.config import DefaultSettings
from DashAI.back.dataloaders.classes.dashai_dataset import (
    prepare_for_model_session,
    select_columns,
    split_dataset,
)
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.models.base_model import BaseModel
from DashAI.back.models.model_factory import ModelFactory
from DashAI.back.tasks.base_task import BaseTask

log = logging.getLogger(__name__)


class TaskAndModel(BaseJob):
    """Pipeline node that selects the ML task and model, and trains it.

    It expects the split data to already be available in the pipeline
    context (populated by the *SplitData* node).

    Parameters
    ----------
    task : str
        Name of the ML task (e.g. ``"TabularClassificationTask"``).
    model : str
        Name of the model to train.
    parameters : Dict[str, Any] | None
        Model-specific hyper-parameters.
    """

    def __init__(
        self,
        task: str,
        model: str,
        parameters: Dict[str, Any] = None,
    ) -> None:
        super().__init__(
            kwargs={
                "task": task,
                "model": model,
                "parameters": parameters,
            },
        )
        self.task = task
        self.model = model
        self.parameters = parameters

    # -- BaseJob interface ---------------------------------------------------

    def set_status_as_delivered(self) -> None:
        log.debug("TaskAndModel executed successfully.")

    def set_status_as_error(self) -> None:
        log.error("TaskAndModel encountered an error.")

    def get_job_name(self) -> str:
        return f"TaskAndModel: {self.model}"

    # -- Execution -----------------------------------------------------------

    async def run(
        self,
        context: Dict[str, Any],
        component_registry: ComponentRegistry = lambda di: di["component_registry"],
    ) -> Dict[str, Any]:
        """Train a model and save it to disk.

        Reads from ``context``:
        * ``input_columns``, ``output_columns`` – populated by *SplitData*
        * ``split_ratios`` – populated by *SplitData*
        * ``dataset`` – the raw dataset
        * ``pipeline_id``

        Writes to ``context``:
        * ``model_class``, ``model_path``, ``model_name``, ``task_name``
        * ``trained_x``, ``trained_y`` – datasets used during training
          (needed by the *Metrics* node)
        * ``x_splits``, ``y_splits``, ``n_labels``
        """
        pipeline_id = context["pipeline_id"]
        dataset = context["dataset"]
        input_columns_names = context["input_columns"]
        output_columns_names = context["output_columns"]
        split_ratios = context["split_ratios"]

        context["task_name"] = self.task
        context["model_name"] = self.model

        # --- Resolve task and prepare dataset ---
        try:
            task_class: BaseTask = component_registry(di)[self.task]["class"]
            task_instance = task_class()

            prepared_dataset = task_instance.prepare_for_task(
                dataset=dataset,
                input_columns=input_columns_names,
                output_columns=output_columns_names,
            )

            n_labels = None
            if self.task in [
                "TextClassificationTask",
                "TabularClassificationTask",
                "ImageClassificationTask",
            ]:
                all_classes = prepared_dataset.unique(output_columns_names[0])
                n_labels = len(all_classes)

            prepared_dataset, splits = prepare_for_model_session(
                dataset=prepared_dataset,
                splits=split_ratios,
                output_columns=output_columns_names,
            )

            x, y = select_columns(
                prepared_dataset, input_columns_names, output_columns_names
            )
            x_splits = split_dataset(x)
            y_splits = split_dataset(y)

            context["x_splits"] = x_splits
            context["y_splits"] = y_splits
            context["splits"] = splits
            context["n_labels"] = n_labels
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Cannot prepare / split dataset for task {self.task}",
            ) from e

        # --- Resolve model class from registry ---
        try:
            model_class = component_registry(di)[self.model]["class"]
            context["model_class"] = model_class
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Unable to find Model with name {self.model} in registry.",
            ) from e

        # --- Instantiate model via factory ---
        try:
            factory = ModelFactory(model_class, self.parameters, n_labels=n_labels)
            model: BaseModel = factory.model
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Unable to instantiate model {self.model}",
            ) from e

        # --- Train ---
        try:
            if hasattr(model, "train") and callable(model.train):
                model.train(
                    x_splits["train"],
                    y_splits["train"],
                    x_splits.get("validation"),
                    y_splits.get("validation"),
                )
                x = x_splits
                y = y_splits
            elif hasattr(model, "fit") and callable(model.fit):
                x = {}
                y = {}
                for split in ["train", "validation", "test"]:
                    if split in x_splits:
                        x[split] = x_splits[split].to_pandas().values
                    if split in y_splits:
                        y[split] = y_splits[split].to_pandas().values.ravel()
                model.fit(x["train"], y["train"])
            else:
                raise AttributeError(
                    f"Model {model_class} has neither 'train' nor 'fit' method"
                )
        except Exception as e:
            log.exception(e)
            raise JobError("Model training failed") from e

        # --- Save trained model ---
        try:
            settings = DefaultSettings()
            sqlite_local = os.path.expanduser(settings.LOCAL_PATH)
            train_root = os.path.join(sqlite_local, "pipelines", "train")
            os.makedirs(train_root, exist_ok=True)

            node_id = context.get("_node_id", "TaskAndModel")

            path = os.path.join(train_root, str(pipeline_id))

            # Backward-compatibility: older runs may have saved a file in
            # `train/<pipeline_id>`. This node now expects that location to be
            # a directory, so replace legacy file with a directory.
            if os.path.isfile(path):
                log.warning("Replacing legacy model file path with directory: %s", path)
                os.remove(path)

            os.makedirs(path, exist_ok=True)

            node_path = os.path.join(path, str(node_id))
            os.makedirs(node_path, exist_ok=True)
            model_path = os.path.join(node_path, "model")

            # Ensure clean overwrite when retraining same pipeline id.
            if os.path.isdir(model_path):
                shutil.rmtree(model_path)
            elif os.path.isfile(model_path):
                os.remove(model_path)

            model.save(model_path)
            context["model_path"] = model_path
        except Exception as e:
            log.exception(e)
            raise JobError("Model saving failed") from e

        # Keep references for the Metrics node
        context["trained_x"] = x
        context["trained_y"] = y
        context["model_factory"] = factory

        return {
            "task_and_model": {
                "task": self.task,
                "model": self.model,
                "parameters": self.parameters,
                "model_path": model_path,
                "input_columns": context.get("input_columns"),
            },
        }

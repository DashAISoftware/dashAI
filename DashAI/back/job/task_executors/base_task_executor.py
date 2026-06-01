"""Base executor for task-specific model flows."""

from abc import ABC, abstractmethod
from typing import Final

from DashAI.back.job.model_job_context import ModelJobContext
from DashAI.back.models.base_model import BaseModel


class BaseTaskExecutor(ABC):
    """Base class for task-specific execution flows.

    A TaskExecutor contains the operational logic required to run a model
    according to a task contract. ModelJob is responsible for loading the
    common runtime context, while each executor decides how to prepare data,
    train the model, evaluate metrics, and persist task-specific results.

    Executors are internal job-layer components. They are not user-facing
    models, tasks, or metrics.
    """

    TYPE: Final[str] = "TaskExecutor"

    @abstractmethod
    def execute(self, context: ModelJobContext) -> BaseModel:
        """Execute the task-specific training and evaluation flow.

        Implementations prepare the dataset, train the selected model, calculate
        the metrics required by the task, and return the trained model so ModelJob
        can persist it using the common saving flow.
        """
        raise NotImplementedError

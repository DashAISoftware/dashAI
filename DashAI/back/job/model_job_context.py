"""Shared runtime context for model jobs."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
    from DashAI.back.dependencies.database.models import Dataset, ModelSession, Run
    from DashAI.back.tasks.base_task import BaseTask


@dataclass
class ModelJobContext:
    """Data required by a task-specific model job executor.

    This object groups values that used to live as local variables inside
    ``ModelJob.run``. It is intentionally internal to the job layer; it is not a
    user-facing DashAI component.
    """

    run: "Run"
    model_session: "ModelSession"
    dataset_record: "Dataset"
    dataset: "DashAIDataset"
    task: "BaseTask"
    component_registry: Any
    db: Any
    config: dict

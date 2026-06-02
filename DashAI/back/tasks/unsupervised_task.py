"""Base task for unsupervised model."""

from DashAI.back.tasks.base_task import BaseTask


class UnsupervisedTask(BaseTask):
    """Base class for tasks trained without target columns."""

    REQUIRES_TARGET = False
    SESSION_CONFIG_SCHEMA = {
        "split_strategy": "none",
        "supports_shuffle": False,
        "supports_stratify": False,
    }

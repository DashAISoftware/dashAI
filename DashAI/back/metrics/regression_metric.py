from typing import Tuple

import numpy as np

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.metrics.base_metric import BaseMetric


class RegressionMetric(BaseMetric):
    """Class for metrics associated with regression models."""

    COMPATIBLE_COMPONENTS = ["RegressionTask"]


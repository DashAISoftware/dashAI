from typing import Tuple

import numpy as np

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.metrics.base_metric import BaseMetric


class ClassificationMetric(BaseMetric):
    """Class for metrics associated to classification models."""

    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "ImageClassificationTask",
        "TextClassificationTask",
    ]

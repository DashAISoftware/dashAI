from typing import TYPE_CHECKING, List

import numpy as np

from DashAI.back.tasks.base_task import BaseTask
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.dashai_value import DashAIValue

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class ClassificationTask(BaseTask):
    """Base class for classification tasks."""

    COMPATIBLE_COMPONENTS = ["Accuracy", "F1", "Precision", "Recall"]

    metadata: dict = {
        "inputs_types": [DashAIValue],
        "outputs_types": [Categorical],
        "inputs_cardinality": "n",
        "outputs_cardinality": 1,
    }

    def process_predictions(
        self, dataset: "DashAIDataset", predictions: np.ndarray, output_column: str
    ) -> "np.ndarray":
        """Process the predictions to return the class labels.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset used for training
        predictions : np.ndarray
            Predictions from the model (probabilities for each class)
        output_column : str
            Output column

        Returns
        -------
        np.ndarray
            Processed predictions with class labels
        """
        from DashAI.back.dataloaders.classes.dashai_dataset import encode_labels

        predictions = np.argmax(predictions, axis=1)

        output_type = dataset.types.get(output_column)

        if isinstance(output_type, Categorical):
            return np.array([output_type.int2str(idx) for idx in predictions])
        else:
            # Fallback to old method if not categorical
            class_labels = encode_labels(dataset, output_column)
            return np.array(class_labels.int2str(predictions))

    def prepare_for_task(
        self,
        dataset: "DashAIDataset",
        input_columns: List[str],
        output_columns: List[str],
    ) -> "DashAIDataset":
        dashai_dataset = super().prepare_for_task(
            dataset, input_columns, output_columns
        )

        for column in output_columns:
            column_type = dashai_dataset.types.get(column)
            if isinstance(column_type, Categorical):
                continue
        return dashai_dataset

    def num_labels(self, dataset: "DashAIDataset", output_column: str) -> int | None:
        """Get the number of unique labels in the output column.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset used for training
        output_column : str
            Output column

        Returns
        -------
        int | None
            Number of unique labels or None if not applicable
        """
        from DashAI.back.dataloaders.classes.dashai_dataset import encode_labels

        class_labels = encode_labels(dataset, output_column)
        return len(class_labels.names)

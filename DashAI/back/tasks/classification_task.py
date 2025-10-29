import numpy as np

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset, encode_labels
from DashAI.back.tasks.base_task import BaseTask


class ClassificationTask(BaseTask):
    """Base class for classification tasks."""

    COMPATIBLE_COMPONENTS = ["Accuracy", "F1", "Precision", "Recall"]

    def process_predictions(
        self, dataset: DashAIDataset, predictions: np.ndarray, output_column: str
    ) -> np.ndarray:
        """Process the predictions to return the class labels.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset used for training
        predictions : np.ndarray
            Predictions from the model
        output_column : str
            Output column

        Returns
        -------
        np.ndarray
            Processed predictions
        """
        predictions = np.argmax(predictions, axis=1)
        class_labels = encode_labels(dataset, output_column)
        return np.array(class_labels.int2str(predictions))

    def num_labels(self, dataset: DashAIDataset, output_column: str) -> int | None:
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
        class_labels = encode_labels(dataset, output_column)
        return len(class_labels.names)

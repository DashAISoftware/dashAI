from typing import List, Union

import numpy as np
from datasets import ClassLabel, DatasetDict, Value

from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    encode_labels,
    to_dashai_dataset,
)
from DashAI.back.tasks.base_task import BaseTask


class ClassificationTask(BaseTask):
    """Base class for classification tasks."""

    COMPATIBLE_COMPONENTS = ["Accuracy", "F1", "Precision", "Recall"]
    DESCRIPTION: str = """
    Classification is a supervised machine learning task that involves predicting
    categorical labels for given input data. Models are trained on labeled datasets to
    learn patterns and relationships, enabling them to classify new, unseen instances
    into predefined categories accurately.
    """
    metadata: dict = {
        "inputs_types": [ClassLabel, Value],
        "outputs_types": [ClassLabel],
        "inputs_cardinality": "n",
        "outputs_cardinality": 1,
    }

    def prepare_for_task(
        self, datasetdict: Union[DatasetDict, DashAIDataset], outputs_columns: List[str]
    ) -> DashAIDataset:
        """Change the column types to suit the tabular classification task.

        A copy of the dataset is created.

        Parameters
        ----------
        datasetdict : Union[DatasetDict, DashAIDataset]
            Dataset to be changed

        Returns
        -------
        DashAIDataset
            Dataset with the new types
        """
        types = dict.fromkeys(outputs_columns, "Categorical")
        datasetdict = to_dashai_dataset(datasetdict)
        dataset = datasetdict.change_columns_type(types)
        return dataset

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

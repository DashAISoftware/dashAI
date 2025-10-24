"""Time Series Classification Task for DashAI."""

from typing import List, Union

import numpy as np
from datasets import ClassLabel, DatasetDict, Sequence, Value

from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    encode_labels,
    to_dashai_dataset,
)
from DashAI.back.tasks.classification_task import ClassificationTask


class TimeSeriesClassificationTask(ClassificationTask):
    """Task for time series classification with metadata.

    This task handles multivariate time series data (e.g., ECG signals)
    with optional metadata features for classification purposes.
    """

    DESCRIPTION: str = """
    Time series classification involves predicting categorical labels for 
    sequential data with temporal dependencies. This task supports multivariate 
    time series (multiple channels) along with additional metadata features.
    Models are trained to learn temporal patterns and relationships, enabling 
    accurate classification of time series instances.
    
    Common applications include:
    - ECG signal classification (detecting cardiac conditions)
    - Activity recognition from sensor data
    - Financial time series classification
    - Audio and speech classification
    """

    metadata: dict = {
        "inputs_types": [Sequence, Value],  # Time series + metadata
        "outputs_types": [ClassLabel],
        "inputs_cardinality": "n",  # Multiple inputs (time series + metadata columns)
        "outputs_cardinality": "n",  # Single classification output
    }

    def prepare_for_task(
        self, datasetdict: Union[DatasetDict, DashAIDataset], outputs_columns: List[str]
    ) -> DashAIDataset:
        """Change the column types to suit the time series classification task.

        This method converts the output columns to categorical type, which is
        required for classification tasks.

        Parameters
        ----------
        datasetdict : Union[DatasetDict, DashAIDataset]
            Dataset to be prepared. Should contain:
            - time_series column: multivariate time series data
            - metadata columns: additional features (e.g., age, sex)
            - target columns: classification labels

        outputs_columns : List[str]
            List of column names that will be used as classification targets

        Returns
        -------
        DashAIDataset
            Dataset with properly typed columns for the task
        """
        # Convert output columns to categorical type
        types = dict.fromkeys(outputs_columns, "Categorical")

        # Ensure we have a DashAIDataset
        datasetdict = to_dashai_dataset(datasetdict)

        # Change column types
        dataset = datasetdict.change_columns_type(types)

        return dataset

    def process_predictions(
        self, dataset: DashAIDataset, predictions: np.ndarray, output_column: str
    ) -> np.ndarray:
        """Process model predictions to return class labels.

        Converts probability distributions or logits to class labels
        using argmax, then maps indices back to original class names.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset used for training (contains label encoding information)
        predictions : np.ndarray
            Model predictions, typically probabilities of shape (n_samples, n_classes)
        output_column : str
            Name of the output column containing the labels

        Returns
        -------
        np.ndarray
            Array of predicted class labels (as strings)
        """
        # Get the predicted class indices (argmax over class probabilities)
        predictions = np.argmax(predictions, axis=1)

        # Get the label encoder to map indices back to original labels
        class_labels = encode_labels(dataset, output_column)

        # Convert indices to label strings
        return np.array(class_labels.int2str(predictions))

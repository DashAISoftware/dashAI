from typing import List

from datasets import DatasetDict, Value

from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.tasks.base_task import BaseTask


class RegressionTask(BaseTask):
    """Base class for regression tasks.

    Here you can change the methods provided by class Task.
    """

    DESCRIPTION: str = """
    Regression in machine learning involves predicting continuous values for
    structured data organized in tabular form (rows and columns).
    Models are trained to learn patterns and relationships in the data,
    enabling accurate prediction of new instances."""
    DISPLAY_NAME: str = "Regression"

    metadata: dict = {
        "inputs_types": [Value],
        "outputs_types": [Value],
        "inputs_cardinality": "n",
        "outputs_cardinality": 1,
    }

    def prepare_for_task(
        self, datasetdict: DatasetDict, outputs_columns: List[str]
    ) -> DashAIDataset:
        """Change the column types to suit the regression task.

        A copy of the dataset is created.

        Parameters
        ----------
        datasetdict : DatasetDict
            Dataset to be changed

        Returns
        -------
        DashAIDataset
            Dataset with the new types
        """
        return to_dashai_dataset(datasetdict)

    def process_predictions(self, dataset, predictions, output_column):
        """Process the predictions

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
        Processed predictions
        """
        return predictions

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
        return None

from typing import List

from datasets import DatasetDict, Value

from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.tasks.base_task import BaseTask


class MultiOutputRegressionTask(BaseTask):
    """Task for handling multi-output regression problems.

    Multi-output regression involves predicting multiple continuous outputs
    for each input sample. This task sets up the necessary metadata and
    processing functions to support training models that generate multiple
    outputs per sample.
    """

    DESCRIPTION: str = """
    Multi-output regression extends standard regression by predicting more
    than one continuous value per input instance. Each output dimension is
    treated as a separate regression target, and models can be trained to
    jointly predict all outputs, capturing correlations between them.
    """

    metadata = {
        "inputs_types": [Value],
        "outputs_types": [Value],
        "inputs_cardinality": "n",
        "outputs_cardinality": "n",
    }

    def prepare_for_task(
        self, datasetdict: DatasetDict, outputs_columns: List[str]
    ) -> DashAIDataset:
        """Change the column types to suit the multi-output regression task.

        Parameters
        ----------
        datasetdict : DatasetDict
            Dataset to be changed
        outputs_columns : List[str]
            Output columns for the task

        Returns
        -------
        DashAIDataset
            Dataset with the new types
        """
        return to_dashai_dataset(datasetdict)

    def process_predictions(self, dataset, predictions, output_column):
        """
        Process predictions for multi-output regression.

        For multi-output regression, we return the predictions as-is since they
        are already in the correct format (n_samples, n_outputs) from sklearn.

        Parameters
        ----------
        dataset : DashAIDataset
            The original dataset.
        predictions : np.ndarray
            Array 2D with predictions. Shape: (n_samples, n_outputs)
        output_column : str
            Not used directly for multi-output regression.

        Returns
        -------
        np.ndarray
            The predictions array as-is for compatibility with DashAI
            prediction pipeline.
        """
        # For multi-output, predictions are already in correct format
        # Shape should be (n_samples, n_outputs)
        print(
            f"[MultiOutputRegressionTask] Processing predictions with "
            f"shape: {predictions.shape}"
        )

        # Ensure predictions are 2D (which they should be from MultiOutputRegressor)
        if predictions.ndim == 1:
            predictions = predictions.reshape(-1, 1)

        return predictions

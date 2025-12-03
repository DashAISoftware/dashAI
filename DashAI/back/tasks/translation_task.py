"""DashAI Translation Task."""

from typing import List, Union

from datasets import DatasetDict, Sequence, Value

from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.tasks.base_task import BaseTask


class TranslationTask(BaseTask):
    """Base class for translation task."""

    COMPATIBLE_COMPONENTS = ["Bleu", "Ter"]

    metadata: dict = {
        "inputs_types": [Value, Sequence],
        "outputs_types": [Value, Sequence],
        "inputs_cardinality": 1,
        "outputs_cardinality": 1,
    }

    DESCRIPTION: str = """
    The translation task is natural language processing (NLP) task that involves
    converting text or speech from one language into another language while
    preserving the meaning and context.
    """
    DISPLAY_NAME: str = "Translation"

    def prepare_for_task(
        self, datasetdict: Union[DatasetDict, DashAIDataset], outputs_columns: List[str]
    ) -> DashAIDataset:
        """Change the column types to suit the tabular classification task.

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

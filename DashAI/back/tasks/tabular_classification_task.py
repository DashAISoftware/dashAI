from typing import List, Union

from datasets import ClassLabel, DatasetDict, Value

from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.tasks.classification_task import ClassificationTask
from DashAI.back.tasks.base_task import BaseTask
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.value_types import Float, Integer


class TabularClassificationTask(ClassificationTask):
    """Base class for tabular classification tasks.

    Here you can change the methods provided by class Task.
    """

    DESCRIPTION: str = """
    Tabular classification in machine learning involves predicting categorical
    labels for structured data organized in tabular form (rows and columns).
    Models are trained to learn patterns and relationships in the data, enabling
    accurate classification of new instances."""
    metadata: dict = {
        "inputs_types": [ClassLabel, Value],
        "outputs_types": [ClassLabel],
        "inputs_cardinality": "n",
        "outputs_cardinality": 1,
    }

    #Now, categorical encoding is a responsability of the model if needed
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

        return to_dashai_dataset(datasetdict)

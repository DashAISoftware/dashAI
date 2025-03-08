from typing import List, Union

from datasets import ClassLabel, DatasetDict, Value

from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.tasks.base_task import BaseTask


class TabularClassificationTask(BaseTask):
    """Base class for tabular classification tasks.

    Here you can change the methods provided by class Task.
    """

    COMPATIBLE_COMPONENTS = ["Accuracy", "F1", "Precision", "Recall"]

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
        types = {column: "Categorical" for column in outputs_columns}
        datasetdict = to_dashai_dataset(datasetdict)
        dataset = datasetdict.change_columns_type(types)
        return dataset

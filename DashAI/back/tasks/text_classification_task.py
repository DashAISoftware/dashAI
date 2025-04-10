from typing import List, Union

from datasets import ClassLabel, DatasetDict, Value

from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.tasks.base_task import BaseTask


class TextClassificationTask(BaseTask):
    """Base class for Text Classification Task."""

    COMPATIBLE_COMPONENTS = ["Accuracy", "F1", "Precision", "Recall"]

    metadata: dict = {
        "inputs_types": [Value],
        "outputs_types": [ClassLabel],
        "inputs_cardinality": 1,
        "outputs_cardinality": 1,
    }

    DESCRIPTION: str = """
    Text classification is an essential Natural Language Processing (NLP) task that
    involves automatically assigning pre-defined categories or labels to text documents
    based on their content. It serves as the foundation for applications like sentiment
    analysis, spam filtering, topic classification, and document categorization.
    """

    def prepare_for_task(
        self, datasetdict: Union[DatasetDict, DashAIDataset], outputs_columns: List[str]
    ) -> DashAIDataset:
        """Change the column types to suit the text classification task.

        A copy of the dataset is created.

        Parameters
        ----------
        datasetdict : DatasetDict
            Dataset to be changed

        Returns
        -------
        DatasetDict
            Dataset with the new types
        """
        types = {column: "Categorical" for column in outputs_columns}
        datasetdict = to_dashai_dataset(datasetdict)
        dataset = datasetdict.change_columns_type(types)
        return dataset

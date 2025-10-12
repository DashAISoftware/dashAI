from typing import List, Union

from datasets import DatasetDict

from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.tasks.classification_task import ClassificationTask
from DashAI.back.types.value_types import Text
from DashAI.back.types.categorical import Categorical


class TextClassificationTask(ClassificationTask):
    """Base class for Text Classification Task."""

    metadata: dict = {
        "inputs_types": [Text],
        "outputs_types": [Categorical],
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

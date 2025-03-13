from typing import List, Union

from datasets import ClassLabel, DatasetDict, Image

from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.tasks.base_task import BaseTask


class ImageClassificationTask(BaseTask):
    """Base class for image classification tasks.

    Here you can change the methods provided by class Task.
    """

    COMPATIBLE_COMPONENTS = ["Accuracy", "F1", "Precision", "Recall"]

    metadata: dict = {
        "inputs_types": [Image],
        "outputs_types": [ClassLabel],
        "inputs_cardinality": 1,
        "outputs_cardinality": 1,
    }

    def prepare_for_task(
        self, datasetdict: Union[DatasetDict, DashAIDataset], outputs_columns: List[str]
    ) -> DashAIDataset:
        """Change the column types to suit the image classification task.

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
        types = {column: "Categorical" for column in outputs_columns}
        datasetdict = to_dashai_dataset(datasetdict)
        dataset = datasetdict.change_columns_type(types)
        return dataset

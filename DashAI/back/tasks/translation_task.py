"""DashAI Translation Task."""

from typing import List, Union

from datasets import DatasetDict

from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
)
from DashAI.back.tasks.base_task import BaseTask
from DashAI.back.types.value_types import Text


class TranslationTask(BaseTask):
    """Base class for translation task."""

    COMPATIBLE_COMPONENTS = ["Bleu", "Ter"]

    metadata: dict = {
        "inputs_types": [Text],
        "outputs_types": [Text],
        "inputs_cardinality": 1,
        "outputs_cardinality": 1,
    }
    DESCRIPTION: str = """
    The translation task is natural language processing (NLP) task that involves
    converting text or speech from one language into another language while
    preserving the meaning and context.
    """

    def prepare_for_task(
        self,
        dataset: Union[DatasetDict, DashAIDataset],
        input_columns: List[str],
        output_columns: List[str],
    ) -> DashAIDataset:
        """Convert the dataset to DashAIDataset and check the columns types

        A copy of the dataset is created.

        Parameters
        ----------
        dataset : Union[DatasetDict, DashAIDataset]
            Dataset to be changed

        Returns
        -------
        DashAIDataset
            Dataset with the new types
        """
        dashai_dataset = super().prepare_for_task(
            dataset, input_columns, output_columns
        )
        return dashai_dataset

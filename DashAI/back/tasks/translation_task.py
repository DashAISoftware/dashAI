"""DashAI Translation Task."""

from typing import TYPE_CHECKING, List, Union

from DashAI.back.core.utils import MultilingualString
from DashAI.back.tasks.base_task import BaseTask
from DashAI.back.types.value_types import Text

if TYPE_CHECKING:
    from datasets import DatasetDict
    from numpy import ndarray

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class TranslationTask(BaseTask):
    """Task for sequence-to-sequence machine translation between languages.

    Translation tasks take a single ``Text`` input column (source language) and
    produce a single ``Text`` output column (target language). The compatible
    metrics are BLEU and TER, which measure n-gram overlap and translation edit
    rate against reference translations respectively.
    """

    COMPATIBLE_COMPONENTS = ["Bleu", "Ter"]

    SCORING_PROFILES = {
        "translation_quality": {
            "description": "Translation Quality",
            "weights": {"Bleu": 0.5, "Chrf": 0.5},
        },
        "translation_balanced": {
            "description": "Translation Balanced",
            "weights": {"Bleu": 0.4, "Chrf": 0.3, "Ter": 0.3},
        },
    }

    metadata: dict = {
        "inputs_types": [Text],
        "outputs_types": [Text],
        "inputs_cardinality": 1,
        "outputs_cardinality": 1,
    }
    DESCRIPTION: str = MultilingualString(
        en="""
    The translation task is natural language processing (NLP) task that involves
    converting text or speech from one language into another language while
    preserving the meaning and context.
    """,
        es="""
    La tarea de traducción es una tarea de procesamiento de lenguaje natural (PLN)
    que implica convertir texto o habla de un idioma a otro idioma mientras se
    preserva el significado y el contexto.
    """,
    )

    DISPLAY_NAME: str = MultilingualString(en="Translation", es="Traducción")

    def prepare_for_task(
        self,
        dataset: Union["DatasetDict", "DashAIDataset"],
        input_columns: List[str],
        output_columns: List[str],
    ) -> "DashAIDataset":
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

    def process_predictions(
        self, dataset: "DashAIDataset", predictions: "ndarray", output_column: str
    ):
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

    def num_labels(self, dataset: "DashAIDataset", output_column: str) -> int | None:
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

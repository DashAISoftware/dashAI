from typing import TYPE_CHECKING, List, Union

from DashAI.back.core.utils import MultilingualString
from DashAI.back.tasks.classification_task import ClassificationTask
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.value_types import Text

if TYPE_CHECKING:
    from datasets import DatasetDict

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class TextClassificationTask(ClassificationTask):
    """Task for classifying raw text sequences into discrete categories.

    Text classification maps a single text input column (type ``Text``) to a
    single categorical output column. It is the DashAI task type for NLP
    applications such as sentiment analysis, spam detection, topic labelling,
    and intent recognition. Models compatible with this task accept tokenised
    or raw text and produce per-class probability distributions.
    """

    metadata: dict = {
        "inputs_types": [Text],
        "outputs_types": [Categorical],
        "inputs_cardinality": 1,
        "outputs_cardinality": 1,
    }

    DESCRIPTION: str = MultilingualString(
        en="""
    Text classification is an essential Natural Language Processing (NLP) task that
    involves automatically assigning pre-defined categories or labels to text documents
    based on their content. It serves as the foundation for applications like sentiment
    analysis, spam filtering, topic classification, and document categorization.
    """,
        es="""
    La clasificación de texto es una tarea esencial del Procesamiento de Lenguaje
    Natural (PLN) que implica asignar automáticamente categorías o etiquetas
    predefinidas a documentos de texto según su contenido. Sirve como base para
    aplicaciones como el análisis de sentimientos, el filtrado de spam,
    la clasificación de temas y la categorización de documentos.
    """,
    )
    DISPLAY_NAME: str = MultilingualString(
        en="Text Classification", es="Clasificación de Texto"
    )

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

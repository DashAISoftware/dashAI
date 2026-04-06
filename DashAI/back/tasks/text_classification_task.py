from typing import TYPE_CHECKING, List, Union

from DashAI.back.core.utils import MultilingualString
from DashAI.back.tasks.classification_task import ClassificationTask
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.value_types import Text

if TYPE_CHECKING:
    from datasets import DatasetDict

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class TextClassificationTask(ClassificationTask):
    """Task for classifying a single text column into discrete categories.

    Text classification takes one input column of type ``Text`` and maps it to
    one categorical output column. The task covers any NLP scenario where a
    raw or pre-processed text sequence must be assigned to one of a fixed set
    of labels, such as sentiment analysis, spam detection, topic labelling, and
    intent recognition. Compatible models consume the text directly and output
    a predicted class label for each sample.
    """

    metadata: dict = {
        "inputs_types": [Text],
        "outputs_types": [Categorical],
        "inputs_cardinality": 1,
        "outputs_cardinality": 1,
    }

    DESCRIPTION: str = MultilingualString(
        en=(
            "Text classification is a Natural Language Processing (NLP) task "
            "that assigns a predefined category or label to a text sequence "
            "based on its content. "
            "It requires exactly one text input column and one categorical "
            "output column. "
            "Typical use cases include sentiment analysis, spam detection, "
            "topic labelling, intent recognition, and language identification. "
            "Models compatible with this task process raw or tokenised text "
            "and predict the most likely class label for each input sample."
        ),
        es=(
            "La clasificación de texto es una tarea de Procesamiento de "
            "Lenguaje Natural (PLN) que asigna una categoría o etiqueta "
            "predefinida a una secuencia de texto según su contenido. "
            "Requiere exactamente una columna de entrada de tipo texto y una "
            "columna de salida categórica. "
            "Los casos de uso más comunes incluyen análisis de sentimientos, "
            "detección de spam, clasificación de temas, reconocimiento de "
            "intenciones e identificación de idioma. "
            "Los modelos compatibles con esta tarea procesan texto sin "
            "procesar o tokenizado y predicen la etiqueta de clase más "
            "probable para cada muestra de entrada."
        ),
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

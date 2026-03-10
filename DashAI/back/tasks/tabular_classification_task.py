from typing import List, Union

from datasets import DatasetDict

from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.tasks.classification_task import ClassificationTask
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.value_types import Float, Integer


class TabularClassificationTask(ClassificationTask):
    """Base class for tabular classification tasks.

    Here you can change the methods provided by class Task.
    """

    DESCRIPTION: str = MultilingualString(
        en=(
            "Tabular classification in machine learning involves predicting "
            "categorical labels for structured data organized in tabular form "
            "(rows and columns). Models are trained to learn patterns and "
            "relationships in the data, enabling accurate classification of "
            "new instances."
        ),
        es=(
            "La clasificación tabular en el aprendizaje automático implica "
            "predecir etiquetas categóricas para datos estructurados "
            "organizados en forma tabular (filas y columnas). Los modelos se "
            "entrenan para aprender patrones y relaciones en los datos, "
            ", lo que permite una clasificación precisa de nuevas instancias."
        ),
    )
    DISPLAY_NAME: str = MultilingualString(
        en="Tabular Classification", es="Clasificación Tabular"
    )
    metadata: dict = {
        "inputs_types": [Float, Integer, Categorical],
        "outputs_types": [Categorical],
        "inputs_cardinality": "n",
        "outputs_cardinality": 1,
    }

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

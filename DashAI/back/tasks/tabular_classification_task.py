from typing import List, Union

import logging
from datasets import DatasetDict

from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.tasks.classification_task import ClassificationTask
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.value_types import Float, Integer, Text

log = logging.getLogger(__name__)


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
        "inputs_types": [Float, Integer, Categorical, Text],
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

        A copy of the dataset is created. Text columns are automatically
        converted to Categorical type.

        Parameters
        ----------
        dataset : Union[DatasetDict, DashAIDataset]
            Dataset to be changed

        Returns
        -------
        DashAIDataset
            Dataset with the new types
        """
        # Convert to DashAIDataset if needed (this is what the parent does first)
        if isinstance(dataset, DatasetDict):
            dashai_dataset = DashAIDataset(dataset)
        else:
            dashai_dataset = dataset

        # Convert Text columns to Categorical BEFORE validation
        for col in input_columns:
            if col in dashai_dataset.types:
                col_type = dashai_dataset.types[col]
                if isinstance(col_type, Text):
                    # Get unique values using dataset API
                    unique_values = [
                        value for value in dashai_dataset.unique(col) if value is not None
                    ]
                    log.info(
                        f"Converting Text column '{col}' to Categorical with "
                        f"{len(unique_values)} categories"
                    )
                    # Create a Categorical type with the unique values
                    categorical = Categorical(values=unique_values)
                    # Update the type in the dataset
                    dashai_dataset.types[col] = categorical

        # Now call parent's prepare_for_task for validation
        # This will validate that all input columns are now of allowed types
        return super().prepare_for_task(
            dashai_dataset, input_columns, output_columns
        )

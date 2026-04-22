from typing import TYPE_CHECKING, List, Union

from DashAI.back.core.utils import MultilingualString
from DashAI.back.tasks.classification_task import ClassificationTask
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.value_types import Float, Integer

if TYPE_CHECKING:
    from datasets import DatasetDict

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class TabularClassificationTask(ClassificationTask):
    """Task for classifying structured tabular data into discrete categories.

    Tabular classification predicts categorical labels from structured feature
    tables (rows of observations, columns of features). It accepts numeric
    (``Float``, ``Integer``) and categorical (``Categorical``) inputs, requires
    a single categorical output column, and is compatible with all sklearn-based
    and DashAI tabular classifier models.
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
    SCORING_PROFILES = {
        "balanced": {
            "description": "Balanced",
            "weights": {"Accuracy": 0.3, "F1": 0.4, "ROCAUC": 0.3},
        },
        "detectPositives": {
            "description": "Detect Positives",
            "weights": {"Recall": 0.6, "F1": 0.3, "Precision": 0.1},
        },
        "avoidFalseAlarms": {
            "description": "Avoid False Alarms",
            "weights": {"Precision": 0.6, "F1": 0.3, "Recall": 0.1},
        },
        "probabilityQuality": {
            "description": "Probability Quality",
            "weights": {"ROCAUC": 0.5, "LogLoss": 0.5},
        },
    }
    metadata: dict = {
        "inputs_types": [Float, Integer, Categorical],
        "outputs_types": [Categorical],
        "inputs_cardinality": "n",
        "outputs_cardinality": 1,
    }

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

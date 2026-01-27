from typing import List, Union

from datasets import DatasetDict

from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.tasks.base_task import BaseTask
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.value_types import Float, Integer


class RegressionTask(BaseTask):
    """Base class for regression tasks.

    Here you can change the methods provided by class Task.
    """

    DESCRIPTION: str = MultilingualString(
        en="""
    Regression in machine learning involves predicting continuous values for
    structured data organized in tabular form (rows and columns).
    Models are trained to learn patterns and relationships in the data,
    enabling accurate prediction of new instances.""",
        es="""
    La regresión en el aprendizaje automático implica predecir valores
    continuos para datos estructurados organizados en
    forma tabular (filas y columnas).
    Los modelos se entrenan para aprender patrones y relaciones en los datos,
    lo que permite una predicción precisa de nuevas instancias.""",
    )
    DISPLAY_NAME: str = MultilingualString(en="Regression", es="Regresión")

    metadata: dict = {
        "inputs_types": [Float, Integer, Categorical],
        "outputs_types": [Float, Integer],
        "inputs_cardinality": "n",
        "outputs_cardinality": 1,
    }

    def prepare_for_task(
        self,
        dataset: Union[DatasetDict, DashAIDataset],
        input_columns: List[str],
        output_columns: List[str],
    ) -> DashAIDataset:
        """Convert the dataset to DashAIDataset and validate types.


        A copy of the dataset is created.

        Parameters
        ----------
        datasetdict : DatasetDict
            Dataset to be changed

        Returns
        -------
        DashAIDataset
            Dataset with validated types
        """
        dashai_dataset = super().prepare_for_task(
            dataset, input_columns, output_columns
        )
        return dashai_dataset

    def process_predictions(self, dataset, predictions, output_column):
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

    def num_labels(self, dataset: DashAIDataset, output_column: str) -> int | None:
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

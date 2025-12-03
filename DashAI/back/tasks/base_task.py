from abc import abstractmethod
from typing import Any, Dict, Final, List, Union

import pandas as pd
from datasets import DatasetDict
from starlette.datastructures import UploadFile

from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.tasks.utils import get_bytes_with_type_filetype


class BaseTask:
    """Base class for DashAI compatible tasks."""

    TYPE: Final[str] = "Task"

    @property
    @abstractmethod
    def schema(self) -> Dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get metadata values for the current task

        Returns:
            Dict[str, Any]: Dictionary with the metadata containing the input and output
             types/cardinality.
        """
        metadata = cls.metadata

        # Extract class names
        inputs_types = [input_type.__name__ for input_type in metadata["inputs_types"]]
        outputs_types = [
            output_type.__name__ for output_type in metadata["outputs_types"]
        ]

        parsed_metadata: dict = {
            "inputs_types": inputs_types,
            "outputs_types": outputs_types,
            "inputs_cardinality": metadata["inputs_cardinality"],
            "outputs_cardinality": metadata["outputs_cardinality"],
        }
        return parsed_metadata

    def validate_dataset_for_task(
        self,
        dataset: DashAIDataset,
        dataset_name: str,
        input_columns: List[str],
        output_columns: List[str],
    ) -> None:
        """Validate a dataset for the current task.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset to be validated
        dataset_name : str
            Dataset name
        """
        metadata = self.metadata
        allowed_input_types = tuple(metadata["inputs_types"])
        allowed_output_types = tuple(metadata["outputs_types"])
        inputs_cardinality = metadata["inputs_cardinality"]
        outputs_cardinality = metadata["outputs_cardinality"]

        # Check input types
        for input_col in input_columns:
            input_col_type = dataset.features[input_col]
            if not isinstance(input_col_type, allowed_input_types):
                raise TypeError(
                    f"{input_col_type} is not an allowed type for input columns."
                )

        # Check output types
        for output_col in output_columns:
            output_col_type = dataset.features[output_col]
            if not isinstance(output_col_type, allowed_output_types):
                raise TypeError(
                    f"{output_col_type} is not an allowed type for output columns."
                )

        # Check input cardinality
        if inputs_cardinality != "n" and len(input_columns) != inputs_cardinality:
            raise ValueError(
                f"Input cardinality ({len(input_columns)}) does not"
                f" match task cardinality ({inputs_cardinality})"
            )

        # Check output cardinality
        if outputs_cardinality != "n" and len(output_columns) != outputs_cardinality:
            raise ValueError(
                f"Output cardinality ({len(output_columns)})"
                f" does not "
                f"match task cardinality ({outputs_cardinality})"
            )

    @abstractmethod
    def prepare_for_task(
        self, dataset: Union[DatasetDict, DashAIDataset], outputs_columns: List[str]
    ) -> DashAIDataset:
        """Change column types to suit the task requirements.

        Parameters
        ----------
        dataset : Union[DatasetDict, DashAIDataset]
            Dataset to be changed

        Returns
        -------
        DashAIDataset
            Dataset with the new types
        """
        raise NotImplementedError

    @abstractmethod
    def process_predictions(
        self, dataset: DashAIDataset, predictions: Any, target_column: str
    ) -> Any:
        """Process the predictions to suit the task requirements.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset to be changed
        predictions : Any
            Predictions to be processed
        target_column : str
            Target column for the task

        Returns
        -------
        Any
            Processed predictions
        """
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    def process_manual_input(self, manual_input: List[dict]) -> DashAIDataset:
        """Process manual input data into a DashAIDataset.

        Parameters
        ----------
        manual_input : List[dict]
            List of dictionaries representing manual input data.

        Returns
        -------
        DashAIDataset
            Processed DashAIDataset from manual input.
        """
        inputs_types = self.get_metadata()["inputs_types"]
        inputs_cardinality = self.get_metadata()["inputs_cardinality"]
        print("inputs_types:", inputs_types)

        # Check that manual input cardinality matches task cardinality
        if inputs_cardinality != "n" and len(manual_input[0]) != inputs_cardinality:
            raise ValueError(
                f"Input cardinality ({len(manual_input[0])}) does not"
                f" match task cardinality ({inputs_cardinality})"
            )

        # Verrify each input type is correct
        mapped_inputs = []
        for input_dict in manual_input:
            row = {}
            for key, value in input_dict.items():
                # File case (image, audio, video, etc.)
                if isinstance(value, UploadFile):
                    file_bytes = value.file.read()
                    data, detected_type = get_bytes_with_type_filetype(file_bytes)
                    if detected_type not in inputs_types:
                        raise TypeError(
                            f"Detected type '{detected_type}' "
                            f"for file '{value.filename}'"
                            f" is not an allowed type for input columns."
                        )
                    row[key] = data
                # Primitive case (value)
                # TODO: Verify primitive types match expected input types with new types
                else:
                    row[key] = value
            mapped_inputs.append(row)

        # Convert to DashAIDataset
        print("Mapped inputs:", mapped_inputs)
        mapped_inputs_df = pd.DataFrame(mapped_inputs)
        return to_dashai_dataset(mapped_inputs_df)

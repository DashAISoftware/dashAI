from abc import abstractmethod
from typing import Any, Dict, Final, List, Union

import numpy as np
import pandas as pd
from datasets import DatasetDict
from starlette.datastructures import UploadFile

from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    get_columns_spec,
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
        types = dataset._types
        # Check input types
        for input_col in input_columns:
            input_col_type = types[input_col]

            if not isinstance(input_col_type, allowed_input_types):
                raise TypeError(
                    f"{input_col_type} is not an allowed type for input columns."
                )

        # Check output types
        for output_col in output_columns:
            output_col_type = types[output_col]

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

    def prepare_for_task(
        self,
        dataset: Union[DatasetDict, DashAIDataset],
        input_columns: List[str],
        output_columns: List[str],
    ) -> DashAIDataset:
        """
        Default preparation shared by every task.

        - Ensures DashAIDataset instance.
        - Validates types against task metadata.
        - Returns dataset ready for the taks.
        """
        dashai_dataset = to_dashai_dataset(dataset)
        self.validate_dataset_for_task(
            dashai_dataset,
            dataset_name=getattr(dashai_dataset, "name", "dataset"),
            input_columns=input_columns,
            output_columns=output_columns,
        )
        return dashai_dataset

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

    def _validate_and_normalize_value(
        self,
        value: Any,
        column_spec: Dict[str, Any],
        column_name: str,
        row_idx: int,
    ) -> Any:
        """Validate and normalize a value against expected column specification.

        Parameters
        ----------
        value : Any
            Value to validate
        column_spec : Dict[str, Any]
            Column specification with 'type', 'dtype', 'categories', etc.
        column_name : str
            Name of the column being validated
        row_idx : int
            Index of the row being validated

        Returns
        -------
        Any
            Normalized value

        Raises
        ------
        ValueError
            If categorical value is not in allowed categories
        TypeError
            If value doesn't match expected type
        """
        col_type = column_spec.get("type")
        dtype = column_spec.get("dtype")

        if col_type == "Categorical":
            categories = column_spec.get("categories", [])

            if dtype and dtype.startswith("int"):
                if isinstance(value, bool):
                    raise TypeError(
                        f"Row {row_idx}, column '{column_name}': "
                        f"Boolean cannot be converted to integer categorical"
                    )
                try:
                    normalized_value = int(float(value))
                except (TypeError, ValueError) as e:
                    raise TypeError(
                        f"Row {row_idx}, column '{column_name}': "
                        f"Cannot convert '{value}' to integer categorical"
                    ) from e

            elif dtype and dtype.startswith("float"):
                if isinstance(value, bool):
                    raise TypeError(
                        f"Row {row_idx}, column '{column_name}': "
                        f"Boolean cannot be converted to float categorical"
                    )
                try:
                    normalized_value = float(value)
                except (TypeError, ValueError) as e:
                    raise TypeError(
                        f"Row {row_idx}, column '{column_name}': "
                        f"Cannot convert '{value}' to float categorical"
                    ) from e

            elif dtype == "bool":
                if isinstance(value, bool):
                    normalized_value = value
                elif isinstance(value, str):
                    if value.lower() in ("true", "1", "yes"):
                        normalized_value = True
                    elif value.lower() in ("false", "0", "no"):
                        normalized_value = False
                    else:
                        raise ValueError(
                            f"Row {row_idx}, column '{column_name}': "
                            f"Cannot convert '{value}' to boolean"
                        )
                else:
                    raise TypeError(
                        f"Row {row_idx}, column '{column_name}': "
                        f"Expected boolean categorical, got {type(value).__name__}"
                    )

            else:
                # String categorical
                normalized_value = str(value)

            if str(normalized_value) not in [str(cat) for cat in categories]:
                raise ValueError(
                    f"Row {row_idx}, column '{column_name}': "
                    f"Value '{value}' is not valid. "
                    f"Allowed: {categories}"
                )

            return normalized_value

        if col_type == "Float":
            if isinstance(value, bool):
                raise TypeError(
                    f"Row {row_idx}, column '{column_name}': "
                    f"Boolean cannot be converted to Float"
                )
            try:
                return float(value)
            except (TypeError, ValueError) as e:
                raise TypeError(
                    f"Row {row_idx}, column '{column_name}': "
                    f"Cannot convert '{value}' to Float"
                ) from e

        if col_type == "Integer":
            if isinstance(value, bool):
                raise TypeError(
                    f"Row {row_idx}, column '{column_name}': "
                    f"Boolean cannot be converted to Integer"
                )
            try:
                int_val = int(value)
                if isinstance(value, float) and not np.isclose(value, int_val):
                    raise TypeError(
                        f"Row {row_idx}, column '{column_name}': "
                        f"Float value '{value}' has decimals, cannot convert to Integer"
                    )
                return int_val
            except (TypeError, ValueError) as e:
                raise TypeError(
                    f"Row {row_idx}, column '{column_name}': "
                    f"Cannot convert '{value}' to Integer"
                ) from e

        if col_type == "Text":
            return str(value)

        # Unknown type
        return value

    def process_manual_input(
        self, manual_input: List[dict], dataset_path: str
    ) -> DashAIDataset:
        """Process manual input data into a DashAIDataset with type validation.

        Parameters
        ----------
        manual_input : List[dict]
            List of dictionaries representing manual input data.
        dataset_path : str
            Path to the training dataset (used to get column specs for validation)

        Returns
        -------
        DashAIDataset
            Processed DashAIDataset from manual input.

        Raises
        ------
        ValueError
            If input cardinality doesn't match or categorical value is invalid
        TypeError
            If input types don't match expected types
        """
        from DashAI.back.dataloaders.classes.dashai_dataset import (
            transform_dataset_with_schema,
        )

        columns_spec = get_columns_spec(dataset_path)
        inputs_cardinality = self.get_metadata()["inputs_cardinality"]

        if inputs_cardinality != "n" and len(manual_input[0]) != inputs_cardinality:
            raise ValueError(
                f"Input cardinality ({len(manual_input[0])}) does not "
                f"match task cardinality ({inputs_cardinality})"
            )

        mapped_inputs = []
        for row_idx, input_dict in enumerate(manual_input):
            row = {}
            for col_name, value in input_dict.items():
                column_spec = columns_spec.get(col_name)
                if not column_spec:
                    raise ValueError(
                        f"Column '{col_name}' not found in training dataset"
                    )

                # File case (image, audio, video, etc.)
                if isinstance(value, UploadFile):
                    file_bytes = value.file.read()
                    data, detected_type = get_bytes_with_type_filetype(file_bytes)

                    if detected_type != column_spec.get("type"):
                        raise TypeError(
                            f"Row {row_idx}, column '{col_name}': "
                            f"File type '{detected_type}' doesn't match "
                            f"expected type '{column_spec.get('type')}'"
                        )
                    row[col_name] = data

                # Primitive value
                else:
                    normalized_value = self._validate_and_normalize_value(
                        value, column_spec, col_name, row_idx
                    )
                    row[col_name] = normalized_value

            mapped_inputs.append(row)

        # Convert to DataFrame first
        mapped_inputs_df = pd.DataFrame(mapped_inputs)

        # Convert to DashAIDataset and apply schema transformation
        # This ensures categorical encoding is applied
        dashai_dataset = to_dashai_dataset(mapped_inputs_df)
        dashai_dataset = transform_dataset_with_schema(dashai_dataset, columns_spec)

        return dashai_dataset

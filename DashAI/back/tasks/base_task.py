from abc import abstractmethod
from typing import Any, Dict, Final, List, Union

from datasets import DatasetDict

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


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
        input_columns : List[str]
            List of input column names
        output_columns : List[str]
            List of output column names
        """
        metadata = self.metadata
        allowed_input_types = tuple(metadata["inputs_types"])
        allowed_output_types = tuple(metadata["outputs_types"])
        inputs_cardinality = metadata["inputs_cardinality"]
        outputs_cardinality = metadata["outputs_cardinality"]

        # Check input types
        for input_col in input_columns:
            if input_col not in dataset.features:
                raise KeyError(
                    f"Input column '{input_col}' not found in dataset '{dataset_name}'. "
                    f"Available columns: {list(dataset.features.keys())}"
                )
            input_col_type = dataset.features[input_col]
            if not isinstance(input_col_type, allowed_input_types):
                raise TypeError(
                    f"{input_col_type} is not an allowed type for input columns. "
                    f"Allowed types: {allowed_input_types}"
                )

        # ✅ Check output types - skip validation if columns will be transformed
        # This allows tasks like TimeSeriesClassificationTask to transform
        # multi-label binary columns into a single categorical column
        missing_output_cols = [
            col for col in output_columns if col not in dataset.features
        ]

        if missing_output_cols:
            # If output columns are missing, check if this task transforms them
            # (e.g., TimeSeriesClassificationTask converts multiple binary columns to one categorical)
            if (
                hasattr(self, "_transforms_output_columns")
                and self._transforms_output_columns
            ):
                # Skip validation for output columns that will be created by prepare_for_task
                pass
            else:
                raise KeyError(
                    f"Output column(s) {missing_output_cols} not found in dataset '{dataset_name}'. "
                    f"Available columns: {list(dataset.features.keys())}"
                )
        else:
            # Validate output column types only if they exist
            for output_col in output_columns:
                output_col_type = dataset.features[output_col]
                if not isinstance(output_col_type, allowed_output_types):
                    raise TypeError(
                        f"{output_col_type} is not an allowed type for output columns. "
                        f"Allowed types: {allowed_output_types}"
                    )

        # Check input cardinality
        if inputs_cardinality != "n" and len(input_columns) != inputs_cardinality:
            raise ValueError(
                f"Input cardinality ({len(input_columns)}) does not"
                f" match task cardinality ({inputs_cardinality})"
            )

        # ✅ Check output cardinality - handle special case for transforming tasks
        if outputs_cardinality != "n":
            # For tasks that transform output columns (like TimeSeriesClassificationTask),
            # the output cardinality check should happen after prepare_for_task
            if not (
                hasattr(self, "_transforms_output_columns")
                and self._transforms_output_columns
            ):
                if len(output_columns) != outputs_cardinality:
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
        outputs_columns : List[str]
            List of output column names

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

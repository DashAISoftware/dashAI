from abc import ABC, abstractmethod
from pathlib import Path

from beartype.typing import Any, Dict, Final, List

from DashAI.back.config_object import ConfigObject
from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    select_columns,
)
from DashAI.back.dependencies.database.models import Exploration, Explorer


class BaseExplorerSchema(BaseSchema):
    """
    Base schema for explorers, it defines the parameters to be used in each explorer.

    The schema should be assigned to the explorer class to define the parameters of
    its configuration.
    """


class BaseExplorer(ConfigObject, ABC):
    """
    Base class for explorers.
    Use this class as reference to create new explorers.

    To create a new explorer, you must:
    - Create a new schema that extends `BaseExplorerSchema`.
    - Create a new class that extends `BaseExplorer` and assign the
        previous schema to the `SCHEMA` attribute.
    - Implement the `launch_exploration` method.
    - Implement the `save_exploration` method.
    - Implement the `get_results` method.

    You can also optionally:
    - Implement the `validate_parameters` method if you want to validate
        the parameters in a custom way before creating/updating the database record.
    - Implement the `prepare_dataset` method if you want to prepare the
        dataset in a custom way before launching the exploration.
    - Add a display name to the `DISPLAY_NAME` attribute to show a custom
        name in the frontend.
    - Add a description to the `DESCRIPTION` attribute to show a custom
        description in the frontend.
    """

    TYPE: Final[str] = "Explorer"
    DISPLAY_NAME: Final[str] = ""
    DESCRIPTION: Final[str] = ""
    SCHEMA: BaseExplorerSchema
    metadata: Dict[str, Any] = {}

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """
        Get metadata values for the current explorer.

        Returns
        -------
        Dict[str, Any]
            Dictionary with the metadata containing valid dtypes and cardinality for
            the explorer columns.
        """
        metadata = cls.metadata
        metadata["display_name"] = (
            cls.DISPLAY_NAME if cls.DISPLAY_NAME else cls.__name__
        )
        # Set default values if not present
        # TODO: Update the metadata when DashAI Types are implemented
        if metadata.get("allowed_value_types", None) is None:
            metadata["allowed_value_types"] = ["*"]
        if metadata.get("restricted_value_types", None) is None:
            metadata["restricted_value_types"] = []
        if metadata.get("allowed_dtypes", None) is None:
            metadata["allowed_dtypes"] = ["*"]
        if metadata.get("restricted_dtypes", None) is None:
            metadata["restricted_dtypes"] = []
        if metadata.get("input_cardinality", None) is None:
            metadata["input_cardinality"] = {"min": 1}
        return metadata

    @classmethod
    def validate_parameters(cls, params: Dict[str, Any]) -> bool:
        """
        Validates the parameters of the explorer.

        Parameters
        ----------
        params : Dict[str, Any]
            The parameters to validate.

        Returns
        -------
        bool
            True if the parameters are valid, False otherwise.
        """
        return cls.SCHEMA.model_validate(params)

    @classmethod
    def validate_columns(
        cls, explorer_info: Explorer, column_spec: Dict[str, Dict[str, str]]
    ) -> bool:
        """
        Validates the columns of the explorer and dataset against the explorer metadata.

        Parameters
        ----------
        explorer_info : Explorer
            The explorer information.

        column_spec : Dict[str, Dict[str, str]]
            The columns to validate.

        Returns
        -------
        bool
            True if the columns are valid, False otherwise.
        """
        metadata = cls.get_metadata()
        selected_columns = explorer_info.columns

        # Check if the number of columns is valid
        input_cardinality = metadata.get("input_cardinality", {})
        if (
            "min" in input_cardinality
            and len(selected_columns) < input_cardinality["min"]
        ):
            return False
        if (
            "max" in input_cardinality
            and len(selected_columns) > input_cardinality["max"]
        ):
            return False
        if (
            "exact" in input_cardinality
            and len(selected_columns) != input_cardinality["exact"]
        ):
            return False

        # TODO: Update the logic when DashAI Types are implemented
        # Check if the columns are of valid types
        for column in selected_columns:
            column_name = column["columnName"]
            column_type = column_spec[column_name]["dtype"]

            # Check if the column's type is allowed
            if (
                "*" not in metadata["allowed_dtypes"]
                and column_type not in metadata["allowed_value_types"]
            ):
                return False

            # Check if the column's type is restricted
            if column_type in metadata["restricted_value_types"]:
                return False

        return True

    def prepare_dataset(
        self, loaded_dataset: DashAIDataset, columns: List[Dict[str, Any]]
    ) -> DashAIDataset:
        """
        Prepare the dataset for the exploration.

        Parameters
        ----------
        dataset : DatasetDict
            The dataset to prepare.

        columns : list[Dict[str, Any]]
            The columns to select from the dataset, each column is a dictionary
            with the following keys:

            [Required]
            - columnName: The name of the column.

            [Optional]
            - id: The id or index of the column.
            - valueType: The type of the column.
            - dataType: The data type of the column.

        Returns
        -------
        DashAIDataset
            The prepared dataset.
        """
        # Select the columns
        columnNames = list({col["columnName"] for col in columns})
        loaded_dataset = select_columns(loaded_dataset, columnNames, [])[0]
        return loaded_dataset

    @abstractmethod
    def launch_exploration(
        self, dataset: DashAIDataset, explorer_info: Explorer
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def save_exploration(
        self,
        exploration_info: Exploration,
        explorer_info: Explorer,
        save_path: Path,
        result: Any,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_results(
        self, exploration_path: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        raise NotImplementedError

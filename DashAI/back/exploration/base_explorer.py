from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Final, List

from DashAI.back.config_object import ConfigObject
from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.dependencies.database.models import Explorer, Notebook
from DashAI.back.static.icons import Icon

if TYPE_CHECKING:
    from pathlib import Path

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


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
    SHORT_DESCRIPTION: Final[str] = ""
    IMAGE_PREVIEW: Final[str] = ""
    CATEGORY: Final[str] = "Other"
    ICON: Final[str] = Icon.Extension.value
    COLOR: Final[str] = "rgb(255, 255, 255)"
    SCHEMA: BaseExplorerSchema
    metadata: Dict[str, Any] = {}

    def __init__(self, **kwargs) -> None:
        """Initialize the explorer, storing any extra kwargs for later use.

        Parameters
        ----------
        **kwargs
            Configuration keyword arguments as defined in the
            explorer's SCHEMA.
        """
        self.kwargs = kwargs

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get metadata for the explorer, used by the DashAI frontend.

        Returns
        -------
        Dict[str, Any]
            Dictionary containing display name, description,
            image preview path, category, icon, color, allowed dtypes,
            restricted dtypes, and input cardinality constraints.
        """
        metadata = cls.metadata
        metadata["display_name"] = (
            cls.DISPLAY_NAME if cls.DISPLAY_NAME else cls.__name__
        )
        metadata["short_description"] = (
            cls.SHORT_DESCRIPTION if cls.SHORT_DESCRIPTION else ""
        )
        metadata["image_preview"] = cls.IMAGE_PREVIEW if cls.IMAGE_PREVIEW else ""
        metadata["category"] = cls.CATEGORY if cls.CATEGORY else "Other"
        metadata["icon"] = cls.ICON if cls.ICON else Icon.Extension.value
        metadata["color"] = cls.COLOR if cls.COLOR else "rgb(255, 255, 255)"
        # Set default values if not present
        # TODO: Update the metadata when DashAI Types are implemented
        if metadata.get("allowed_dtypes", None) is None:
            metadata["allowed_dtypes"] = ["*"]
        if metadata.get("restricted_dtypes", None) is None:
            metadata["restricted_dtypes"] = []
        if metadata.get("input_cardinality", None) is None:
            metadata["input_cardinality"] = {"min": 1}
        return metadata

    @classmethod
    def validate_parameters(cls, params: Dict[str, Any]) -> bool:
        """Validate explorer parameters against the explorer's schema.

        Parameters
        ----------
        params : Dict[str, Any]
            The configuration parameters to validate.

        Returns
        -------
        BaseExplorerSchema
            The validated and parsed schema instance.
            Subclasses that override this method may return a bool to
            indicate pass/fail without returning the model instance.

        Raises
        ------
        ValidationError
            If any parameter fails schema validation.
        """
        return cls.SCHEMA.model_validate(params)

    @classmethod
    def validate_columns(
        cls, explorer_info: Explorer, column_spec: Dict[str, Dict[str, str]]
    ) -> bool:
        """Validate that the selected columns satisfy the explorer's constraints.

        Checks column count against `input_cardinality` and column data types
        against `allowed_dtypes` / `restricted_dtypes` in the explorer metadata.

        Parameters
        ----------
        explorer_info : Explorer
            The database record for the explorer
            instance, including the selected columns.
        column_spec : Dict[str, Dict[str, str]]
            A mapping from column name
            to a dict with at least a ``"type"`` key describing the column's
            data type.

        Returns
        -------
        bool
            True if all column constraints are satisfied, False otherwise.
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
            column_type = column_spec[column_name]["type"]

            # Check if the column's type is allowed
            if (
                "*" not in metadata["allowed_dtypes"]
                and column_type not in metadata["allowed_dtypes"]
            ):
                return False

            # Check if the column's type is restricted
            if column_type in metadata["restricted_dtypes"]:
                return False

        return True

    def prepare_dataset(
        self, loaded_dataset: "DashAIDataset", columns: List[Dict[str, Any]]
    ) -> "DashAIDataset":
        """Prepare the dataset by selecting only the columns
        needed for this exploration.

        Override this method in subclasses that need to load additional columns
        beyond those explicitly selected (e.g. a color-grouping column).

        Parameters
        ----------
        loaded_dataset : DashAIDataset
            The full dataset loaded from storage.
        columns : List[Dict[str, Any]]
            List of column descriptor dicts, each
            containing at least ``"columnName"``. Optional keys: ``"id"``,
            ``"valueType"``, ``"dataType"``.

        Returns
        -------
        DashAIDataset
            Dataset restricted to the requested columns.
        """
        # Select the columns
        columnNames = list({col["columnName"] for col in columns})
        loaded_dataset = loaded_dataset.select_columns(columnNames)
        return loaded_dataset

    @abstractmethod
    def launch_exploration(
        self, dataset: "DashAIDataset", explorer_info: Explorer
    ) -> Any:
        """Run the exploration and return the raw result.

        Parameters
        ----------
        dataset : DashAIDataset
            The prepared dataset (output of
            `prepare_dataset`).
        explorer_info : Explorer
            The database record for this explorer
            instance, including name, columns, and parameters.

        Returns
        -------
        Any
            The exploration result (e.g. a Plotly figure, a DataFrame).
        """
        raise NotImplementedError

    @abstractmethod
    def save_notebook(
        self,
        notebook_info: Notebook,
        explorer_info: Explorer,
        save_path: "Path",
        result: Any,
    ) -> str:
        """Persist the exploration result to disk.

        Parameters
        ----------
        notebook_info : Notebook
            The notebook database record.
        explorer_info : Explorer
            The explorer database record.
        save_path : Path
            The directory where the result should be saved.
        result : Any
            The raw result returned by `launch_exploration`.

        Returns
        -------
        str
            The path of the saved result file as a POSIX string.
        """
        raise NotImplementedError

    @abstractmethod
    def get_results(
        self, exploration_path: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Load a previously saved exploration result and return it for the frontend.

        Parameters
        ----------
        exploration_path : str
            Path to the file saved by `save_notebook`.
        options : Dict[str, Any]
            Optional rendering or filtering options
            passed from the frontend.

        Returns
        -------
        Dict[str, Any]
            A dict with keys ``"data"`` (serialized result),
            ``"type"`` (result type string, e.g. ``"plotly_json"``), and
            ``"config"`` (frontend rendering config).
        """
        raise NotImplementedError

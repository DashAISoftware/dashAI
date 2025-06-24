from abc import abstractmethod
from typing import Any, Dict, Final, List, Tuple

from DashAI.back.dependencies.database.models import ProcessData


class BaseGenerativeTask:
    """Base task for generative processes."""

    TYPE: Final[str] = "GenerativeTask"

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

    @abstractmethod
    def prepare_for_task(
        self,
        input: List[ProcessData],
        **kwargs: Any,
    ) -> Any:
        """Prepare input data for the task.

        Parameters
        ----------
        input : List[ProcessData]
            Input data to be prepared, a list of ProcessData objects

        Returns
        -------
        Any
            Prepared input data
        """
        raise NotImplementedError

    @abstractmethod
    def prepare_input_for_database(
        self,
        input: List[Any],
        **kwargs: Any,
    ) -> List[Tuple[str, str]]:
        """Prepare input data for the database.

        Parameters
        ----------
        input : List[Any]
            Input data to be prepared

        Returns
        -------
        List[Tuple[str, str]]
            Prepared input data as a list of tuples containing the data and its type
        """
        raise NotImplementedError

    @abstractmethod
    def process_output(
        self,
        output: List[Any],
        **kwargs: Any,
    ) -> List[Tuple[str, str]]:
        """Process output data of the task.

        Parameters
        ----------
        output : List[Any]
            Output data to be processed

        Returns
        -------
        List[Tuple[str, str]]
            Processed output data as a list of tuples containing the data and its type
        """
        raise NotImplementedError

    @abstractmethod
    def process_output_from_database(
        self,
        output: List[ProcessData],
        **kwargs: Any,
    ) -> List[ProcessData]:
        """Process output data from the database.

        Parameters
        ----------
        output : List[ProcessData]
            Output data to be processed, a list of ProcessData objects

        Returns
        -------
        List[ProcessData]
            Processed output data, a list of ProcessData objects
        """
        raise NotImplementedError

    @abstractmethod
    def process_input_from_database(
        self,
        input: List[ProcessData],
        **kwargs: Any,
    ) -> List[ProcessData]:
        """Process input data from the database.

        Parameters
        ----------
        input : List[ProcessData]
            Input data to be processed, a list of ProcessData objects

        Returns
        -------
        List[ProcessData]
            Processed input data, a list of ProcessData objects
        """
        raise NotImplementedError

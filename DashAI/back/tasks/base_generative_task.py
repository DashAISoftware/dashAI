from abc import abstractmethod
from typing import Any, Dict, Final, List, Optional


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
        input: Any,
        **kwargs: Any,
    ) -> Any:
        """Prepare input data for the task.

        Parameters
        ----------
        input : Any
            Input data to be prepared

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
    ) -> List[Any]:
        """Prepare input data for the database.

        Parameters
        ----------
        input : List[Any]
            Input data to be prepared

        Returns
        -------
        List[Any]
            Prepared input data
        """
        raise NotImplementedError

    @abstractmethod
    def process_output(
        self,
        output: List[Any],
        path: Optional[str] = None,
        **kwargs: Any,
    ) -> List[str]:
        """Process output data of the task.

        Parameters
        ----------
        output : List[Any]
            Output data to be processed
        path : Optional[str], optional
            Path to save the output data, by default None

        Returns
        -------
        List[str]
            Processed output data
        """
        raise NotImplementedError

    @abstractmethod
    def process_output_from_database(
        self,
        output: List[str],
        **kwargs: Any,
    ) -> List[str]:
        """Process output data from the database.

        Parameters
        ----------
        output : List[str]
            Output data to be processed

        Returns
        -------
        List[str]
            Processed output data
        """
        raise NotImplementedError

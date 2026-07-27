from abc import abstractmethod
from typing import Any, Dict, Final


class BaseAgentTask:
    """Base task for agent processes."""

    TYPE: Final[str] = "AgentTask"

    @property
    @abstractmethod
    def schema(self) -> Dict[str, Any]:
        """Return the schema of components compatible with this agent task.

        Concrete subclasses must implement this property to return a mapping
        that describes which models and other components are compatible with
        the task.

        Returns
        -------
        Dict[str, Any]
            A dictionary whose keys are component category names and whose
            values are lists or mappings of the compatible component classes
            or identifiers.

        Raises
        ------
        NotImplementedError
            If the subclass does not provide an implementation.
        """
        raise NotImplementedError

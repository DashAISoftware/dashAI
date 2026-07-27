from abc import ABCMeta, abstractmethod
from typing import Any, Final, List

from DashAI.back.config_object import ConfigObject


class BaseAgenticModel(ConfigObject, metaclass=ABCMeta):
    """Abstract base class for all agentic models in DashAI.

    Agentic models differ from standard generative models in that they
    can do actions allowed in DashAI application and answer queries.
    """

    TYPE: Final[str] = "AgenticModel"

    @classmethod
    def get_metadata(cls) -> dict[str, Any]:
        """Get metadata values for the current agentic model."""
        metadata = getattr(cls, "METADATA", {})
        if isinstance(metadata, dict):
            return metadata
        return {}

    @abstractmethod
    def __init__(self, **kwargs):
        """Initialize the generative model with configuration parameters.

        Parameters
        ----------
        **kwargs
            Model-specific configuration keyword arguments as
            defined in the model's SCHEMA.
        """
        raise NotImplementedError

    @abstractmethod
    def generate(self, user_prompt: list[dict[str, str]]) -> List[Any]:
        """Generate the final answer of the agent or ask for approval.

        Parameters
        ----------
        user_prompt : list[dict[str, str]]
            The user prompt

        Returns
        -------
        List[Any]
            A list of generated outputs or a Interrupt.
        """
        raise NotImplementedError

from abc import ABCMeta, abstractmethod
from typing import Any, Final

from DashAI.back.config_object import ConfigObject


class BaseGenerativeModel(ConfigObject, metaclass=ABCMeta):

    TYPE: Final[str] = "GenerativeModel"

    @abstractmethod
    def __init__(self, **kwargs):
        """Initialize the generative model.
        model_id (str): The ID of the model.
        """
        raise NotImplementedError

    @abstractmethod
    def generate(self, input: Any) -> Any:
        """Generate output from a generative model.

        input (Any): Input to the generative model.
        """
        raise NotImplementedError

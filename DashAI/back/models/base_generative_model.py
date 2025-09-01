from abc import ABCMeta, abstractmethod
from typing import Any, Final, List, Tuple, Union

from DashAI.back.config_object import ConfigObject


class BaseGenerativeModel(ConfigObject, metaclass=ABCMeta):
    TYPE: Final[str] = "GenerativeModel"

    @abstractmethod
    def __init__(self, **kwargs):
        """Initialize the generative model."""
        raise NotImplementedError

    @abstractmethod
    def generate(self, input: Union[Any, Tuple[Any, Any]]) -> List[Any]:
        """Generate output from a generative model.

        Parameters
        ----------
        input : Any
            Input data to be generated

        Returns
        -------
        List[Any]
            Generated output data in a list
        """
        raise NotImplementedError

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Final, List, Tuple

from DashAI.back.config_object import ConfigObject
from DashAI.back.models.base_model import BaseModel

if TYPE_CHECKING:
    from datasets import DatasetDict


class BaseGlobalExplainer(ConfigObject, ABC):
    """Base class for global explainers."""

    TYPE: Final[str] = "GlobalExplainer"

    def __init__(self, model: BaseModel) -> None:
        """Initialise the global explainer with the model to be explained.

        Parameters
        ----------
        model : BaseModel
            The trained DashAI model whose predictions will be explained.
        """
        self.model = model

    @abstractmethod
    def explain(self, dataset: Tuple["DatasetDict", "DatasetDict"]) -> dict:
        """Compute a global explanation for the given dataset.

        Concrete implementations must analyse the model's behaviour across
        the full dataset and return a structured explanation dictionary.

        Parameters
        ----------
        dataset : Tuple[DatasetDict, DatasetDict]
            A two-element tuple ``(x, y)`` where ``x`` contains the input
            splits (e.g. ``x["test"]``) and ``y`` contains the corresponding
            target splits.

        Returns
        -------
        dict
            A dictionary of explanation data.  The exact keys depend on the
            explainer, but typically include feature names and their associated
            importance scores (e.g. ``"features"``, ``"importances_mean"``,
            ``"importances_std"``).

        Raises
        ------
        NotImplementedError
            If the subclass does not provide an implementation.
        """
        raise NotImplementedError

    @abstractmethod
    def plot(self, explanation: dict) -> List[dict]:
        """Generate serialised plots from a previously computed explanation.

        Concrete implementations must convert the explanation dictionary
        returned by :meth:`explain` into one or more serialised plot objects
        that can be rendered on the frontend.

        Parameters
        ----------
        explanation : dict
            The explanation dictionary produced by :meth:`explain`.

        Returns
        -------
        List[dict]
            A list of serialised plot objects.  Each element is a JSON string
            (produced by ``plotly.io.to_json``) representing a single Plotly
            figure.

        Raises
        ------
        NotImplementedError
            If the subclass does not provide an implementation.
        """
        raise NotImplementedError

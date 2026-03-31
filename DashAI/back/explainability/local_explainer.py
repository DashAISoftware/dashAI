from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Final, List, Tuple

from DashAI.back.config_object import ConfigObject
from DashAI.back.models.base_model import BaseModel

if TYPE_CHECKING:
    from datasets import DatasetDict


class BaseLocalExplainer(ConfigObject, ABC):
    """Base class for local explainers."""

    TYPE: Final[str] = "LocalExplainer"

    def __init__(self, model: BaseModel) -> None:
        """Initialise the local explainer with the model to be explained.

        Parameters
        ----------
        model : BaseModel
            The trained DashAI model whose predictions will be explained.
        """
        self.model = model
        self.explanation = None

    def fit(self, dataset: Tuple["DatasetDict", "DatasetDict"], *args, **kwargs):
        """Fit the explainer on the full dataset (optional pre-computation step).

        The default implementation is a no-op that simply returns ``self``.
        Subclasses may override this method to pre-compute any background data
        or internal state required before calling :meth:`explain_instance`.

        Parameters
        ----------
        dataset : Tuple[DatasetDict, DatasetDict]
            A two-element tuple ``(x, y)`` containing the full dataset splits
            used to fit or calibrate the explainer.
        *args : Any
            Additional positional arguments passed to concrete implementations.
        **kwargs : Any
            Additional keyword arguments passed to concrete implementations.

        Returns
        -------
        BaseLocalExplainer
            The fitted explainer instance (``self``).
        """
        return self

    @abstractmethod
    def explain_instance(self, instances: "DatasetDict") -> dict:
        """Compute a local explanation for the given instances.

        Concrete implementations must produce a per-instance explanation that
        describes how the model arrived at its prediction for each input.

        Parameters
        ----------
        instances : DatasetDict
            One or more instances to explain, provided as a ``DatasetDict``
            containing the input features.

        Returns
        -------
        dict
            A dictionary of explanation data for the provided instances.
            The exact keys depend on the explainer, but typically include
            feature attributions or importance scores for each instance.

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
        returned by :meth:`explain_instance` into one or more serialised plot
        objects that can be rendered on the frontend.

        Parameters
        ----------
        explanation : dict
            The explanation dictionary produced by :meth:`explain_instance`.

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

"""Shared behaviour for models that forecast a series from its own history."""

from typing import TYPE_CHECKING, Any, List

from DashAI.back.models.base_model import BaseModel

if TYPE_CHECKING:
    import numpy as np

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class ForecastingModel(BaseModel):
    """Base class for models that predict the future of a single series.

    These models are unusual among DashAI models in that they do not learn a
    mapping from features to a target. There are no features: the only input
    is a date column, and everything the model knows comes from the history of
    the series itself. Two consequences shape the interface.

    ``train`` reads the series out of ``y_train`` and ignores the feature
    matrix, because there is nothing in it to learn from.

    ``predict`` treats its argument as a request for a length rather than as
    data to score. It is handed the rows to forecast, usually a partition's
    date column, and returns one value per row, continuing from where the
    training history ended. Nothing about those rows changes the answer, which
    is what makes these models different from a regressor: the forecast for
    step three depends on steps one and two, not on any column.

    That is why the windowed route through ``TimeSeriesWindowConverter`` and
    ``RegressionTask`` exists alongside this one. It turns the history into
    real features, which is the only way an ordinary regressor can help.
    """

    COMPATIBLE_COMPONENTS = ["ForecastingTask"]

    def __init__(self, **kwargs):
        """Initialize the shared forecasting state."""
        super().__init__(**kwargs)
        self._history: List[float] = []
        self._fitted = False

    @staticmethod
    def _series(y: "DashAIDataset") -> "np.ndarray":
        """Read a target dataset as a flat array of numbers.

        Parameters
        ----------
        y : DashAIDataset
            The target dataset, holding the single series column.

        Returns
        -------
        np.ndarray
            The series values as floats, in row order.
        """
        import numpy as np

        return np.asarray(y.to_pandas().iloc[:, 0], dtype=float)

    def _require_fitted(self) -> None:
        """Refuse to forecast before there is any history to forecast from.

        Raises
        ------
        ValueError
            If ``train`` has not been called.
        """
        if not self._fitted:
            raise ValueError(
                f"{type(self).__name__} has no history to forecast from. "
                "Call train before predict."
            )

    @staticmethod
    def _horizon(x: "DashAIDataset") -> int:
        """Read how many steps to forecast from the rows requested.

        Parameters
        ----------
        x : DashAIDataset
            The rows to forecast, whose contents are irrelevant; only how many
            there are matters.

        Returns
        -------
        int
            The number of steps to forecast.
        """
        return len(x)

    def save(self, filename: str) -> None:
        """Serialise the model to disk using joblib.

        Parameters
        ----------
        filename : str
            Destination file path where the model will be written.
        """
        import joblib

        joblib.dump(self, filename)

    @staticmethod
    def load(filename: str) -> Any:
        """Deserialise a model from disk using joblib.

        Parameters
        ----------
        filename : str
            Path to the file previously written by :meth:`save`.

        Returns
        -------
        ForecastingModel
            The loaded model instance.
        """
        import joblib

        return joblib.load(filename)

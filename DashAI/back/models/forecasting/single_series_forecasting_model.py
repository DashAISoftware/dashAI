"""The contract of a model that forecasts a single series from its history."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Optional, Sequence

from DashAI.back.models.base_model import BaseModel

if TYPE_CHECKING:
    import numpy as np

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

# What a model does with exogenous variables, as it declares in EXOGENOUS.
EXOGENOUS_NONE = "none"
EXOGENOUS_OPTIONAL = "optional"
EXOGENOUS_REQUIRED = "required"


@dataclass(frozen=True)
class Forecast:
    """What a forecaster returns for the next ``h`` steps.

    Attributes
    ----------
    point : numpy.ndarray
        One value per step, in order.
    lower, upper : dict of int to numpy.ndarray
        The bounds of the prediction interval at each requested level, in
        percent, one value per step. Empty when no level was asked for.
    """

    point: "np.ndarray"
    lower: Dict[int, "np.ndarray"] = field(default_factory=dict)
    upper: Dict[int, "np.ndarray"] = field(default_factory=dict)


class SingleSeriesForecastingModel(BaseModel):
    """Base class for models that forecast one series from its own history.

    **The model never sees a date.** It is fitted on the values of the series
    in time order and forecasts a number of steps past the end of them. The
    task turns the dates into a validated grid before fitting, and the unit
    that forecasts turns the steps back into dates with the grid's frequency
    and last date. A model that read dates would have to guess the grid, and
    the old one did: rows with no date were counted as consecutive steps,
    without a word.

    **What a model declares.**
    - ``EXOGENOUS``: whether it ignores exogenous variables (``"none"``), uses
      them when a session has them (``"optional"``) or needs them
      (``"required"``). ``fit`` and ``predict`` take them already, as ``x``
      and ``x_future``; sessions give them a role later.
    - ``SUPPORTS_INTERVALS``: whether it can bound its forecasts.

    **What a subclass implements.** ``_fit(y, x)``, ``_forecast(h, x_future)``
    and, with intervals, ``_intervals(h, levels, x_future)``. The checks on
    the arguments live here, once.

    ``train`` is the ``BaseModel`` entry point. It reads the series out of a
    one-column dataset and fits on it; the dates it is handed are ignored.
    """

    COMPATIBLE_COMPONENTS = ["SingleSeriesForecastingTask"]

    EXOGENOUS: str = EXOGENOUS_NONE
    SUPPORTS_INTERVALS: bool = False

    def __init__(self, **kwargs):
        """Initialise the forecaster with no history."""
        super().__init__(**kwargs)
        self._fitted = False
        self._n_obs = 0

    # --- the contract --------------------------------------------------------

    def fit(
        self, y: Sequence[float], x: Optional[Any] = None
    ) -> "SingleSeriesForecastingModel":
        """Fit the model on the series, in time order.

        Parameters
        ----------
        y : sequence of float
            The series, one value per step of its grid.
        x : array-like, optional
            Exogenous variables, one row per step. Refused by a model that
            declares ``EXOGENOUS = "none"``, and required by one that declares
            ``"required"``.

        Returns
        -------
        SingleSeriesForecastingModel
            The fitted model.

        Raises
        ------
        ValueError
            If the series is empty or holds a value that is not finite, or if
            ``x`` does not match what the model declares.
        """
        import numpy as np

        values = np.asarray(y, dtype=float)
        if values.ndim != 1:
            raise ValueError(
                f"{type(self).__name__} fits one series, but was handed an "
                f"array of shape {values.shape}."
            )
        if len(values) == 0:
            raise ValueError(f"{type(self).__name__} needs at least one observation.")
        if not np.isfinite(values).all():
            raise ValueError(
                f"{type(self).__name__} was handed a series with "
                f"{int((~np.isfinite(values)).sum())} value(s) that are not "
                "finite. The task validates the series before fitting, so this "
                "is a wiring error."
            )
        self._check_exogenous(x, len(values), "x")

        self._fit(values, x)
        self._n_obs = len(values)
        self._fitted = True
        return self

    def predict(
        self,
        h: int,
        x_future: Optional[Any] = None,
        levels: Optional[Sequence[int]] = None,
    ) -> Forecast:
        """Forecast the ``h`` steps that follow the fitted series.

        Parameters
        ----------
        h : int
            How many steps to forecast, at least 1.
        x_future : array-like, optional
            Exogenous variables for the forecast steps, one row per step.
        levels : sequence of int, optional
            Prediction interval levels, in percent, each between 0 and 100.

        Returns
        -------
        Forecast
            The point forecast and, if levels were asked for, the intervals.

        Raises
        ------
        TypeError
            If ``h`` is not an integer, for instance rows of dates: the model
            counts steps and never reads a date.
        ValueError
            If the model is not fitted, ``h`` is below 1, a level is out of
            range, the model gives no intervals and some were asked for, or
            ``x_future`` does not match what the model declares.
        """
        import numpy as np

        if isinstance(h, bool) or not isinstance(h, (int, np.integer)):
            raise TypeError(
                f"{type(self).__name__}.predict takes a number of steps, not "
                f"{type(h).__name__}. A forecaster never reads dates: the unit "
                "that forecasts turns steps into dates with the series' grid."
            )
        if not self._fitted:
            raise ValueError(
                f"{type(self).__name__} has no history to forecast from. "
                "Fit it before predicting."
            )
        if h < 1:
            raise ValueError(f"The horizon has to be at least 1 step, got {h}.")

        levels = [int(level) for level in (levels or [])]
        for level in levels:
            if not 0 < level < 100:
                raise ValueError(
                    f"A prediction interval level is a percentage between 0 "
                    f"and 100, got {level}."
                )
        if levels and not self.SUPPORTS_INTERVALS:
            raise ValueError(f"{type(self).__name__} gives no prediction intervals.")
        self._check_exogenous(x_future, h, "x_future")

        point = np.asarray(self._forecast(int(h), x_future), dtype=float)
        if not levels:
            return Forecast(point=point)
        lower, upper = self._intervals(int(h), levels, x_future)
        return Forecast(point=point, lower=lower, upper=upper)

    def train(
        self,
        x_train: "DashAIDataset",
        y_train: "DashAIDataset",
        x_validation: "DashAIDataset" = None,
        y_validation: "DashAIDataset" = None,
    ) -> "SingleSeriesForecastingModel":
        """Fit on the series held by ``y_train``, ignoring every other input.

        Parameters
        ----------
        x_train : DashAIDataset
            Ignored: the model never sees dates.
        y_train : DashAIDataset
            One column holding the series, in time order.
        x_validation, y_validation : DashAIDataset, optional
            Ignored.

        Returns
        -------
        SingleSeriesForecastingModel
            The fitted model.
        """
        return self.fit(y_train.to_pandas().iloc[:, 0].to_numpy(dtype=float))

    # --- what a subclass implements ------------------------------------------

    def _fit(self, y: "np.ndarray", x: Optional[Any]) -> None:
        """Fit on a validated series. ``x`` is None unless the model uses it."""
        raise NotImplementedError(
            f"{type(self).__name__} must say how it fits a series."
        )

    def _forecast(self, h: int, x_future: Optional[Any]) -> "np.ndarray":
        """The point forecast of the next ``h`` steps."""
        raise NotImplementedError(
            f"{type(self).__name__} must say how it forecasts a number of steps."
        )

    def _intervals(
        self, h: int, levels: Sequence[int], x_future: Optional[Any]
    ) -> "tuple[Dict[int, np.ndarray], Dict[int, np.ndarray]]":
        """The lower and upper bounds at each level, for the next ``h`` steps."""
        raise NotImplementedError(
            f"{type(self).__name__} declares intervals but does not compute them."
        )

    # --- shared helpers ------------------------------------------------------

    def _check_exogenous(self, x: Optional[Any], rows: int, name: str) -> None:
        """Refuse exogenous variables that do not match the declaration."""
        if x is None:
            if self.EXOGENOUS == EXOGENOUS_REQUIRED:
                raise ValueError(
                    f"{type(self).__name__} requires exogenous variables, but "
                    f"{name} is empty."
                )
            return
        if self.EXOGENOUS == EXOGENOUS_NONE:
            raise ValueError(
                f"{type(self).__name__} uses no exogenous variables, but was "
                f"handed {name}."
            )
        if len(x) != rows:
            raise ValueError(
                f"{name} has {len(x)} row(s), but {rows} step(s) need one each."
            )

    @staticmethod
    def _normal_bounds(
        point: "np.ndarray", sd: "np.ndarray", levels: Sequence[int]
    ) -> "tuple[Dict[int, np.ndarray], Dict[int, np.ndarray]]":
        """Normal prediction intervals around ``point`` with step-wise ``sd``."""
        from scipy.stats import norm

        lower, upper = {}, {}
        for level in levels:
            z = norm.ppf(0.5 + level / 200.0)
            lower[level] = point - z * sd
            upper[level] = point + z * sd
        return lower, upper

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
        SingleSeriesForecastingModel
            The loaded model instance.
        """
        import joblib

        return joblib.load(filename)

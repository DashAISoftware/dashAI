"""Shared behaviour for models that forecast a series from its own history."""

from typing import TYPE_CHECKING, Any, List

from DashAI.back.models.base_model import BaseModel

if TYPE_CHECKING:
    import numpy as np
    import pandas as pd

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class ForecastingModel(BaseModel):
    """Base class for models that predict the future of a single series.

    These models are unusual among DashAI models in that they do not learn a
    mapping from features to a target. There are no features: the only input
    is a date column, and everything the model knows comes from the history of
    the series itself. Two consequences shape the interface.

    ``train`` reads the series out of ``y_train``. A model that declares
    ``SUPPORTS_EXOGENOUS`` also reads the numeric columns beside the date as
    explanatory variables; the rest ignore the feature matrix, because for
    them there is nothing in it to learn from.

    ``predict`` reads the **dates** it is handed and works out how far each one
    lies beyond the end of training, then returns the forecast for exactly
    those points. Counting rows instead would be wrong for any partition that
    does not directly follow the training data: with a train, validation and
    test split, the test rows start a whole validation window later, and
    forecasting ``len(test)`` steps would score the model against the wrong
    period entirely.

    That is why the windowed route through ``TimeSeriesWindowConverter`` and
    ``RegressionTask`` exists alongside this one. It turns the history into
    real features, which is the only way an ordinary regressor can help.

    Each model names the tasks it serves itself rather than inheriting a list
    from here. A model that reads only the date belongs to ``ForecastingTask``
    alone, one that requires explanatory variables to
    ``ExogenousForecastingTask`` alone, and one that can do either belongs to
    both.
    """

    SUPPORTS_EXOGENOUS: bool = False

    def __init__(self, **kwargs):
        """Initialize the shared forecasting state."""
        super().__init__(**kwargs)
        self._history: List[float] = []
        self._fitted = False
        self._exogenous_columns: List[str] = []
        # Where the training data ends and how far apart its rows sit, which
        # is what lets predict turn a date into a number of steps ahead.
        self._last_train_date = None
        self._step_delta = None
        self._freq_alias = None
        self._date_format = None

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

    def _remember_dates(self, x_train: "DashAIDataset") -> None:
        """Record where the training data ends and how far apart its rows are.

        Both are needed to answer "how many steps ahead is this date", which is
        what turns a requested partition into positions in a forecast.

        Parameters
        ----------
        x_train : DashAIDataset
            The training input, holding the date column.
        """
        from DashAI.back.types.date_utils import (
            DEFAULT_DATE_FORMAT,
            infer_frequency,
            parse_date_column,
        )
        from DashAI.back.types.value_types import Date

        date_columns = [
            name
            for name in x_train.column_names
            if isinstance(x_train.types.get(name), Date)
        ]
        if not date_columns:
            # Nothing to align against; predict falls back to counting rows.
            self._last_train_date = None
            self._step_delta = None
            self._freq_alias = None
            return

        self._date_format = (
            getattr(x_train.types[date_columns[0]], "format", None)
            or DEFAULT_DATE_FORMAT
        )
        dates = parse_date_column(
            x_train.to_pandas()[date_columns[0]], self._date_format
        ).sort_values()

        self._last_train_date = dates.iloc[-1]
        # The typical gap rather than the mean: monthly rows sit 28 to 31 days
        # apart, and the median lands on a real period instead of between two.
        gaps = dates.diff().dropna()
        self._step_delta = gaps.median() if not gaps.empty else None
        if self._step_delta is not None and self._step_delta.total_seconds() <= 0:
            self._step_delta = None

        # A calendar period is not a fixed number of days, so measuring in
        # days drifts: months run 28 to 31, the median lands on 31, and after
        # a couple of years the count is a whole period short. When the rows
        # sit on a regular grid the alias names that grid, and a position on
        # it is exact however long the horizon gets.
        alias = infer_frequency(dates)
        self._freq_alias = alias if isinstance(alias, str) else None

    def _steps_from_grid(self, dates: "pd.Series") -> "np.ndarray | None":
        """Read each date as a position on the calendar grid of the training rows.

        Counting positions rather than dividing durations is what keeps a
        monthly or quarterly series aligned: those periods are not a fixed
        number of days, so a duration divided by the typical gap drifts by a
        whole period over a long enough horizon.

        Parameters
        ----------
        dates : pd.Series
            The requested dates, already parsed.

        Returns
        -------
        np.ndarray or None
            One step number per date, or ``None`` when the grid cannot answer:
            no regular frequency, a missing date, or a date that does not land
            on the grid. The caller then measures by duration instead.
        """
        import pandas as pd

        if self._freq_alias is None or dates.isna().any():
            return None

        grid = pd.date_range(
            start=self._last_train_date, end=dates.max(), freq=self._freq_alias
        )
        # The grid starts at the last training date, so a position on it is
        # already a number of steps past the end of training. date_range rolls
        # a start that is off the grid forward, which would break that.
        if len(grid) == 0 or grid[0] != self._last_train_date:
            return None

        positions = grid.get_indexer(pd.DatetimeIndex(dates))
        if (positions < 0).any():
            return None

        return positions

    def _dates_of(self, x: "DashAIDataset") -> "pd.Series | None":
        """Read and parse the date column of a set of rows.

        Parameters
        ----------
        x : DashAIDataset
            Rows holding the date column.

        Returns
        -------
        pd.Series or None
            The parsed dates, or None when the rows carry no date column.
        """
        from DashAI.back.types.date_utils import parse_date_column
        from DashAI.back.types.value_types import Date

        date_columns = [
            name for name in x.column_names if isinstance(x.types.get(name), Date)
        ]
        if not date_columns:
            return None
        return parse_date_column(x.to_pandas()[date_columns[0]], self._date_format)

    def _steps_of(self, dates: "pd.Series") -> "np.ndarray":
        """Count how many periods past the end of training each date falls.

        Unlike :meth:`_steps_ahead` this reports what it finds, including the
        zero and negative counts of dates inside the fitted window, because
        the caller may be looking for exactly those.

        Parameters
        ----------
        dates : pd.Series
            Dates already parsed.

        Returns
        -------
        np.ndarray
            One step number per date, in the order given.
        """
        import numpy as np

        steps = self._steps_from_grid(dates)
        if steps is None:
            offsets = (dates - self._last_train_date) / self._step_delta
            steps = np.rint(offsets.to_numpy(dtype=float)).astype(int)
        return steps

    def _steps_ahead(self, x: "DashAIDataset") -> "np.ndarray":
        """Work out how many periods past training each requested date falls.

        Parameters
        ----------
        x : DashAIDataset
            The rows to forecast, holding the date column.

        Returns
        -------
        np.ndarray
            One 1-based step number per requested row, in the order given.

        Raises
        ------
        ValueError
            If any requested date falls at or before the end of the training
            data. These models forecast forward only, so returning a number
            for a past date would be passing off a fit as a forecast.
        """
        import numpy as np

        dates = None
        if self._last_train_date is not None and self._step_delta is not None:
            dates = self._dates_of(x)
        if dates is None:
            # No dates to align against, so the rows can only mean "the next
            # len(x) periods", which is what they meant before.
            return np.arange(1, len(x) + 1)

        steps = self._steps_of(dates)

        if (steps < 1).any():
            raise ValueError(
                f"{type(self).__name__} forecasts forward only, but "
                f"{int((steps < 1).sum())} of the requested dates fall inside "
                "the training data rather than after it. A value for those "
                "dates would be a fit, not a forecast."
            )

        return steps

    def predict(self, x: "DashAIDataset") -> "np.ndarray":
        """Forecast the requested dates from the end of the training data.

        A partition that does not directly follow the training data is
        reached by forecasting across the gap, so the model's own forecasts
        stand in for the periods in between and the error compounds over a
        horizon nobody asked about. That is what a model fitted on the
        training partition alone can say, and every other task predicts
        from that same fit.

        Parameters
        ----------
        x : DashAIDataset
            The rows to forecast, whose dates say how far ahead each one is.

        Returns
        -------
        np.ndarray
            One forecast value per requested row.
        """
        self._require_fitted()
        return self._forecast_at(x)

    def _forecast(self, steps: int, exog: "np.ndarray | None" = None) -> "np.ndarray":
        """Forecast the next ``steps`` periods after the end of the history.

        Parameters
        ----------
        steps : int
            How many periods to forecast.
        exog : np.ndarray, optional
            The explanatory variables over those periods, one row per step.
            Passed only to a model that declares ``SUPPORTS_EXOGENOUS`` and
            was fitted with variables.

        Returns
        -------
        np.ndarray
            One value per period, in order.

        Raises
        ------
        NotImplementedError
            If the subclass does not provide an implementation.
        """
        raise NotImplementedError(
            "A forecasting model must say how it forecasts a number of steps."
        )

    def _forecast_at(self, x: "DashAIDataset") -> "np.ndarray":
        """Pick the forecast values for the requested dates.

        Parameters
        ----------
        x : DashAIDataset
            The rows that were requested.

        Returns
        -------
        np.ndarray
            One value per requested row, in the order the rows were given.
        """
        import numpy as np

        steps = self._steps_ahead(x)
        horizon = int(steps.max())

        if self._exogenous_columns:
            values = self._forecast(horizon, self._exogenous_over(x, steps, horizon))
        else:
            values = self._forecast(horizon)

        return np.asarray(values, dtype=float)[steps - 1]

    def _remember_exogenous(self, x_train: "DashAIDataset") -> None:
        """Record which input columns are explanatory variables.

        Everything that is not the date column is one. A model that does not
        support them records none, so it goes on forecasting from the history
        alone even if the columns are there.

        Parameters
        ----------
        x_train : DashAIDataset
            The training input.
        """
        from DashAI.back.types.value_types import Date

        if not self.SUPPORTS_EXOGENOUS:
            self._exogenous_columns = []
            return

        self._exogenous_columns = [
            name
            for name in x_train.column_names
            if not isinstance(x_train.types.get(name), Date)
        ]

    def _exogenous_of(self, x: "DashAIDataset") -> "np.ndarray | None":
        """Read the explanatory variables out of a set of rows.

        Parameters
        ----------
        x : DashAIDataset
            Rows holding the columns recorded at training time.

        Returns
        -------
        np.ndarray or None
            One row per observation and one column per variable, in the order
            the columns were recorded, or ``None`` when there are none.

        Raises
        ------
        ValueError
            If a column the model was fitted with is missing.
        """
        if not self._exogenous_columns:
            return None

        frame = x.to_pandas()
        missing = [name for name in self._exogenous_columns if name not in frame]
        if missing:
            raise ValueError(
                f"{type(self).__name__} was fitted with the explanatory "
                f"variables {self._exogenous_columns}, but "
                f"{missing} are not among the columns it was given."
            )

        return frame[self._exogenous_columns].to_numpy(dtype=float)

    def _exogenous_over(
        self, x: "DashAIDataset", steps: "np.ndarray", horizon: int
    ) -> "np.ndarray":
        """Lay the explanatory variables out over every step of the horizon.

        A model forecasts a whole horizon and the requested rows are read off
        it, so the variables have to cover the horizon too. The requested rows
        need not: a test partition that starts a validation window after the
        training data leaves the periods in between with no values at all.
        Those are filled by interpolating between the rows that do have them.

        The filled rows are scaffolding, not data. An explanatory variable
        enters a forecast at the period it belongs to, so the value returned
        for a requested step is built from that step's own row and from the
        history of the series, never from a filled row. The filled rows
        produce the values at their own steps, which are discarded. Whatever
        they hold, the requested rows come back the same.

        Parameters
        ----------
        x : DashAIDataset
            The rows that were requested.
        steps : np.ndarray
            How many periods past training each requested row falls.
        horizon : int
            The furthest step being forecast.

        Returns
        -------
        np.ndarray
            One row per step from 1 to ``horizon``, in that order.
        """
        import pandas as pd

        given = pd.DataFrame(self._exogenous_of(x), index=steps)
        given = given[~given.index.duplicated()]

        return (
            given.reindex(range(1, horizon + 1))
            .interpolate(limit_direction="both")
            .to_numpy(dtype=float)
        )

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

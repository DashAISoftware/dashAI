from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Mapping, Sequence, Union

from DashAI.back.core.utils import MultilingualString
from DashAI.back.tasks.column_roles import ColumnRole, IOColumns
from DashAI.back.tasks.forecasting_task import ForecastingTask
from DashAI.back.tasks.time_grid import TimeGrid
from DashAI.back.types.value_types import Date, Float, Integer

if TYPE_CHECKING:
    from datasets import DatasetDict
    from numpy import ndarray

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

TIME_INDEX = "time_index"
SERIES = "series"


@dataclass(frozen=True)
class PreparedSeries:
    """A series ready for a forecaster.

    Attributes
    ----------
    dataset : DashAIDataset
        The validated rows, in date order.
    values : numpy.ndarray
        The series' values in time order, one per step of ``grid``.
    grid : TimeGrid
        The regular grid the series sits on.
    """

    dataset: "DashAIDataset"
    values: "ndarray"
    grid: TimeGrid


class SingleSeriesForecastingTask(ForecastingTask):
    """Forecast the future values of a single time series.

    The session names two columns: the time index, a ``Date``, and the series,
    a number. Both are protected from the session's preprocessing. Nothing else
    is offered to the model, so the only information it has is the history of
    the series itself. Exogenous variables arrive as a third role later.

    The name says the axis on which the kinds of forecasting differ: one series
    here, several in a panel task that would sit beside this one under
    ``ForecastingTask``.
    """

    DESCRIPTION: str = MultilingualString(
        en=(
            "Predict the future values of a time series from its own history. "
            "Takes one date column and one numeric column, with no other "
            "variables."
        ),
        es=(
            "Predice los valores futuros de una serie temporal a partir de su "
            "propia historia. Toma una columna de fecha y una columna "
            "numerica, sin ninguna otra variable."
        ),
        pt=(
            "Preve os valores futuros de uma serie temporal a partir da sua "
            "propria historia. Recebe uma coluna de data e uma coluna "
            "numerica, sem nenhuma outra variavel."
        ),
        de=(
            "Sagt die zukuenftigen Werte einer Zeitreihe aus ihrer eigenen "
            "Vergangenheit voraus. Nimmt eine Datumsspalte und eine numerische "
            "Spalte, ohne weitere Variablen."
        ),
        zh=(
            "根据时间序列自身的历史预测其未来值。"
            "接受一个日期列和一个数值列，不使用其他变量。"
        ),
    )
    DISPLAY_NAME: str = MultilingualString(
        en="Forecasting",
        es="Pronostico",
        pt="Previsao",
        de="Zeitreihenprognose",
        zh="时间序列预测",
    )

    COLUMN_ROLES = (
        ColumnRole(
            name=TIME_INDEX,
            label=MultilingualString(
                en="Time index",
                es="Índice temporal",
                pt="Índice temporal",
                de="Zeitindex",
                zh="时间索引",
            ),
            types=(Date,),
            min=1,
            max=1,
            transformable=False,
        ),
        ColumnRole(
            name=SERIES,
            label=MultilingualString(
                en="Series",
                es="Serie",
                pt="Série",
                de="Zeitreihe",
                zh="序列",
            ),
            types=(Float, Integer),
            min=1,
            max=1,
            transformable=False,
        ),
    )

    # The shared point metrics, listed here rather than naming this task from
    # the metric: ``RegressionMetric`` names only ``RegressionTask``.
    COMPATIBLE_COMPONENTS = ["MAE", "RMSE"]

    @classmethod
    def io_roles(cls) -> Dict[str, List[str]]:
        """The time index feeds a model's inputs and the series its outputs."""
        return {"inputs": [TIME_INDEX], "outputs": [SERIES]}

    def io_columns(self, roles: Mapping[str, Sequence]) -> IOColumns:
        """The time index as the model's input and the series as its output."""
        return IOColumns(
            inputs=list(roles.get(TIME_INDEX) or []),
            outputs=list(roles.get(SERIES) or []),
        )

    def roles_from_io(
        self, input_columns: Sequence, output_columns: Sequence
    ) -> Dict[str, list]:
        """The roles that a model's input and output came from."""
        return {TIME_INDEX: list(input_columns), SERIES: list(output_columns or [])}

    def prepare_for_task(
        self,
        dataset: Union["DatasetDict", "DashAIDataset"],
        input_columns: List[str],
        output_columns: List[str],
    ) -> "DashAIDataset":
        """Convert the dataset to a DashAIDataset and validate its types.

        Parameters
        ----------
        dataset : DatasetDict or DashAIDataset
            Dataset to prepare.
        input_columns : list of str
            The single date column.
        output_columns : list of str
            The single numeric column holding the series.

        Returns
        -------
        DashAIDataset
            Dataset with validated types, in date order, on a regular grid.

        Raises
        ------
        ValueError
            If the series does not sit on a regular grid (``validate_grid``).
        """
        return self.prepare_series(dataset, input_columns, output_columns).dataset

    def prepare_series(
        self,
        dataset: Union["DatasetDict", "DashAIDataset"],
        input_columns: List[str],
        output_columns: List[str],
    ) -> PreparedSeries:
        """Validate the columns, put the rows in date order and check the grid.

        Everything downstream reads row order as time order: a step of the
        series is a row, and a cut is a number of steps. A file that is not
        sorted by its date column would give cuts that are not periods of
        time and a model fitted on a scrambled series, and one off its grid
        would shift every step after a gap. Both are refused or fixed here,
        before anything is fitted, and never silently.

        This is the task's job rather than the splitter's. The splitter is
        handed the selected input columns, which on the windowed route through
        ``TimeSeriesWindowConverter`` are lag columns with no date among them.

        Sorting reads the format the column declares. Text order only matches
        time order for ISO layouts: as text, "01/02/2020" precedes
        "31/01/2020" while following it in time. The sort is stable.

        Parameters
        ----------
        dataset : DatasetDict or DashAIDataset
            Dataset to prepare.
        input_columns : list of str
            The single date column.
        output_columns : list of str
            The single numeric column holding the series.

        Returns
        -------
        PreparedSeries
            The ordered dataset, the series' values in time order, and the
            grid they sit on.

        Raises
        ------
        TypeError, ValueError
            If the columns do not fit the roles, or the series does not sit on
            a regular grid (``validate_grid``).
        """
        import numpy as np

        from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset
        from DashAI.back.tasks.time_grid import time_order, validate_grid
        from DashAI.back.types.date_utils import DEFAULT_DATE_FORMAT, parse_date_column

        prepared = super().prepare_for_task(dataset, input_columns, output_columns)
        date_column, series_column = input_columns[0], output_columns[0]

        date_format = (
            getattr(prepared.types[date_column], "format", None) or DEFAULT_DATE_FORMAT
        )
        frame = prepared.to_pandas()
        dates = parse_date_column(frame[date_column], date_format)
        order = time_order(dates)

        if order != list(range(len(frame))):
            frame = frame.iloc[order].reset_index(drop=True)
            dates = dates.iloc[order].reset_index(drop=True)
            prepared = to_dashai_dataset(frame, types=dict(prepared.types))

        values = frame[series_column].astype("float64")
        grid = validate_grid(dates, values)
        return PreparedSeries(
            dataset=prepared, values=np.asarray(values, dtype=float), grid=grid
        )

    # ``process_predictions`` and ``num_labels`` serve the x/y units, which
    # still train and predict this task until the backtest and the horizon
    # prediction replace them (RECONCILING_FORECASTING §5). They go then.

    def process_predictions(
        self, dataset: "DashAIDataset", predictions: "ndarray", output_column: str
    ):
        """Return the forecast values unchanged.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset used for training.
        predictions : np.ndarray
            Predictions from the model.
        output_column : str
            Output column.

        Returns
        -------
        np.ndarray
            The predictions as they were produced. A forecast is already a
            number on the scale of the series, so there is nothing to decode.
        """
        return predictions

    def num_labels(self, dataset: "DashAIDataset", output_column: str) -> int | None:
        """Report that this task has no labels.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset used for training.
        output_column : str
            Output column.

        Returns
        -------
        int | None
            Always ``None``: the output is continuous, so there is no class
            count for a model to size itself against.
        """
        return None

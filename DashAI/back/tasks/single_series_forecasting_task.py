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
EXOGENOUS = "exogenous"


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

    The session names the time index, a ``Date``, and the series, a number.
    Both are protected from the session's preprocessing. A third role takes
    the exogenous variables: any number of columns known ahead of time, such
    as the calendar, holidays or planned promotions. The session's
    preprocessing may transform them, and the model reads them as numbers.
    Every step of that preprocessing has to keep the rows, because the cuts
    of a backtest are counted in steps (``PREPROCESSING_KEEPS_ROWS``).

    The name says the axis on which the kinds of forecasting differ: one series
    here, several in a panel task that would sit beside this one under
    ``ForecastingTask``.
    """

    DESCRIPTION: str = MultilingualString(
        en=(
            "Predict the future values of a time series from its own history. "
            "Takes one date column and one numeric column, and optionally "
            "exogenous variables known ahead of time."
        ),
        es=(
            "Predice los valores futuros de una serie temporal a partir de su "
            "propia historia. Toma una columna de fecha y una columna "
            "numérica, y opcionalmente variables exógenas conocidas de "
            "antemano."
        ),
        pt=(
            "Prevê os valores futuros de uma série temporal a partir da sua "
            "própria história. Recebe uma coluna de data e uma coluna "
            "numérica, e opcionalmente variáveis exógenas conhecidas de "
            "antemão."
        ),
        de=(
            "Sagt die zukünftigen Werte einer Zeitreihe aus ihrer eigenen "
            "Vergangenheit voraus. Nimmt eine Datumsspalte und eine numerische "
            "Spalte, und optional im Voraus bekannte exogene Variablen."
        ),
        zh=(
            "根据时间序列自身的历史预测其未来值。"
            "接受一个日期列和一个数值列，并可选择提前已知的外生变量。"
        ),
    )
    ICON: str = "Timeline"
    DISPLAY_NAME: str = MultilingualString(
        en="Forecasting",
        es="Pronóstico",
        pt="Previsão",
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
        ColumnRole(
            name=EXOGENOUS,
            label=MultilingualString(
                en="Exogenous variables",
                es="Variables exógenas",
                pt="Variáveis exógenas",
                de="Exogene Variablen",
                zh="外生变量",
            ),
            description=MultilingualString(
                en=(
                    "Only variables known ahead of time, whose future values "
                    "you will have when you predict: the calendar, holidays, "
                    "planned promotions, prices already set."
                ),
                es=(
                    "Solo variables conocidas de antemano, cuyos valores "
                    "futuros tendrás al predecir: el calendario, los feriados, "
                    "las promociones planificadas, los precios ya fijados."
                ),
                pt=(
                    "Apenas variáveis conhecidas de antemão, cujos valores "
                    "futuros você terá ao prever: o calendário, os feriados, "
                    "as promoções planejadas, os preços já definidos."
                ),
                de=(
                    "Nur im Voraus bekannte Variablen, deren zukünftige Werte "
                    "Sie bei der Vorhersage haben: der Kalender, Feiertage, "
                    "geplante Aktionen, bereits festgelegte Preise."
                ),
                zh=(
                    "仅限提前已知、预测时已有未来值的变量：日历、节假日、"
                    "计划中的促销、已确定的价格。"
                ),
            ),
            # What the model reads, after the session's preprocessing: a
            # Categorical reaches it through an encoder, a Date through
            # ``DateFeaturesConverter``.
            types=(Float, Integer),
            min=0,
            max="n",
            transformable=True,
        ),
    )

    # A backtest's cuts are counted in steps, and a step is a row: a step of
    # the preprocessing that dropped or added rows would shift every cut.
    PREPROCESSING_KEEPS_ROWS = True

    # The shared point metrics, listed here rather than naming this task from
    # the metric: ``RegressionMetric`` names only ``RegressionTask``.
    COMPATIBLE_COMPONENTS = ["MAE", "RMSE", "MAPE", "SMAPE"]

    # A trained model forecasts a number of steps past the end of its series;
    # there are no rows to hand it. A kind of forecasting whose dates are not
    # on a grid could predict otherwise, so this is the concrete task's to say.
    PREDICTION_MODE = "horizon"

    @classmethod
    def io_roles(cls) -> Dict[str, List[str]]:
        """The time index and the exogenous variables feed a model's inputs."""
        return {"inputs": [TIME_INDEX, EXOGENOUS], "outputs": [SERIES]}

    def io_columns(self, roles: Mapping[str, Sequence]) -> IOColumns:
        """The time index first, then the exogenous variables, as the inputs."""
        return IOColumns(
            inputs=list(roles.get(TIME_INDEX) or []) + list(roles.get(EXOGENOUS) or []),
            outputs=list(roles.get(SERIES) or []),
        )

    def roles_from_io(
        self, input_columns: Sequence, output_columns: Sequence
    ) -> Dict[str, list]:
        """The roles that a model's input and output came from.

        The time index is always one column and comes first, so every input
        after it is an exogenous variable, however many columns a step of the
        preprocessing resolved them to.
        """
        inputs = list(input_columns)
        return {
            TIME_INDEX: inputs[:1],
            EXOGENOUS: inputs[1:],
            SERIES: list(output_columns or []),
        }

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

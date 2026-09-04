from DashAI.back.core.utils import MultilingualString
from DashAI.back.tasks.time_series_task import TimeSeriesTask
from DashAI.back.types.value_types import Date, Float, Integer


class ForecastingTask(TimeSeriesTask):
    """Task for predicting the future values of a single time series.

    The input is one ``Date`` column and the output is one numeric column: the
    series to forecast. Nothing else is offered to the model, so the only
    information it has is the history of the series itself.

    That restriction is the point. Models that take a date and nothing more,
    such as ARIMA or exponential smoothing, are a different family from models
    that also take explanatory variables. Those belong to
    :class:`ExogenousForecastingTask`, which takes the same date column with
    any number of numeric variables beside it.

    Two routes lead to a forecast in DashAI, and this is only one of them. The
    other is ``TimeSeriesWindowConverter``, which reshapes the same data into
    lag columns and hands it to ``RegressionTask``, making every existing
    regressor usable. This task exists for the models that read a date column
    directly and cannot be expressed that way.
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

    metadata: dict = {
        "inputs": [{"types": [Date], "cardinality": 1}],
        "outputs": [{"types": [Float, Integer], "cardinality": 1}],
    }

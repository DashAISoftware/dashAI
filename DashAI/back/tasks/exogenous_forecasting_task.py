from DashAI.back.core.utils import MultilingualString
from DashAI.back.tasks.time_series_task import TimeSeriesTask
from DashAI.back.types.value_types import Date, Float, Integer


class ExogenousForecastingTask(TimeSeriesTask):
    """Task for forecasting a time series with explanatory variables beside it.

    The input is one ``Date`` column and at least one numeric column, and the
    output is one numeric column: the series to forecast. The extra numeric
    columns are the exogenous variables, the things measured alongside the
    series that are believed to move it. Price and a promotion flag against
    units sold, temperature against electricity demand, an advertising budget
    against enquiries.

    Splitting this off from :class:`ForecastingTask` rather than widening it is
    what keeps each task honest about what it offers. A model that reads only
    a date cannot use a price column, so offering it here would silently drop
    the variables the user selected, and a model that needs explanatory
    variables cannot be fitted without them.

    Forecasting with exogenous variables asks something of the data that
    forecasting from history alone does not: the variables have to be known
    for the periods being forecast. That is what makes the approach worth the
    trouble for a planned price or a published calendar, and what makes it a
    poor fit for anything that would itself have to be forecast first.
    """

    DESCRIPTION: str = MultilingualString(
        en=(
            "Predict the future values of a time series using explanatory "
            "variables measured alongside it. Takes one date column, one or "
            "more numeric variables, and the numeric series to forecast."
        ),
        es=(
            "Predice los valores futuros de una serie temporal usando "
            "variables explicativas medidas junto a ella. Toma una columna de "
            "fecha, una o mas variables numericas y la serie numerica a "
            "pronosticar."
        ),
        pt=(
            "Preve os valores futuros de uma serie temporal usando variaveis "
            "explicativas medidas ao lado dela. Recebe uma coluna de data, uma "
            "ou mais variaveis numericas e a serie numerica a prever."
        ),
        de=(
            "Sagt die zukuenftigen Werte einer Zeitreihe mithilfe erklaerender "
            "Variablen voraus, die daneben gemessen werden. Nimmt eine "
            "Datumsspalte, eine oder mehrere numerische Variablen und die zu "
            "prognostizierende numerische Reihe."
        ),
        zh=(
            "利用与时间序列一同测量的解释变量预测其未来值。"
            "接受一个日期列、一个或多个数值变量，以及要预测的数值序列。"
        ),
    )
    DISPLAY_NAME: str = MultilingualString(
        en="Forecasting with Exogenous Variables",
        es="Pronostico con Variables Exogenas",
        pt="Previsao com Variaveis Exogenas",
        de="Zeitreihenprognose mit exogenen Variablen",
        zh="含外生变量的时间序列预测",
    )

    metadata: dict = {
        "inputs": [
            {"types": [Date], "cardinality": 1},
            {"types": [Float, Integer], "cardinality": {"min": 1, "max": "n"}},
        ],
        "outputs": [{"types": [Float, Integer], "cardinality": 1}],
    }

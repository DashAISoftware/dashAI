"""Unit that forecasts the steps after a series with their exogenous values."""

from DashAI.back.core.schema_fields import (
    BaseSchema,
    list_field,
    schema_field,
    string_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.job.base_job import JobError
from DashAI.back.units.base_unit import BaseUnit
from DashAI.back.units.context import ExecutionContext
from DashAI.back.units.forecast_scope import forecast_steps, model_grid


def model_exogenous_columns_field():
    """The columns of ``model_input`` the kept model was fitted on."""
    return schema_field(
        list_field(string_field()),
        placeholder=[],
        description=MultilingualString(
            en="The exogenous columns the model reads, as the session's "
            "preprocessing resolved them for the final fit.",
            es="Las columnas exógenas que lee el modelo, como las resolvió el "
            "preprocesamiento de la sesión para el ajuste final.",
            pt="As colunas exógenas que o modelo lê, tal como o "
            "pré-processamento da sessão as resolveu para o ajuste final.",
            de="Die exogenen Spalten, die das Modell liest, wie die "
            "Vorverarbeitung der Sitzung sie für die finale Anpassung auflöste.",
            zh="模型读取的外生列，即会话预处理为最终拟合解析出的列。",
        ),
        alias=MultilingualString(
            en="Model exogenous columns",
            es="Columnas exógenas del modelo",
            pt="Colunas exógenas do modelo",
            de="Exogene Spalten des Modells",
            zh="模型外生列",
        ),
    )


class ForecastFutureSchema(BaseSchema):
    exogenous_columns: model_exogenous_columns_field()  # type: ignore


class ForecastFutureUnit(BaseUnit):
    """Forecast the steps of the future rows, reading their exogenous values.

    The sibling of ``ForecastHorizonUnit`` for a run that read exogenous
    variables, and a provisional one: the contract cannot declare an optional
    input yet (ATOMIZING §5.4), and once it can this folds into that unit with
    an optional ``x_future`` (RECONCILING_FORECASTING §7.2, decision 2). The
    two share the helpers that forecast and check the grid.

    ``dataset`` holds the future rows ``PrepareFutureUnit`` checked, one per
    step, and ``model_input`` the same rows after the session's ``final.pkl``.
    The horizon is their number, and the model reads, from ``model_input``,
    the columns it was fitted on. The forecast is published as ``y_pred``, and
    ``dataset`` goes on unchanged: the saved prediction keeps the exogenous
    values it was made with.
    """

    SCHEMA = ForecastFutureSchema

    REQUIRES = ("model", "dataset", "model_input")
    PROVIDES = ("dataset", "y_pred")

    def execute(self, ctx: ExecutionContext) -> None:
        model = ctx.require("model")
        dataset = ctx.require("dataset")
        model_input = ctx.require("model_input")
        model_grid(model)

        columns = list(self.config["exogenous_columns"])
        missing = [c for c in columns if c not in model_input.column_names]
        if missing:
            raise JobError(
                "The session's preprocessing did not produce the column(s) the "
                f"model reads: {', '.join(repr(c) for c in missing)}."
            )
        x_future = model_input.select_columns(columns).to_pandas().to_numpy(dtype=float)
        point = forecast_steps(model, dataset.num_rows, x_future)

        ctx.put("dataset", dataset)
        ctx.put("y_pred", point)

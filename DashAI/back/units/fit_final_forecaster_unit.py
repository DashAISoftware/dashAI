"""Unit that fits the forecaster a run keeps, on the whole series."""

import logging

from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.job.base_job import JobError
from DashAI.back.units.base_unit import BaseUnit
from DashAI.back.units.context import ExecutionContext
from DashAI.back.units.forecast_scope import build_model, exogenous_for

log = logging.getLogger(__name__)


class FitFinalForecasterSchema(BaseSchema):
    """Nothing to configure: the parameters come from the backtest."""


class FitFinalForecasterUnit(BaseUnit):
    """Fit the model a run keeps, with the best parameters, on the whole series.

    The metrics come from the backtest; the kept model is the one that
    forecasts the future, so it has seen everything up to the last step:
    train, validation and test (D4). It is a fresh instance built from the
    parameters, not the backtest's.

    The grid goes with it (``time_grid``): its frequency and last date are
    what turn a forecast's steps into dates when the model is asked to
    predict (D5). A run that reads exogenous variables fits it on the final
    cut, which ``final.pkl`` made from the whole series, the same fit that
    transforms the future when predicting.
    """

    SCHEMA = FitFinalForecasterSchema

    REQUIRES = ("factory", "best_parameters", "series", "grid", "exogenous")
    PROVIDES = ("model",)

    def execute(self, ctx: ExecutionContext) -> None:
        import numpy as np

        factory = ctx.require("factory")
        parameters = ctx.require("best_parameters")
        series = np.asarray(ctx.require("series"), dtype=float)
        grid = ctx.require("grid")
        exogenous = ctx.require("exogenous")

        try:
            model_class = type(factory.model)
            model = build_model(model_class, parameters, factory.model.run_id)
            x = exogenous_for(
                model_class, parameters, exogenous["declared"], exogenous["final"]
            )
            model.fit(series, x)
        except JobError:
            raise
        except Exception as e:
            log.exception(e)
            raise JobError(f"Fitting the model on the whole series failed: {e}") from e

        model.time_grid = grid
        ctx.put("model", model)

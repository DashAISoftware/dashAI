"""Unit that fits the forecaster a run keeps, on the whole series."""

import logging

from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.job.base_job import JobError
from DashAI.back.units.base_unit import BaseUnit
from DashAI.back.units.context import ExecutionContext
from DashAI.back.units.forecast_scope import build_model

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
    predict (D5).
    """

    SCHEMA = FitFinalForecasterSchema

    REQUIRES = ("factory", "best_parameters", "series", "grid")
    PROVIDES = ("model",)

    def execute(self, ctx: ExecutionContext) -> None:
        import numpy as np

        factory = ctx.require("factory")
        parameters = ctx.require("best_parameters")
        series = np.asarray(ctx.require("series"), dtype=float)
        grid = ctx.require("grid")

        try:
            model = build_model(type(factory.model), parameters, factory.model.run_id)
            model.fit(series)
        except Exception as e:
            log.exception(e)
            raise JobError(f"Fitting the model on the whole series failed: {e}") from e

        model.time_grid = grid
        ctx.put("model", model)

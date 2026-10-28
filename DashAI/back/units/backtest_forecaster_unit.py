"""Unit that backtests a forecaster over the origins of a series."""

import logging

from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.job.base_job import JobError
from DashAI.back.units.base_unit import BaseUnit
from DashAI.back.units.context import ExecutionContext
from DashAI.back.units.fit_scope import (
    ModelFitScopeMixin,
    goal_metric_field,
    optimizer_field,
)
from DashAI.back.units.forecast_scope import (
    LEVELS,
    build_model,
    forecast_origin,
    scored_forecast,
)

log = logging.getLogger(__name__)


class BacktestForecasterSchema(BaseSchema):
    optimizer: optimizer_field()  # type: ignore
    goal_metric: goal_metric_field()  # type: ignore


class BacktestForecasterUnit(BaseUnit, ModelFitScopeMixin):
    """Forecast every origin of a backtest, searching first if there is a search.

    One unit for the holdout and the rolling origin alike: a holdout is a
    backtest with one validation origin (RECONCILING_FORECASTING §2.13).

    **The search**, when the model declares something to tune and the run
    names an optimizer, measures a trial by the mean of the goal metric over
    the validation origins, each fitted on the steps before it. The test
    origin is never part of it.

    **The forecasts** come after, with the best parameters, or the ones given
    when there was no search: every validation origin and then the test, each
    one a fresh model fitted on the steps before its origin and asked for the
    horizon after it, with intervals when the model gives them. They are
    published as ``forecasts``, in the shape the forecasts file holds, and
    ``ScoreForecastsUnit`` and ``SaveForecastsUnit`` read them.

    ``best_parameters`` is published whether or not there was a search, so the
    final fit can require it rather than check for it (ATOMIZING §5.4).
    """

    SCHEMA = BacktestForecasterSchema

    REQUIRES = (
        "model",
        "factory",
        "optimizable_parameters",
        "model_parameters",
        "series",
        "split_indexes",
        "grid",
    )
    PROVIDES = ("forecasts", "plot_paths", "best_parameters")
    RUNTIME_PARAMS = ("run_id", "artifact_prefix")

    def __init__(self, **config) -> None:
        super().__init__(**config)
        self._optimizer = None
        self._goal_metric = None

    def validate(self, ctx: ExecutionContext) -> None:
        self._validate_search(ctx.require("optimizable_parameters"))

    def execute(self, ctx: ExecutionContext) -> None:
        import numpy as np

        from DashAI.back.tasks.time_grid import TimeGrid

        model = ctx.require("model")
        series = np.asarray(ctx.require("series"), dtype=float)
        cuts = ctx.require("split_indexes")
        grid = TimeGrid.from_ref(ctx.require("grid"))
        optimizable_parameters = ctx.require("optimizable_parameters")
        best_parameters = ctx.require("model_parameters")

        plot_paths = []
        try:
            if self._will_search(optimizable_parameters):
                # The search checks the model it gets back still points at
                # its data; a forecaster's data is the series.
                model.x_data = series
                _, best_parameters, plot_paths = self._search(
                    model,
                    series,
                    cuts,
                    optimizable_parameters,
                    ctx.require("factory"),
                    best_parameters,
                    self.config["run_id"],
                    self.config["artifact_prefix"],
                    self._score_one_trial,
                )

            model_class = type(model)
            levels = LEVELS if model_class.SUPPORTS_INTERVALS else []
            horizon = cuts["horizon"]
            origins = [
                forecast_origin(
                    build_model(model_class, best_parameters),
                    series,
                    origin,
                    horizon,
                    grid,
                    "validation",
                    index,
                    levels,
                )
                for index, origin in enumerate(cuts["validation_origins"])
            ]
            origins.append(
                forecast_origin(
                    build_model(model_class, best_parameters),
                    series,
                    cuts["test_origin"],
                    horizon,
                    grid,
                    "test",
                    0,
                    levels,
                )
            )
            season_length = getattr(
                build_model(model_class, best_parameters), "season_length", 1
            )
        except JobError:
            raise
        except Exception as e:
            log.exception(e)
            raise JobError(f"Backtesting the model failed: {e}") from e

        ctx.put_ref(
            "forecasts",
            {
                "version": 1,
                "freq": grid.freq,
                "horizon": horizon,
                "levels": levels,
                "season_length": int(season_length or 1),
                "origins": origins,
            },
        )
        ctx.put_ref("plot_paths", plot_paths)
        ctx.put_ref("best_parameters", best_parameters)

    def _score_one_trial(self, model, series, cuts, metric) -> float:
        """The mean of the goal metric over the validation origins.

        The optimizer has set this trial's parameters on ``model``; it is
        fitted once per origin, on the steps before it, and never on the test.

        A window with no number to compare stops the run, the same as a fold
        in ``FitModelOverFoldsUnit``: skipped, the objective would be the
        mean of a different set of windows on each trial; averaged, NaN can
        neither win nor lose. ``RuntimeError`` and not ``ValueError``, which
        the optimizer swallows into "every trial failed, narrow the ranges",
        the wrong advice for a model that forecast no number.
        """
        import math

        import numpy as np

        horizon = cuts["horizon"]
        levels = [95] if model.SUPPORTS_INTERVALS else []
        scores = []
        for index, origin in enumerate(cuts["validation_origins"]):
            where = f"the validation window at step {origin}"
            # No grid: a score never reads the dates.
            record = forecast_origin(
                model, series, origin, horizon, None, "validation", index, levels
            )
            if any(value is None for value in record["forecast"]):
                raise RuntimeError(
                    f"The model forecast values that are not numbers on {where}, "
                    f"so the optimization metric {metric.__name__} has nothing to "
                    "score. Check that the series suits the model, or search "
                    "other ranges."
                )
            forecast = scored_forecast(
                record, series, getattr(model, "season_length", 1) or 1
            )
            score = self._goal_score_forecast(metric, forecast, where)
            if not math.isfinite(score):
                raise RuntimeError(
                    f"The optimization metric {metric.__name__} scored a value "
                    f"that is not a number ({score}) on {where}. Check that the "
                    "metric is defined on the window's values."
                )
            scores.append(score)
        return float(np.mean(scores))

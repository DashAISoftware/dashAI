"""Unit that instantiates a single-series forecaster for a series' grid."""

import logging

from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.job.base_job import JobError
from DashAI.back.units.base_unit import BaseUnit
from DashAI.back.units.context import ExecutionContext
from DashAI.back.units.forecast_scope import forecaster_field, season_length_for

log = logging.getLogger(__name__)


class BuildForecasterSchema(BaseSchema):
    model: forecaster_field()  # type: ignore


class BuildForecasterUnit(BaseUnit):
    """Instantiate an unfitted forecaster, with the season its grid implies.

    A forecaster with a ``season_length`` that the run leaves out gets the
    season the series' frequency implies: 12 for a monthly series, 7 for a
    daily one, 24 for an hourly one (D3). The model receives only the number;
    the frequency is this unit's to read. A season the run gives, even 1, is
    kept.

    The sibling for the x/y tasks is ``BuildModelUnit``, which sizes a model by
    its label count and attaches the metrics it logs while training. A
    forecaster has no labels, and its metrics are scored on the forecasts of a
    backtest, by ``ScoreForecastsUnit``.
    """

    SCHEMA = BuildForecasterSchema

    REQUIRES = ("task_name", "grid")
    PROVIDES = ("model", "factory", "optimizable_parameters", "model_parameters")
    RUNTIME_PARAMS = ("run_id",)

    def __init__(self, **config) -> None:
        super().__init__(**config)
        self._model_class = None

    def _resolve_model_class(self) -> type:
        """Resolve the model class from the registry, memoized on this unit."""
        if self._model_class is not None:
            return self._model_class

        from kink import di

        model_name = self.config["model"]["component"]
        try:
            self._model_class = di["component_registry"][model_name]["class"]
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Unable to find Model with name {model_name} in registry.",
            ) from e
        return self._model_class

    def execute(self, ctx: ExecutionContext) -> None:
        from DashAI.back.models.model_factory import ModelFactory
        from DashAI.back.tasks.time_grid import TimeGrid

        task_name = ctx.require("task_name")
        grid = TimeGrid.from_ref(ctx.require("grid"))
        model_class = self._resolve_model_class()

        parameters = dict(self.config["model"]["params"])
        declared = model_class.SCHEMA.model_json_schema().get("properties", {})
        if "season_length" in declared and "season_length" not in parameters:
            parameters["season_length"] = season_length_for(grid.freq)

        try:
            factory = ModelFactory(model_class, parameters, self.config["run_id"])
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Unable to instantiate {model_class.__name__} for task "
                f"{task_name}: {e}",
            ) from e

        ctx.put_ref("model_parameters", parameters)
        ctx.put("factory", factory)
        ctx.put("model", factory.model)
        ctx.put("optimizable_parameters", factory.optimizable_parameters)

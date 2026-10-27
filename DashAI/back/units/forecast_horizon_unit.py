"""Unit that forecasts a number of steps past the end of a model's series."""

import logging

from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.job.base_job import JobError
from DashAI.back.splitters.origin_splitter import horizon_field
from DashAI.back.units.base_unit import BaseUnit
from DashAI.back.units.context import ExecutionContext
from DashAI.back.units.splitter_scope import input_columns_field

log = logging.getLogger(__name__)


class ForecastHorizonSchema(BaseSchema):
    horizon: horizon_field()  # type: ignore
    input_columns: input_columns_field()  # type: ignore


class ForecastHorizonUnit(BaseUnit):
    """Forecast the steps after a trained series, and name their dates.

    The kept model of a forecasting run was fitted on the whole series and
    carries its grid (``time_grid``): the frequency and the last date are what
    turn the forecast's steps into dates. The dates come out as the time index
    column the session named, in the format the training dataset declared it
    with, so the rows look like the training rows.

    Publishes them as ``dataset``, the rows a prediction is made for, and the
    forecast as ``y_pred``: ``SavePredictionUnit`` writes the two side by side
    as it writes any prediction. Nothing is read from a dataset to predict on,
    because there is none: a forecast reaches past the end of the data
    (RECONCILING_FORECASTING §2.13, D6).
    """

    SCHEMA = ForecastHorizonSchema

    REQUIRES = ("model", "train_dataset_types")
    PROVIDES = ("dataset", "y_pred")

    def execute(self, ctx: ExecutionContext) -> None:
        import pandas as pd

        from DashAI.back.dataloaders.classes.dashai_dataset import (
            to_dashai_dataset,
            transform_dataset_with_schema,
        )
        from DashAI.back.tasks.time_grid import TimeGrid
        from DashAI.back.types.date_utils import DEFAULT_DATE_FORMAT

        model = ctx.require("model")
        train_types = ctx.require("train_dataset_types")
        horizon = int(self.config["horizon"])
        time_index = self.config["input_columns"][0]

        grid_ref = getattr(model, "time_grid", None)
        if not grid_ref:
            raise JobError(
                "The model has no grid to name the dates of its forecast: it "
                "was not trained by a forecasting run. Train it again."
            )
        grid = TimeGrid.from_ref(grid_ref)

        try:
            forecast = model.predict(horizon)
        except Exception as e:
            log.exception(e)
            raise JobError(f"The model could not forecast {horizon} steps: {e}") from e

        # The training type spells the format apart from the Arrow dtype; a
        # schema to apply carries the format as its dtype.
        date_format = (train_types.get(time_index) or {}).get(
            "format"
        ) or DEFAULT_DATE_FORMAT
        dates = grid.dates(grid.n_steps, horizon)
        rows = pd.DataFrame({time_index: dates.strftime(date_format)})
        schema = {time_index: {"type": "Date", "dtype": date_format}}
        dataset = transform_dataset_with_schema(to_dashai_dataset(rows), schema)

        ctx.put("dataset", dataset)
        ctx.put("y_pred", forecast.point)

"""Unit that prepares a single series for a task and cuts it into origins."""

import logging

from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.job.base_job import JobError
from DashAI.back.units.base_unit import BaseUnit
from DashAI.back.units.context import ExecutionContext
from DashAI.back.units.forecast_scope import origin_splitter_field
from DashAI.back.units.splitter_scope import (
    SplitterScopeMixin,
    input_columns_field,
    output_columns_field,
    task_name_field,
)

log = logging.getLogger(__name__)


class PrepareSeriesSchema(BaseSchema):
    task_name: task_name_field()  # type: ignore
    input_columns: input_columns_field()  # type: ignore
    output_columns: output_columns_field()  # type: ignore
    splitter: origin_splitter_field()  # type: ignore


class PrepareSeriesUnit(BaseUnit, SplitterScopeMixin):
    """Turn a dataset into a series on its grid, and cut it into origins.

    The task validates the roles, orders the rows by time and checks the
    series sits on a regular grid (``SingleSeriesForecastingTask.prepare_series``).
    What comes out is the series' values in time order, which is all a
    forecaster reads, and the grid, which turns a step back into a date.

    The splitter then cuts the series into backtest origins. The cuts are
    steps, and they are published as ``split_indexes``: the job stores them on
    the run as it stores a holdout's rows, and the splitter's class is what
    reads either.

    The sibling for the x/y tasks is ``PrepareAndSplitUnit``. A series is not
    an ``x`` and a ``y``, and a backtest's cuts are not partitions of rows, so
    this publishes different keys. A forecasting session takes no session
    preprocessing yet (RECONCILING_FORECASTING 2.13, decision 8), so a
    ``preprocessing_artifacts_path`` is a wiring error: the API refuses the
    steps, and a session that carries the artifacts anyway is refused here
    rather than trained on the raw series without a word.
    """

    SCHEMA = PrepareSeriesSchema

    REQUIRES = ("dataset", "dataset_id")
    PROVIDES = ("series", "grid", "task", "task_name", "split_indexes")
    RUNTIME_PARAMS = ("preprocessing_artifacts_path",)

    def __init__(self, **config) -> None:
        super().__init__(**config)
        self._task = None
        self._splitter_class = None

    def validate(self, ctx: ExecutionContext) -> None:
        if self.config.get("preprocessing_artifacts_path"):
            raise JobError(
                f"Task {self.config['task_name']} takes no session preprocessing "
                "yet, and this session has fitted preprocessing. Create the "
                "session again without preprocessing steps, or transform the "
                "dataset in a notebook."
            )

    def execute(self, ctx: ExecutionContext) -> None:
        dataset = ctx.require("dataset")
        dataset_id = ctx.require("dataset_id")

        task = self._resolve_task()
        if not hasattr(task, "prepare_series"):
            raise JobError(
                f"Task {self.config['task_name']} does not prepare a single "
                "series, so it cannot be backtested."
            )
        try:
            prepared = task.prepare_series(
                dataset, self.config["input_columns"], self.config["output_columns"]
            )
        except (TypeError, ValueError) as e:
            log.exception(e)
            raise JobError(
                f"The series in dataset {dataset_id} cannot be forecast: {e}"
            ) from e

        try:
            cuts = self._resolve_splitter().cuts(prepared.grid.n_steps)
        except ValueError as e:
            raise JobError(str(e)) from e

        ctx.put("series", prepared.values)
        ctx.put_ref("grid", prepared.grid.to_ref())
        ctx.put("task", task)
        ctx.put_ref("task_name", self.config["task_name"])
        ctx.put_ref("split_indexes", cuts)

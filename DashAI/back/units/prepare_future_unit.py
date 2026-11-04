"""Unit that checks the future rows a forecast with exogenous variables needs."""

from typing import Optional

from DashAI.back.core.schema_fields import BaseSchema, schema_field, string_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.job.base_job import JobError
from DashAI.back.units.base_unit import BaseUnit
from DashAI.back.units.context import ExecutionContext
from DashAI.back.units.forecast_scope import model_grid


def time_index_field():
    """The column of the future rows that holds their dates."""
    return schema_field(
        string_field(),
        placeholder="",
        description=MultilingualString(
            en="The time index column, which dates every future row.",
            es="La columna del índice temporal, que fecha cada fila futura.",
            pt="A coluna do índice temporal, que data cada linha futura.",
            de="Die Zeitindexspalte, die jede zukünftige Zeile datiert.",
            zh="时间索引列，为每个未来行标注日期。",
        ),
        alias=MultilingualString(
            en="Time index",
            es="Índice temporal",
            pt="Índice temporal",
            de="Zeitindex",
            zh="时间索引",
        ),
    )


def future_columns_field():
    """The raw columns the run's exogenous variables are read from, typed."""
    return schema_field(
        list,
        placeholder=[],
        description=MultilingualString(
            en="The columns the future rows have to bring, as the run recorded "
            "them: {'name': ..., 'type': ...} for each raw column the run read "
            "its exogenous variables from.",
            es="Las columnas que tienen que traer las filas futuras, como las "
            "registró el run: {'name': ..., 'type': ...} por cada columna cruda "
            "de la que leyó sus variables exógenas.",
            pt="As colunas que as linhas futuras têm de trazer, tal como o run "
            "as registou: {'name': ..., 'type': ...} por cada coluna bruta de "
            "onde leu as suas variáveis exógenas.",
            de="Die Spalten, die die zukünftigen Zeilen mitbringen müssen, wie "
            "der Lauf sie aufzeichnete: {'name': ..., 'type': ...} für jede "
            "Rohspalte, aus der er seine exogenen Variablen las.",
            zh="未来行必须包含的列，按运行记录的形式：每个读取外生变量的原始列"
            "对应 {'name': ..., 'type': ...}。",
        ),
        alias=MultilingualString(
            en="Exogenous columns",
            es="Columnas exógenas",
            pt="Colunas exógenas",
            de="Exogene Spalten",
            zh="外生列",
        ),
    )


#: Types a forecaster reads as numbers: one of them recorded takes the other.
NUMERIC_TYPES = {"Float", "Integer"}


def type_problem(name: str, given: str, recorded: str) -> Optional[str]:
    """Why a future column's type is not the one the run read, or None.

    A number recorded as Integer and brought as Float (or the other way) is
    still a number, and a forecaster reads both alike. Any other type has to
    be the one the run read.
    """
    if given == recorded or {given, recorded} <= NUMERIC_TYPES:
        return None
    return (
        f"The exogenous variable {name!r} is {given} in the future rows, but "
        f"the run read it as {recorded}."
    )


class PrepareFutureSchema(BaseSchema):
    time_index: time_index_field()  # type: ignore
    exogenous_columns: future_columns_field()  # type: ignore


class PrepareFutureUnit(BaseUnit):
    """Check the rows a user brings for the steps after the series.

    A run that read exogenous variables forecasts with their future values,
    so the rows to predict are those values (RECONCILING_FORECASTING §2.14,
    decisions 5 and 6). Read from a dataset or typed by hand, they arrive as
    the same ``dataset``, and are checked here once:

    - they are put in date order, as the training series was (D5);
    - their dates have to be exactly the next steps of the kept model's grid,
      as many as there are rows: that number is the horizon. A date repeated,
      off the grid or skipping a step is refused, naming it;
    - every column the run read is there, of the type the run read it as
      (``Run.exogenous.columns``), and has a value on every row: a number
      that is not finite is refused like a gap, naming the column and dates.

    What comes out, as ``dataset`` again, is the date and those columns only.
    The series, if it came along, and any other column are left out, as an
    x/y prediction ignores the columns its model does not read.
    """

    SCHEMA = PrepareFutureSchema

    REQUIRES = ("dataset", "model")
    PROVIDES = ("dataset",)

    def execute(self, ctx: ExecutionContext) -> None:
        import numpy as np

        from DashAI.back.tasks.time_grid import sample_dates, time_order
        from DashAI.back.types.date_utils import DEFAULT_DATE_FORMAT, parse_date_column

        dataset = ctx.require("dataset")
        grid = model_grid(ctx.require("model"))
        from DashAI.back.preprocessing.structure_types import type_fields

        time_index = self.config["time_index"]
        recorded = {c["name"]: c["type"] for c in self.config["exogenous_columns"]}
        columns = list(recorded)

        missing = [c for c in [time_index, *columns] if c not in dataset.column_names]
        if missing:
            raise JobError(
                "The future rows lack the column(s) this run reads: "
                f"{', '.join(repr(c) for c in missing)}."
            )
        if dataset.num_rows == 0:
            raise JobError("There are no future rows to forecast.")
        for column in columns:
            given = dataset.types.get(column)
            if given is None:
                continue
            problem = type_problem(column, type_fields(given)[0], recorded[column])
            if problem:
                raise JobError(problem)

        date_format = (
            getattr(dataset.types.get(time_index), "format", None)
            or DEFAULT_DATE_FORMAT
        )
        frame = dataset.to_pandas()
        dates = parse_date_column(frame[time_index], date_format)
        if dates.isna().any():
            raise JobError(
                f"Some future rows have no date in {time_index!r}, and each one "
                "has to be a step after the series."
            )
        repeated = dates[dates.duplicated(keep=False)]
        if not repeated.empty:
            raise JobError(
                f"The future repeats {sample_dates(sorted(set(repeated)))}: "
                "each step after the series comes once."
            )
        expected = grid.dates(grid.n_steps, len(frame))
        given = set(dates)
        absent = [date for date in expected if date not in given]
        if absent:
            raise JobError(
                f"The future has to bring the {len(frame)} dates after the "
                f"series ends ({sample_dates(grid.dates(grid.n_steps - 1, 1))}), "
                f"and lacks {sample_dates(absent, 'more dates')}."
            )

        order = time_order(dates)
        future = dataset.select(order).select_columns([time_index, *columns])
        values = future.select_columns(columns).to_pandas() if columns else None
        for column in columns:
            gaps = np.flatnonzero(values[column].isna().to_numpy())
            if gaps.size:
                raise JobError(
                    f"The exogenous variable {column!r} has no value on "
                    f"{sample_dates(expected[gaps])}. A forecast reads it on "
                    "every step it forecasts."
                )
            if recorded[column] in NUMERIC_TYPES:
                numbers = values[column].to_numpy(dtype=float)
                endless = np.flatnonzero(~np.isfinite(numbers))
                if endless.size:
                    raise JobError(
                        f"The exogenous variable {column!r} is not a finite "
                        f"number on {sample_dates(expected[endless])}. A "
                        "forecast reads it on every step it forecasts."
                    )
        ctx.put("dataset", future)

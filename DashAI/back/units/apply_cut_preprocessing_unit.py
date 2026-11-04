"""Unit that turns a series' exogenous variables into what each cut reads."""

import logging
from typing import TYPE_CHECKING, Any, Dict, List

from DashAI.back.core.schema_fields import BaseSchema, none_type, schema_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.job.base_job import JobError
from DashAI.back.units.base_unit import BaseUnit
from DashAI.back.units.context import ExecutionContext

if TYPE_CHECKING:
    from numpy import ndarray

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
    from DashAI.back.tasks.time_grid import TimeGrid

log = logging.getLogger(__name__)


def exogenous_column_refs_field():
    """The exogenous role's columns, as the references a session stores.

    A raw ref names a column of the dataset, a group ref what a step of the
    session's preprocessing produces, and the latter only resolves against
    the fits ``PreprocessingJob`` left at ``preprocessing_artifacts_path``.
    Left out, the session has no exogenous variables.
    """
    return schema_field(
        none_type(list),
        placeholder=None,
        description=MultilingualString(
            en="The exogenous variables, as column references: {'kind': "
            "'raw', 'name': ...} for a column of the dataset, {'kind': "
            "'group', 'step': n} for what preprocessing step n produces.",
            es="Las variables exógenas, como referencias a columnas: {'kind': "
            "'raw', 'name': ...} para una columna del conjunto de datos, "
            "{'kind': 'group', 'step': n} para lo que produce el paso n del "
            "preprocesamiento.",
            pt="As variáveis exógenas, como referências a colunas: {'kind': "
            "'raw', 'name': ...} para uma coluna do conjunto de dados, "
            "{'kind': 'group', 'step': n} para o que o passo n do "
            "pré-processamento produz.",
            de="Die exogenen Variablen, als Spaltenreferenzen: {'kind': 'raw', "
            "'name': ...} für eine Spalte des Datensatzes, {'kind': 'group', "
            "'step': n} für das, was Vorverarbeitungsschritt n erzeugt.",
            zh="外生变量，以列引用表示：{'kind': 'raw', 'name': ...} 表示数据集的"
            "一列，{'kind': 'group', 'step': n} 表示预处理第 n 步产生的列。",
        ),
        alias=MultilingualString(
            en="Exogenous variables",
            es="Variables exógenas",
            pt="Variáveis exógenas",
            de="Exogene Variablen",
            zh="外生变量",
        ),
    )


class ApplyCutPreprocessingSchema(BaseSchema):
    exogenous_column_refs: exogenous_column_refs_field()  # type: ignore


def cut_names(cuts: Dict[str, Any]) -> List[str]:
    """The artifact of every cut, in the order the unit publishes them.

    One per validation origin, then the test, then the final fit: the files
    ``PreprocessingJob`` writes for a backtest, without their ``.pkl``.
    """
    return [
        *(f"origin_{i}" for i in range(len(cuts["validation_origins"]))),
        "test",
        "final",
    ]


def cut_lengths(cuts: Dict[str, Any]) -> List[int]:
    """How many steps of the series each cut reads, in ``cut_names`` order.

    A validation origin reads up to the end of its window, the steps it is
    fitted on and the horizon it forecasts with. The test's window ends the
    series, and the final fit reads all of it.
    """
    horizon, n_steps = cuts["horizon"], cuts["n_steps"]
    return [
        *(origin + horizon for origin in cuts["validation_origins"]),
        n_steps,
        n_steps,
    ]


def exogenous_matrix(dataset: "DashAIDataset", columns: List[str]) -> "ndarray":
    """The exogenous columns as floats, one row per row of ``dataset``.

    Raises
    ------
    JobError
        If a column is not a number.
    """
    import numpy as np

    if not columns:
        return np.empty((dataset.num_rows, 0))
    frame = dataset.select_columns(columns).to_pandas()
    for column in columns:
        if not np.issubdtype(frame[column].dtype, np.number):
            raise JobError(
                f"The exogenous variable {column!r} is not a number "
                f"({frame[column].dtype}), and a forecaster reads numbers."
            )
    return frame.to_numpy(dtype=float)


def refuse_gaps(
    values: "ndarray", columns: List[str], steps: int, grid: "TimeGrid"
) -> None:
    """Refuse a gap in the steps a cut reads, naming the column and dates.

    Parameters
    ----------
    values : numpy.ndarray
        The cut's matrix, from the first step of the series on.
    columns : list of str
        The columns the exogenous refs resolved to for this cut.
    steps : int
        How many steps from the start the cut reads (``cut_lengths``).
    grid : TimeGrid
        Dates the steps, for the message.

    Raises
    ------
    JobError
        If a column has no value on a step the cut reads.
    """
    import numpy as np

    from DashAI.back.tasks.time_grid import sample_dates

    for index, column in enumerate(columns):
        gaps = np.flatnonzero(~np.isfinite(values[:steps, index]))
        if gaps.size:
            dates = grid.dates(0, grid.n_steps)[gaps]
            raise JobError(
                f"The exogenous variable {column!r} has no value on "
                f"{sample_dates(dates)}. A forecaster reads every step of it "
                "up to the end of the window it forecasts. Fill the gaps in "
                "the notebook, or add an imputer to the session's "
                "preprocessing."
            )


class ApplyCutPreprocessingUnit(BaseUnit):
    """Publish the exogenous variables each cut of a backtest reads.

    ``PreprocessingJob`` fits the session's preprocessing once per cut, on
    the steps before it: ``origin_{i}.pkl`` for each validation origin,
    ``test.pkl`` for the test and ``final.pkl`` for the final fit on the
    whole series. This applies each one, without fitting, to the rows of the
    series in date order (the ``dataset`` that ``PrepareSeriesUnit``
    publishes), and resolves the exogenous refs against what that same fit
    resolved, since a step may produce other columns on other steps.

    What comes out, under ``exogenous``, is one matrix per cut, with a row per
    step the cut reads (``cut_lengths``), from the first step of the series:
    a forecaster fitted on the steps before origin ``o`` reads its rows
    ``[:o]`` and forecasts with ``[o:o + h]``, and the test and the final fit
    read every step. Without artifacts the raw columns are read once and
    every cut shares them, whole. Each cut carries its ``name``, the artifact
    it came from, and ``declared`` says whether the role has columns at all:
    that, and not the columns one cut resolved, is what decides whether a run
    reads them (``exogenous_for``).

    **It always runs,** as ``ApplySessionPreprocessingUnit`` does on the
    prediction side. Without artifacts every cut reads the raw columns, and
    without the role every cut reads none; the graph is one shape either way.

    **Every step keeps the rows** (``PREPROCESSING_KEEPS_ROWS``), and the
    dataset goes under the ``"predict"`` key of ``transform_dataset``, where
    no step may add or remove rows. A cut that comes back with another number
    of rows is a broken contract, and is reported as one.

    **A gap is refused after the preprocessing,** on the steps the cut reads,
    so an imputer in the session fills what it should. The message names the
    column and the dates.
    """

    SCHEMA = ApplyCutPreprocessingSchema

    REQUIRES = ("dataset", "split_indexes", "grid")
    PROVIDES = ("exogenous",)
    RUNTIME_PARAMS = ("preprocessing_artifacts_path",)

    def __init__(self, **config) -> None:
        super().__init__(**config)
        self._refs = None

    def validate(self, ctx: ExecutionContext) -> None:
        import os

        cuts = ctx.require("split_indexes")
        refs = self._resolve_refs()
        artifacts_path = self.config.get("preprocessing_artifacts_path")
        if not artifacts_path:
            if any(ref.kind != "raw" for ref in refs):
                raise JobError(
                    "The exogenous variables name the output of a preprocessing "
                    "step, but no preprocessing_artifacts_path was given to "
                    "resolve it against."
                )
            return
        for name in cut_names(cuts):
            if not os.path.exists(os.path.join(artifacts_path, f"{name}.pkl")):
                raise JobError(
                    f"The session's preprocessing was not fitted for {name}: "
                    f"{name}.pkl is missing from {artifacts_path}. Create the "
                    "session again to fit it."
                )

    def execute(self, ctx: ExecutionContext) -> None:
        from DashAI.back.tasks.time_grid import TimeGrid

        dataset = ctx.require("dataset")
        cuts = ctx.require("split_indexes")
        grid = TimeGrid.from_ref(ctx.require("grid"))

        artifacts_path = self.config.get("preprocessing_artifacts_path")
        # Without artifacts every cut reads the same raw columns, so they are
        # read once; each cut still refuses the gaps in its own steps.
        raw = None
        if not artifacts_path:
            columns = [ref.name for ref in self._resolve_refs()]
            raw = (columns, exogenous_matrix(dataset, columns))
        published = []
        for name, steps in zip(cut_names(cuts), cut_lengths(cuts), strict=True):
            columns, values = raw or self._apply(dataset, artifacts_path, name, steps)
            refuse_gaps(values, columns, steps, grid)
            published.append({"name": name, "columns": columns, "values": values})

        ctx.put(
            "exogenous",
            {
                "declared": bool(self._resolve_refs()),
                "validation": published[:-2],
                "test": published[-2],
                "final": published[-1],
            },
        )

    def _resolve_refs(self) -> list:
        """The configured refs, parsed once."""
        if self._refs is None:
            from DashAI.back.preprocessing.column_ref import parse_column_refs

            try:
                self._refs = parse_column_refs(
                    self.config.get("exogenous_column_refs") or []
                )
            except Exception as e:
                raise JobError(
                    "Can not parse the exogenous column refs "
                    f"{self.config.get('exogenous_column_refs')}: {e}"
                ) from e
        return self._refs

    def _apply(self, dataset, artifacts_path, name, steps):
        """The columns a cut's exogenous refs resolve to, and their matrix.

        Only the ``steps`` the cut reads are transformed: a step keeps the
        rows, so the rows after them would be transformed for nothing.
        """
        import os
        import pickle

        from DashAI.back.preprocessing.column_ref import resolve_refs

        rows = dataset.select(range(steps)) if steps < dataset.num_rows else dataset
        artifact = os.path.join(artifacts_path, f"{name}.pkl")
        try:
            with open(artifact, "rb") as f:
                preprocessor = pickle.load(f)
            transformed = preprocessor.transform_dataset(rows)
            columns = resolve_refs(
                self._resolve_refs(),
                preprocessor.resolved_columns,
                preprocessor.resolved_slots,
            )
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Error applying the preprocessing fitted for {name} from "
                f"{artifact}: {e}"
            ) from e
        if transformed.num_rows != rows.num_rows:
            raise JobError(
                f"The preprocessing fitted for {name} turned {rows.num_rows} "
                f"rows into {transformed.num_rows}, and every step of a "
                "forecasting session has to keep the rows."
            )
        return columns, exogenous_matrix(transformed, columns)

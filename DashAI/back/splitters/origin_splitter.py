from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

from DashAI.back.core.schema_fields import int_field, schema_field
from DashAI.back.core.utils import MultilingualString

from .base_splitter import BaseSplitter

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


def horizon_field():
    """The horizon of a backtest, in steps of the series' grid."""
    return schema_field(
        int_field(ge=1),
        placeholder=6,
        description=MultilingualString(
            en=(
                "How many steps ahead the model is scored, from every origin and "
                "on the test. A step is one period of the series: a month on a "
                "monthly series."
            ),
            es=(
                "Cuantos pasos hacia adelante se evalua el modelo, desde cada "
                "origen y en el test. Un paso es un periodo de la serie: un mes "
                "en una serie mensual."
            ),
            pt=(
                "Quantos passos a frente o modelo e avaliado, a partir de cada "
                "origem e no teste. Um passo e um periodo da serie: um mes numa "
                "serie mensal."
            ),
            de=(
                "Wie viele Schritte voraus das Modell bewertet wird, von jedem "
                "Ursprung aus und im Test. Ein Schritt ist eine Periode der "
                "Reihe: ein Monat bei einer Monatsreihe."
            ),
            zh=(
                "从每个起点以及在测试中向前评估模型的步数。"
                "一步是序列的一个周期：月度序列中为一个月。"
            ),
        ),
        alias=MultilingualString(
            en="Horizon", es="Horizonte", pt="Horizonte", de="Horizont", zh="预测步长"
        ),
    )


class OriginSplitter(BaseSplitter):
    """Cut a series into backtest origins, counted in steps of its grid.

    A forecaster is fitted on the steps before an origin and scored on the
    ``horizon`` steps that follow it. The test is one more origin, at
    ``n - horizon``; the validation origins sit before it, ``horizon`` apart::

        n = 48, horizon = 6, 3 validation origins

        validation   fit [0, 24)  forecast [24, 30)
        validation   fit [0, 30)  forecast [30, 36)
        validation   fit [0, 36)  forecast [36, 42)
        test         fit [0, 42)  forecast [42, 48)

    The window only grows, the step between origins is always the horizon and
    the history before the first origin is whatever is left. A holdout is the
    same backtest with one validation origin.

    The cuts are steps, not row positions: the task has already checked the
    series sits on its grid, so a step is a row of the prepared series, and no
    unit needs to read rows to find one.

    Not a ``Base*`` class: the registry finds a splitter's type by the one
    ancestor named ``Base*`` with a ``TYPE``, and a second would break both
    splitters that inherit this.
    """

    PARTITIONING: str = "origins"
    # No preview draws this shape yet; the frontend leaves it blank rather
    # than drawing proportions that the cuts no longer are.
    GEOMETRY: str = "backtest_origins"
    NO_ROW_PARTITIONS = (
        "A backtest cuts the series in steps of its grid, so its run has no "
        "partitions of rows to explain or to predict on: its validation and "
        "test are windows of steps. Forecast by horizon instead."
    )

    def __init__(self, splits_data: Dict[str, Any]):
        """Read the horizon and the number of validation origins.

        Parameters
        ----------
        splits_data : dict
            The splitter's configuration.
        """
        super().__init__(splits_data)
        self.horizon = int(splits_data.get("horizon", 6))
        self.n_origins = int(splits_data.get("n_origins", 1))
        self.shuffle = False

    def cuts(self, n_steps: int) -> Dict[str, Any]:
        """Where a series of ``n_steps`` steps is cut.

        Parameters
        ----------
        n_steps : int
            How many steps the series has.

        Returns
        -------
        dict
            ``{"horizon", "validation_origins", "test_origin", "n_steps"}``.
            Origin ``o`` fits on steps ``[0, o)`` and forecasts ``[o, o + h)``.

        Raises
        ------
        ValueError
            If the series is too short to leave a step to fit on before the
            first origin.
        """
        h, k = self.horizon, self.n_origins
        needed = (k + 1) * h + 1
        if n_steps < needed:
            raise ValueError(
                f"A horizon of {h} step(s) with {k} validation origin(s) needs "
                f"a series of at least {needed} steps: {k} validation "
                f"window(s) and the test, {h} step(s) each, after at least one "
                f"step to fit on. The series has {n_steps}. Shorten the "
                "horizon, use fewer origins, or bring more history."
            )
        test_origin = n_steps - h
        return {
            "horizon": h,
            "validation_origins": [test_origin - h * (k - i) for i in range(k)],
            "test_origin": test_origin,
            "n_steps": n_steps,
        }

    def validate_size(self, n_rows: int) -> None:
        """Refuse a dataset too short for these cuts (see ``cuts``)."""
        self.cuts(n_rows)

    @classmethod
    def explainable_partitions(cls, split_indexes: Dict[str, Any]) -> Dict:
        """No partition of rows to explain: a backtest's cuts are steps.

        Forecasting declares no explainers, and a cut is not a set of rows an
        explainer could read, so a run of this splitter offers none.
        """
        return {}

    def split(self, x: "DashAIDataset", y: "DashAIDataset"):
        """Not how a backtest is cut: see ``cuts``."""
        raise NotImplementedError(
            f"{type(self).__name__} cuts a series in steps; call cuts(n_steps)."
        )

    def split_indexes(self, x: "DashAIDataset", y: "DashAIDataset") -> List:
        """Not how a backtest is cut: see ``cuts``."""
        raise NotImplementedError(
            f"{type(self).__name__} cuts a series in steps; call cuts(n_steps)."
        )

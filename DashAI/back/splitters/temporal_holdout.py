from __future__ import annotations

from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.core.utils import MultilingualString

from .origin_splitter import OriginSplitter, horizon_field


class TemporalHoldoutSplitterSchema(BaseSchema):
    """Schema that configures the temporal holdout splitter."""

    horizon: horizon_field()  # type: ignore


class TemporalHoldoutSplitter(OriginSplitter):
    """Hold out the end of a series: one validation window, then the test.

    The model is fitted on everything before the validation window, scored on
    its ``horizon`` steps, then refitted on everything before the test and
    scored on the last ``horizon`` steps. Validation and test measure the same
    horizon, so the two columns of the results can be compared::

        n = 48, horizon = 6

        validation   fit [0, 36)  forecast [36, 42)
        test         fit [0, 42)  forecast [42, 48)

    It is a backtest with one origin (``OriginSplitter``), and runs the same
    units as the rolling origin. Rows are never sampled, so every step a model
    is scored on comes after every step it was fitted on. The windowed route
    through ``TimeSeriesWindowConverter`` and ``RegressionTask`` does not reach
    this splitter; use ``HoldoutSplitter`` with shuffling turned off there.
    """

    SCHEMA = TemporalHoldoutSplitterSchema
    DESCRIPTION = MultilingualString(
        en=(
            "Holds out the end of a series: the model is scored on the "
            "horizon steps before the test, then refitted and scored on the "
            "last horizon steps. Never shuffles."
        ),
        es=(
            "Reserva el final de una serie: el modelo se evalua en los pasos "
            "del horizonte anteriores al test y luego se reajusta y se evalua "
            "en los ultimos pasos del horizonte. Nunca mezcla."
        ),
        pt=(
            "Reserva o final de uma serie: o modelo e avaliado nos passos do "
            "horizonte anteriores ao teste e depois e reajustado e avaliado "
            "nos ultimos passos do horizonte. Nunca embaralha."
        ),
        de=(
            "Haelt das Ende einer Zeitreihe zurueck: Das Modell wird auf den "
            "Horizontschritten vor dem Test bewertet, dann neu angepasst und "
            "auf den letzten Horizontschritten bewertet. Es wird nie gemischt."
        ),
        zh=(
            "保留序列的末尾：模型先在测试之前的预测步长上评分，"
            "再重新拟合并在最后的预测步长上评分。从不打乱顺序。"
        ),
    )
    COMPATIBLE_COMPONENTS = ["SingleSeriesForecastingTask"]
    DISPLAY_NAME: str = MultilingualString(
        en="Temporal Holdout",
        es="Holdout Temporal",
        pt="Holdout Temporal",
        de="Zeitlicher Holdout",
        zh="时序留出法",
    )

    def __init__(self, splits_data):
        """Read the horizon; a holdout has one validation origin.

        Parameters
        ----------
        splits_data : dict
            The splitter's configuration.
        """
        super().__init__({**splits_data, "n_origins": 1})

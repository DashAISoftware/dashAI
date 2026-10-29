from __future__ import annotations

from pydantic import ConfigDict

from DashAI.back.core.schema_fields import BaseSchema, int_field, schema_field
from DashAI.back.core.utils import MultilingualString

from .origin_splitter import OriginSplitter, horizon_field


class RollingOriginSplitterSchema(BaseSchema):
    """Schema that configures the rolling origin splitter."""

    # A key it does not know is refused rather than dropped: the parameters
    # these splitters took before they cut in steps (train, validation and
    # test proportions; n_splits, step, test_size) would otherwise leave a
    # session running on the defaults without a word.
    model_config = ConfigDict(extra="forbid")

    horizon: horizon_field()  # type: ignore
    n_origins: schema_field(
        int_field(ge=2),
        placeholder=3,
        description=MultilingualString(
            en=(
                "How many validation windows the model is scored on, each one "
                "horizon after the last and each with more history."
            ),
            es=(
                "En cuantas ventanas de validacion se evalua el modelo, cada "
                "una un horizonte despues de la anterior y con mas historia."
            ),
            pt=(
                "Em quantas janelas de validacao o modelo e avaliado, cada uma "
                "um horizonte depois da anterior e com mais historia."
            ),
            de=(
                "Auf wie vielen Validierungsfenstern das Modell bewertet wird, "
                "jedes einen Horizont nach dem vorigen und mit mehr Historie."
            ),
            zh="模型在多少个验证窗口上评分，每个窗口比上一个晚一个预测步长，历史更长。",
        ),
        alias=MultilingualString(
            en="Number of origins",
            es="Numero de origenes",
            pt="Numero de origens",
            de="Anzahl der Ursprunge",
            zh="起点数量",
        ),
    )  # type: ignore


class RollingOriginSplitter(OriginSplitter):
    """Cross-validate a series by walking the origin forward through time.

    The model is fitted on everything before each origin and scored on the
    ``horizon`` steps after it; the origin then advances by one horizon and the
    model is refitted with more history. The last horizon is the test::

        n = 48, horizon = 6, 3 origins

        validation   fit [0, 24)  forecast [24, 30)
        validation   fit [0, 30)  forecast [30, 36)
        validation   fit [0, 36)  forecast [36, 42)
        test         fit [0, 42)  forecast [42, 48)

    This is what k-fold cannot do for a series: its folds train on rows that
    come after the ones they score, which measures interpolation rather than
    forecasting. The validation score is the mean over the origins.
    """

    SCHEMA = RollingOriginSplitterSchema
    DESCRIPTION = MultilingualString(
        en=(
            "Walks the origin forward through a series. The model is fitted "
            "on everything before each origin and scored on the horizon steps "
            "after it; the origin then advances by one horizon. The last "
            "horizon is the test."
        ),
        es=(
            "Avanza el origen a lo largo de una serie. El modelo se ajusta con "
            "todo lo anterior a cada origen y se evalua en los pasos del "
            "horizonte siguientes; luego el origen avanza un horizonte. El "
            "ultimo horizonte es el test."
        ),
        pt=(
            "Avanca a origem ao longo de uma serie. O modelo e ajustado com "
            "tudo o que vem antes de cada origem e avaliado nos passos do "
            "horizonte seguintes; entao a origem avanca um horizonte. O ultimo "
            "horizonte e o teste."
        ),
        de=(
            "Schiebt den Ursprung durch eine Zeitreihe. Das Modell wird auf "
            "allem vor jedem Ursprung angepasst und auf den folgenden "
            "Horizontschritten bewertet; dann rueckt der Ursprung um einen "
            "Horizont weiter. Der letzte Horizont ist der Test."
        ),
        zh=(
            "让起点沿序列向前推进。模型用每个起点之前的全部数据拟合，"
            "并在其后的预测步长上评分；随后起点前移一个预测步长。"
            "最后一个预测步长用于测试。"
        ),
    )
    COMPATIBLE_COMPONENTS = ["SingleSeriesForecastingTask"]
    DISPLAY_NAME: str = MultilingualString(
        en="Rolling Origin",
        es="Origen Movil",
        pt="Origem Movel",
        de="Rollierender Ursprung",
        zh="滚动起点",
    )

    def __init__(self, splits_data):
        """Read the horizon and the number of validation origins.

        Parameters
        ----------
        splits_data : dict
            The splitter's configuration.
        """
        super().__init__({"n_origins": 3, **splits_data})

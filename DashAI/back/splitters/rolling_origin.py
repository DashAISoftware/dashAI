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
                "En cuántas ventanas de validación se evalúa el modelo, cada "
                "una un horizonte después de la anterior y con más historia."
            ),
            pt=(
                "Em quantas janelas de validação o modelo é avaliado, cada uma "
                "um horizonte depois da anterior e com mais história."
            ),
            de=(
                "Auf wie vielen Validierungsfenstern das Modell bewertet wird, "
                "jedes einen Horizont nach dem vorigen und mit mehr Historie."
            ),
            zh="模型在多少个验证窗口上评分，每个窗口比上一个晚一个预测步长，历史更长。",
        ),
        alias=MultilingualString(
            en="Number of origins",
            es="Número de orígenes",
            pt="Número de origens",
            de="Anzahl der Ursprünge",
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
            "todo lo anterior a cada origen y se evalúa en los pasos del "
            "horizonte siguientes; luego el origen avanza un horizonte. El "
            "último horizonte es el test."
        ),
        pt=(
            "Avança a origem ao longo de uma série. O modelo é ajustado com "
            "tudo o que vem antes de cada origem e avaliado nos passos do "
            "horizonte seguintes; então a origem avança um horizonte. O último "
            "horizonte é o teste."
        ),
        de=(
            "Schiebt den Ursprung durch eine Zeitreihe. Das Modell wird auf "
            "allem vor jedem Ursprung angepasst und auf den folgenden "
            "Horizontschritten bewertet; dann rückt der Ursprung um einen "
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
        es="Origen Móvil",
        pt="Origem Móvel",
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

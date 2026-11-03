"""Holdout evaluation for models that forecast a series from its own history."""

from DashAI.back.core.enums.metrics import SplitEnum
from DashAI.back.core.utils import MultilingualString
from DashAI.back.evaluation.holdout import SinglePartitionEvaluationStrategy


class ForecastingHoldoutEvaluationStrategy(SinglePartitionEvaluationStrategy):
    """A backtest with one validation origin, then the test.

    Pair it with ``TemporalHoldoutSplitter``. The model is fitted on the steps
    before the validation window and scored on its ``horizon`` steps, then
    refitted on everything before the test and scored on the last ``horizon``
    steps. Validation and test measure the same horizon, so the two columns of
    the results compare like with like.

    It runs the same units as the rolling origin (``KIND = "backtest"``): a
    holdout is a backtest with one origin. The training steps are never
    scored, since a forecaster asked about steps it was fitted on reports a
    fit, not a forecast. A search measures its trials on validation only. The
    kept model is fitted on the whole series, and the metrics are the
    backtest's (RECONCILING_FORECASTING §2.13).
    """

    DESCRIPTION = MultilingualString(
        en=(
            "Cuts the series once, in time order: the model trains on the "
            "earliest rows and is scored on the ones that come after. The "
            "training partition is not scored, since a forecaster asked about "
            "dates it was fitted on reports a fit, not a forecast."
        ),
        es=(
            "Corta la serie una sola vez, en orden temporal: el modelo entrena "
            "con las filas mas antiguas y se evalua con las que vienen despues. "
            "La particion de entrenamiento no se evalua, porque preguntarle a un "
            "pronosticador por fechas con las que fue ajustado da un ajuste, no "
            "un pronostico."
        ),
        pt=(
            "Corta a serie uma unica vez, em ordem temporal: o modelo treina nas "
            "linhas mais antigas e e avaliado nas que vem depois. A particao de "
            "treino nao e avaliada, porque perguntar a um previsor sobre datas "
            "em que ele foi ajustado da um ajuste, nao uma previsao."
        ),
        de=(
            "Teilt die Zeitreihe ein einziges Mal in zeitlicher Reihenfolge: Das "
            "Modell trainiert auf den fruehesten Zeilen und wird auf den "
            "folgenden bewertet. Die Trainingspartition wird nicht bewertet, "
            "denn ein Prognosemodell, das nach Daten seiner eigenen Anpassung "
            "gefragt wird, liefert eine Anpassung und keine Prognose."
        ),
        zh=(
            "按时间顺序只切分序列"
            "一次：模型在最早的行"
            "上训练，并在其后的行"
            "上评分。训练部分不参"
            "与评分，因为让预测模"
            "型回答它自己拟合过的"
            "日期，得到的是拟合而"
            "不是预测。"
        ),
    )

    COMPATIBLE_COMPONENTS = ["SingleSeriesForecastingTask"]
    SCORED_SPLITS: tuple = (SplitEnum.VALIDATION, SplitEnum.TEST)
    # A holdout is a backtest with one origin, so both forecasting strategies
    # run the same units: ModelJob dispatches them on this one KIND.
    KIND = "backtest"
    # Both take a splitter that cuts the series into origins, in steps.
    SPLITTER_PARTITIONING = "origins"

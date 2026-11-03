"""Cross-validation for models that forecast a series from its own history."""

from DashAI.back.core.enums.metrics import SplitEnum
from DashAI.back.core.utils import MultilingualString
from DashAI.back.evaluation.cv import FoldEvaluationStrategy


class ForecastingCrossValidationEvaluationStrategy(FoldEvaluationStrategy):
    """A backtest over several validation origins, then the test.

    Pair it with ``RollingOriginSplitter``. Each origin fits on the steps before
    it and is scored on the ``horizon`` steps after it; the validation score is
    the mean over the origins, which is also what a search optimizes. The
    test is one more origin, at the end.

    It runs the same units as the forecasting holdout (``KIND = "backtest"``).
    The training steps are never scored, and the kept model is fitted on the
    whole series (RECONCILING_FORECASTING §2.13).
    """

    DESCRIPTION = MultilingualString(
        en=(
            "Walks the origin forward through the series. Each fold trains on "
            "everything up to a point and is scored on the rows just after it, "
            "then the origin moves on and the model is refitted with more "
            "history. Training partitions are not scored."
        ),
        es=(
            "Avanza el origen a lo largo de la serie. Cada pliegue entrena con "
            "todo lo anterior a un punto y se evalúa con las filas justo "
            "posteriores; luego el origen avanza y el modelo se reajusta con más "
            "historia. Las particiones de entrenamiento no se evalúan."
        ),
        pt=(
            "Avança a origem ao longo da série. Cada dobra treina com tudo o que "
            "vem antes de um ponto e é avaliada nas linhas logo depois; então a "
            "origem avança e o modelo é reajustado com mais histórico. As "
            "partições de treino não são avaliadas."
        ),
        de=(
            "Schiebt den Ursprung durch die Zeitreihe. Jeder Fold trainiert auf "
            "allem bis zu einem Punkt und wird auf den unmittelbar folgenden "
            "Zeilen bewertet, dann rückt der Ursprung weiter und das Modell "
            "wird mit mehr Historie neu angepasst. Trainingspartitionen werden "
            "nicht bewertet."
        ),
        zh=(
            "让起点沿序列向前推进。"
            "每一折用某个时点之前的"
            "全部数据训练，并在紧随"
            "其后的行上评分；随后起"
            "点前移，模型用更多历史"
            "重新拟合。训练部分不参"
            "与评分。"
        ),
    )

    COMPATIBLE_COMPONENTS = ["SingleSeriesForecastingTask"]
    SCORED_SPLITS: tuple = (SplitEnum.VALIDATION, SplitEnum.TEST)
    # The same backtest as the forecasting holdout, with more than one origin:
    # ModelJob dispatches both on this one KIND.
    KIND = "backtest"
    # Both take a splitter that cuts the series into origins, in steps.
    SPLITTER_PARTITIONING = "origins"
    DEFAULT_SPLITTER = "RollingOriginSplitter"
    # Both splitters cut origins, so the partitioning alone would take the
    # other strategy's: the same backtest under this strategy's label.
    SPLITTERS: tuple = ("RollingOriginSplitter",)
    # One score per origin, and the forecasts of every origin.
    RESULT_VIEWS: tuple = ("fold_metrics", "forecasts")

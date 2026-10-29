"""DashAI MAPE forecasting metric implementation."""

from typing import TYPE_CHECKING

from DashAI.back.core.utils import MultilingualString
from DashAI.back.metrics.forecasting_metric import ForecastingMetric, PointMetricMixin
from DashAI.back.metrics.regression_metric import prepare_to_metric
from DashAI.back.metrics.undefined_metric import UndefinedMetricError

if TYPE_CHECKING:
    import numpy as np

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class MAPE(PointMetricMixin, ForecastingMetric):
    """Average error as a percentage of the true value.

    Mean Absolute Percentage Error expresses each error relative to the value
    it missed, so a forecast can be judged without knowing the scale of the
    series. That is what makes it the usual way to compare a forecast across
    products, regions or periods whose magnitudes differ by orders of
    magnitude, where an absolute error in units says nothing on its own.

    ::

        MAPE(y, y') = 100 / N  ·  sum |yi - y'i| / |yi|

    Range: [0, +inf), lower is better.

    The formula divides by the true value, so it is undefined wherever that
    value is zero, and then the whole score is undefined: averaging only the
    other rows would report the error of a different series, and an infinity
    says nothing. It raises ``UndefinedMetricError``, which a run records as
    "not available" with the reason. Prefer :class:`SMAPE` or :class:`MASE`
    on series that reach zero.

    MAPE is also asymmetric: it penalises a forecast that is too high more
    heavily than one that is too low by the same amount, since the denominator
    stays fixed while the error does not.

    References
    ----------
    - [1] https://otexts.com/fpp3/accuracy.html
    """

    DESCRIPTION = MultilingualString(
        en=(
            "Average error as a percentage of the true value, so forecasts can "
            "be compared across series of different sizes. Not available when "
            "any true value is zero."
        ),
        es=(
            "Error promedio como porcentaje del valor real, lo que permite "
            "comparar pronosticos entre series de distinta magnitud. No esta "
            "disponible si algun valor real es cero."
        ),
        pt=(
            "Erro medio como porcentagem do valor real, permitindo comparar "
            "previsoes entre series de magnitudes diferentes. Nao esta "
            "disponivel se algum valor real for zero."
        ),
        de=(
            "Durchschnittlicher Fehler als Prozentsatz des wahren Wertes, "
            "sodass Prognosen ueber unterschiedlich grosse Reihen hinweg "
            "vergleichbar sind. Nicht verfuegbar, wenn ein wahrer Wert null "
            "ist."
        ),
        zh=(
            "以真实值的百分比表示的平均误差，便于比较不同量级序列的预测效果。"
            "任一真实值为零时不可用。"
        ),
    )

    @staticmethod
    def score(
        true_values: "DashAIDataset",
        pred_values: "np.ndarray",
    ) -> float:
        """Calculate the MAPE between true values and predicted values.

        Parameters
        ----------
        true_values : DashAIDataset
            A DashAI dataset with true values.
        pred_values : np.ndarray
            A one-dimensional array with the predicted values for each
            instance.

        Returns
        -------
        float
            MAPE as a percentage.

        Raises
        ------
        UndefinedMetricError
            If any true value is zero.
        """
        import numpy as np

        true_values, pred_values = prepare_to_metric(true_values, pred_values)

        zeros = np.flatnonzero(true_values == 0)
        if len(zeros):
            raise UndefinedMetricError(
                "MAPE divides by each actual value, and the actual value is zero",
                positions=zeros,
                hint="Use SMAPE or MASE for a series that reaches zero.",
            )

        errors = np.abs(true_values - pred_values)
        return float(100 * np.mean(errors / np.abs(true_values)))

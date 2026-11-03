from typing import TYPE_CHECKING, Any, Optional

from DashAI.back.core.schema_fields import BaseSchema, int_field, search_space
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.forecasting.single_series_forecasting_model import (
    SingleSeriesForecastingModel,
)

if TYPE_CHECKING:
    import numpy as np


class SeasonalNaiveForecasterSchema(BaseSchema):
    """Schema that configures the seasonal naive forecaster."""

    season_length: search_space(
        int_field(ge=1),
        fixed=1,
        low=1,
        high=12,
        description=MultilingualString(
            en=(
                "How many observations make up one full cycle: 12 for monthly "
                "data repeating yearly, 7 for daily data repeating weekly. "
                "Leave it at 1 when the series has no season, which makes this "
                "the plain naive forecast."
            ),
            es=(
                "Cuantas observaciones forman un ciclo completo: 12 para datos "
                "mensuales que se repiten cada ano, 7 para datos diarios que se "
                "repiten cada semana. Dejar en 1 cuando la serie no tiene "
                "estacionalidad, lo que equivale al pronostico ingenuo simple."
            ),
            pt=(
                "Quantas observacoes formam um ciclo completo: 12 para dados "
                "mensais que se repetem a cada ano, 7 para dados diarios que se "
                "repetem a cada semana. Deixe em 1 quando a serie nao tem "
                "sazonalidade, o que equivale a previsao ingenua simples."
            ),
            de=(
                "Wie viele Beobachtungen einen vollen Zyklus bilden: 12 fuer "
                "monatliche Daten mit jaehrlicher Wiederholung, 7 fuer "
                "taegliche Daten mit woechentlicher. Bei 1 belassen, wenn die "
                "Reihe keine Saison hat, was der einfachen naiven Prognose "
                "entspricht."
            ),
            zh=(
                "一个完整周期包含多少个观测值：月度数据按年重复为 12，"
                "日度数据按周重复为 7。序列没有季节性时保持为 1，"
                "此时等同于普通的朴素预测。"
            ),
        ),
        alias=MultilingualString(
            en="Season length",
            es="Longitud de estacion",
            pt="Comprimento da estacao",
            de="Saisonlaenge",
            zh="季节长度",
        ),
    )  # type: ignore


class SeasonalNaiveForecaster(SingleSeriesForecastingModel):
    """Predict that each season repeats the one before it.

    Every future value is forecast as the value one full season earlier, so a
    monthly series with ``season_length = 12`` predicts next January from last
    January.

    On anything with a strong repeating pattern this is a much harder baseline
    than the plain naive forecast, and a seasonal model that cannot beat it has
    learned nothing beyond the repetition. With ``season_length = 1`` it is
    exactly :class:`NaiveForecaster`.

    The season length is not inferred. Monthly data may repeat yearly or not
    repeat at all, and only someone who knows what the series measures can say
    which.

    References
    ----------
    - [1] https://otexts.com/fpp3/simple-methods.html
    """

    SCHEMA = SeasonalNaiveForecasterSchema
    DESCRIPTION = MultilingualString(
        en=(
            "Predicts that each value repeats the one a full season earlier, "
            "for example next January from last January. A far harder baseline "
            "than the naive forecast on any series with a repeating pattern."
        ),
        es=(
            "Predice que cada valor repite el de una estacion completa antes, "
            "por ejemplo el proximo enero a partir del enero anterior. Una "
            "linea base mucho mas exigente que el pronostico ingenuo en "
            "cualquier serie con un patron repetitivo."
        ),
        pt=(
            "Preve que cada valor repete o de uma estacao completa antes, por "
            "exemplo o proximo janeiro a partir do janeiro anterior. Uma linha "
            "de base bem mais exigente que a previsao ingenua em qualquer "
            "serie com padrao repetitivo."
        ),
        de=(
            "Sagt voraus, dass sich jeder Wert von vor einer vollen Saison "
            "wiederholt, etwa der naechste Januar aus dem letzten Januar. Eine "
            "deutlich haertere Grundlinie als die naive Prognose bei jeder "
            "Reihe mit wiederkehrendem Muster."
        ),
        zh=(
            "预测每个值重复一个完整季节之前的值，例如用去年一月预测下个一月。"
            "对于任何具有重复模式的序列，这都是比朴素预测严格得多的基准。"
        ),
    )
    DISPLAY_NAME = MultilingualString(
        en="Seasonal Naive Forecaster",
        es="Pronostico Ingenuo Estacional",
        pt="Previsao Ingenua Sazonal",
        de="Saisonale Naive Prognose",
        zh="季节性朴素预测",
    )

    def __init__(self, season_length: int = 1, **kwargs):
        """Initialise the forecaster with the length of one cycle.

        Parameters
        ----------
        season_length : int
            Observations per full cycle. 1 means no seasonality.
        **kwargs
            Ignored, accepted for consistency with the other models.

        Raises
        ------
        ValueError
            If ``season_length`` is less than 1.
        """
        super().__init__(**kwargs)
        if season_length < 1:
            raise ValueError(
                f"'season_length' must be at least 1, got {season_length}."
            )
        self.season_length = season_length

    SUPPORTS_INTERVALS = True

    def _fit(self, y: "np.ndarray", x: Optional[Any]) -> None:
        """Remember the most recent full season, and the seasonal spread.

        Parameters
        ----------
        y : np.ndarray
            The series, in time order.
        X : None
            The model uses no exogenous variables.

        Raises
        ------
        ValueError
            If the series is shorter than one season, since there would be no
            complete cycle to repeat.
        """
        import numpy as np

        m = self.season_length
        if len(y) < m:
            raise ValueError(
                f"A season of {m} needs at least that many observations to "
                f"repeat, but the series has {len(y)}. Shorten the season "
                "length or supply more history."
            )

        self._last_season = [float(v) for v in y[-m:]]
        # The residual is the change from the same step a season earlier, and
        # the first season has none: fpp3 estimates over the T - m there are.
        changes = y[m:] - y[:-m]
        self._sigma = (
            float(np.sqrt(np.mean(changes**2))) if len(changes) else float("nan")
        )

    def _forecast(self, h: int, x_future: Optional[Any]) -> "np.ndarray":
        """Repeat the last full season out to the requested length.

        Parameters
        ----------
        h : int
            How many steps to forecast.
        x_future : None
            The model uses no exogenous variables.

        Returns
        -------
        np.ndarray
            The last observed season, tiled to the requested length.
        """
        import numpy as np

        return np.array(
            [self._last_season[i % self.season_length] for i in range(h)],
            dtype=float,
        )

    def _intervals(self, h: int, levels, x_future: Optional[Any]):
        """Normal intervals that widen once per completed season.

        fpp3 §5.5: the h-step standard deviation is the one-step one times
        sqrt(k + 1), where k is the number of complete seasons before step h.
        A series of one season has no seasonal change to measure, so its
        bounds are not a number.
        """
        import numpy as np

        k = (np.arange(1, h + 1) - 1) // self.season_length
        sd = self._sigma * np.sqrt(k + 1)
        return self._normal_bounds(self._forecast(h, None), sd, levels)

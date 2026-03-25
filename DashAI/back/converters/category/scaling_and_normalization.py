from typing import Final

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.core.utils import MultilingualString
from DashAI.back.static.icons import Icon


class ScalingAndNormalizationConverter(BaseConverter):
    CATEGORY = MultilingualString(
        en="Scaling and Normalization", es="Escalado y Normalización"
    )
    ICON: Final[str] = Icon.TrendingUp.value
    COLOR: Final[str] = "rgb(255, 165, 0)"

from typing import Final

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.core.utils import MultilingualString
from DashAI.back.static.icons import Icon


class SamplingConverter(BaseConverter):
    CATEGORY = MultilingualString(
        en="Resampling & Class Balancing", es="Remuestreo y Balanceo de Clases"
    )
    ICON: Final[str] = Icon.Casino.value
    COLOR: Final[str] = "rgb(255, 159, 64)"

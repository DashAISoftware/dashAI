from typing import Final

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.core.utils import MultilingualString
from DashAI.back.static.icons import Icon


class DimensionalityReductionConverter(BaseConverter):
    CATEGORY = MultilingualString(
        en="Dimensionality Reduction", es="Reducción de Dimensionalidad"
    )
    ICON: Final[str] = Icon.Layers.value
    COLOR: Final[str] = "rgb(255, 99, 132)"

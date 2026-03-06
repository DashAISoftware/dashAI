from typing import Final

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.core.utils import MultilingualString
from DashAI.back.static.icons import Icon


class AdvancedPreprocessingConverter(BaseConverter):
    CATEGORY: Final[str] = MultilingualString(
        en="Advanced Preprocessing", es="Preprocesamiento Avanzado"
    )
    ICON: Final[str] = Icon.Psychology.value
    COLOR: Final[str] = "rgb(70, 130, 180)"

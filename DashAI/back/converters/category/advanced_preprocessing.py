from beartype.typing import Final

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.core.utils import MultilingualString


class AdvancedPreprocessingConverter(BaseConverter):
    CATEGORY: Final[str] = MultilingualString(
        en="Advanced Preprocessing", es="Preprocesamiento Avanzado"
    )
    COLOR: Final[str] = "rgb(70, 130, 180)"

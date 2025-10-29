from beartype.typing import Final

from DashAI.back.converters.base_converter import BaseConverter


class AdvancedPreprocessingConverter(BaseConverter):
    CATEGORY: Final[str] = "Advanced Preprocessing"
    COLOR: Final[str] = "rgb(70, 130, 180)"

from beartype.typing import Final

from DashAI.back.converters.base_converter import BaseConverter


class BasicPreprocessingConverter(BaseConverter):
    CATEGORY: Final[str] = "Basic Preprocessing"
    COLOR: Final[str] = "rgb(60, 179, 113)"

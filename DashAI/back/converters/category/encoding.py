from beartype.typing import Final

from DashAI.back.converters.base_converter import BaseConverter


class EncodingConverter(BaseConverter):
    CATEGORY: Final[str] = "Encoding"
    COLOR: Final[str] = "rgb(138, 43, 226)"

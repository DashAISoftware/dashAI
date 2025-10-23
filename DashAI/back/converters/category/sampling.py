from beartype.typing import Final

from DashAI.back.converters.base_converter import BaseConverter


class SamplingConverter(BaseConverter):
    CATEGORY: Final[str] = "Sampling"
    COLOR: Final[str] = "rgb(255, 159, 64)"

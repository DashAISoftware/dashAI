from beartype.typing import Final

from DashAI.back.converters.base_converter import BaseConverter


class DimensionalityReductionConverter(BaseConverter):
    CATEGORY: Final[str] = "Dimensionality Reduction"
    COLOR: Final[str] = "rgb(255, 99, 132)"

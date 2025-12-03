from beartype.typing import Final

from DashAI.back.converters.base_converter import BaseConverter


class ScalingAndNormalizationConverter(BaseConverter):
    CATEGORY: Final[str] = "Scaling and Normalization"
    COLOR: Final[str] = "rgb(255, 165, 0)"

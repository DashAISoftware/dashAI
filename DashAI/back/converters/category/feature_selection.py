from beartype.typing import Final

from DashAI.back.converters.base_converter import BaseConverter


class FeatureSelectionConverter(BaseConverter):
    CATEGORY: Final[str] = "Feature Selection"
    COLOR: Final[str] = "rgb(255, 206, 86)"

from beartype.typing import Final

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.core.utils import MultilingualString
from DashAI.back.static.icons import Icon


class FeatureSelectionConverter(BaseConverter):
    CATEGORY = MultilingualString(
        en="Feature Selection", es="Selección de Características"
    )
    ICON: Final[str] = Icon.FilterList.value
    COLOR: Final[str] = "rgb(255, 206, 86)"

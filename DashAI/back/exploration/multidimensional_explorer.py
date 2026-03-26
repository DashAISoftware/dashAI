from typing import Final

from DashAI.back.core.utils import MultilingualString
from DashAI.back.exploration.base_explorer import BaseExplorer
from DashAI.back.static.icons import Icon


class MultidimensionalExplorer(BaseExplorer):
    CATEGORY: Final[str] = MultilingualString(
        en="Multidimensional Analysis", es="Análisis Multidimensional"
    )
    ICON: Final[str] = Icon.Timeline.value
    COLOR: Final[str] = "rgb(241, 196, 15)"

from typing import Final

from DashAI.back.core.utils import MultilingualString
from DashAI.back.exploration.base_explorer import BaseExplorer
from DashAI.back.static.icons import Icon


class StatisticalExplorer(BaseExplorer):
    CATEGORY: Final[str] = MultilingualString(
        en="Statistical Analysis", es="Análisis Estadístico"
    )
    ICON: Final[str] = Icon.Functions.value
    COLOR: Final[str] = "rgb(231, 76, 60)"

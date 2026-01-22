from beartype.typing import Final

from DashAI.back.core.utils import MultilingualString
from DashAI.back.exploration.base_explorer import BaseExplorer


class StatisticalExplorer(BaseExplorer):
    CATEGORY: Final[str] = MultilingualString(
        en="Statistical Analysis", es="Análisis Estadístico"
    )
    COLOR: Final[str] = "rgb(231, 76, 60)"

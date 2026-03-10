from beartype.typing import Final

from DashAI.back.core.utils import MultilingualString
from DashAI.back.exploration.base_explorer import BaseExplorer
from DashAI.back.static.icons import Icon


class DistributionExplorer(BaseExplorer):
    CATEGORY: Final[str] = MultilingualString(
        en="Distribution Analysis", es="Análisis de Distribución"
    )
    ICON: Final[str] = Icon.BarChart.value
    COLOR: Final[str] = "rgb(155, 89, 182)"

from beartype.typing import Final

from DashAI.back.core.utils import MultilingualString
from DashAI.back.exploration.base_explorer import BaseExplorer


class DistributionExplorer(BaseExplorer):
    CATEGORY: Final[str] = MultilingualString(
        en="Distribution Analysis", es="Análisis de Distribución"
    )
    COLOR: Final[str] = "rgb(155, 89, 182)"

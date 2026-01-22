from beartype.typing import Final

from DashAI.back.core.utils import MultilingualString
from DashAI.back.exploration.base_explorer import BaseExplorer


class MultidimensionalExplorer(BaseExplorer):
    CATEGORY: Final[str] = MultilingualString(
        en="Multidimensional Analysis", es="Análisis Multidimensional"
    )
    COLOR: Final[str] = "rgb(241, 196, 15)"

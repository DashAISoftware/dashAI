from beartype.typing import Final

from DashAI.back.exploration.base_explorer import BaseExplorer


class MultidimensionalExplorer(BaseExplorer):
    CATEGORY: Final[str] = "Multidimensional"
    COLOR: Final[str] = "rgb(241, 196, 15)"

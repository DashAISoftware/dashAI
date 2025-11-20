from beartype.typing import Final

from DashAI.back.exploration.base_explorer import BaseExplorer


class StatisticalExplorer(BaseExplorer):
    CATEGORY: Final[str] = "Statistical"
    COLOR: Final[str] = "rgb(231, 76, 60)"

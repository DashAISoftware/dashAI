from beartype.typing import Final

from DashAI.back.exploration.base_explorer import BaseExplorer


class DistributionExplorer(BaseExplorer):
    CATEGORY: Final[str] = "Distribution"
    COLOR: Final[str] = "rgb(155, 89, 182)"

from beartype.typing import Final

from DashAI.back.exploration.base_explorer import BaseExplorer


class RelationshipExplorer(BaseExplorer):
    CATEGORY: Final[str] = "Relationship"
    COLOR: Final[str] = "rgb(46, 204, 113)"

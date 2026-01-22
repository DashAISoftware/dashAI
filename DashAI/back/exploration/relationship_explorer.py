from beartype.typing import Final

from DashAI.back.core.utils import MultilingualString
from DashAI.back.exploration.base_explorer import BaseExplorer


class RelationshipExplorer(BaseExplorer):
    CATEGORY: Final[str] = MultilingualString(
        en="Relationship Analysis", es="Análisis de Relaciones"
    )
    COLOR: Final[str] = "rgb(46, 204, 113)"

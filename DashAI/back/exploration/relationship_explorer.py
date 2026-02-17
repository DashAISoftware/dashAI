from beartype.typing import Final

from DashAI.back.core.utils import MultilingualString
from DashAI.back.exploration.base_explorer import BaseExplorer
from DashAI.back.static.icons import Icon


class RelationshipExplorer(BaseExplorer):
    CATEGORY: Final[str] = MultilingualString(
        en="Relationship Analysis", es="Análisis de Relaciones"
    )
    ICON: Final[str] = Icon.ScatterPlot.value
    COLOR: Final[str] = "rgb(46, 204, 113)"

from typing import Final

from DashAI.back.core.utils import MultilingualString
from DashAI.back.exploration.base_explorer import BaseExplorer
from DashAI.back.static.icons import Icon


class DistributionExplorer(BaseExplorer):
    """Base class for explorers that analyze the statistical distribution of columns.

    Distribution explorers generate visualizations such as histograms, box
    plots, ECDF plots, and density plots that show how values in a column
    are spread, centered, and shaped.

    Subclass this and implement `launch_exploration`, `save_notebook`, and
    `get_results` to create a new distribution explorer.
    """

    CATEGORY: Final[str] = MultilingualString(
        en="Distribution Analysis", es="Análisis de Distribución"
    )
    ICON: Final[str] = Icon.BarChart.value
    COLOR: Final[str] = "rgb(155, 89, 182)"
    TAGS: Final[list] = ["distribution", "univariate", "visualization"]

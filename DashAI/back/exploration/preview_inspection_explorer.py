from beartype.typing import Final

from DashAI.back.exploration.base_explorer import BaseExplorer


class PreviewInspectionExplorer(BaseExplorer):
    CATEGORY: Final[str] = "Preview Inspection"
    COLOR: Final[str] = "rgb(52, 152, 219)"

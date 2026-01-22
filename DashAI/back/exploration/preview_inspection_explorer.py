from beartype.typing import Final

from DashAI.back.core.utils import MultilingualString
from DashAI.back.exploration.base_explorer import BaseExplorer


class PreviewInspectionExplorer(BaseExplorer):
    CATEGORY: Final[str] = MultilingualString(
        en="Preview Inspection", es="Inspección Previa"
    )
    COLOR: Final[str] = "rgb(52, 152, 219)"

from typing import Final

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.core.utils import MultilingualString
from DashAI.back.static.icons import Icon


class BasicPreprocessingConverter(BaseConverter):
    CATEGORY = MultilingualString(
        en="Basic Preprocessing", es="Preprocesamiento Básico"
    )
    ICON: Final[str] = Icon.Build.value
    COLOR: Final[str] = "rgb(60, 179, 113)"

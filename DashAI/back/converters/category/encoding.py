from typing import Final

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.core.utils import MultilingualString
from DashAI.back.static.icons import Icon


class EncodingConverter(BaseConverter):
    CATEGORY = MultilingualString(en="Encoding", es="Codificación")
    ICON: Final[str] = Icon.Dns.value
    COLOR: Final[str] = "rgb(138, 43, 226)"

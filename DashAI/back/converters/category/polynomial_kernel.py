from typing import Final

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.core.utils import MultilingualString
from DashAI.back.static.icons import Icon


class PolynomialKernelConverter(BaseConverter):
    CATEGORY = MultilingualString(
        en="Polynomial & Kernel Methods", es="Métodos Polinomiales y de Kernel"
    )
    ICON: Final[str] = Icon.Functions.value
    COLOR: Final[str] = "rgb(153, 102, 255)"

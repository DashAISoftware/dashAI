from beartype.typing import Final

from DashAI.back.converters.base_converter import BaseConverter


class PolynomialKernelConverter(BaseConverter):
    CATEGORY: Final[str] = "Polynomial & Kernel Methods"
    COLOR: Final[str] = "rgb(153, 102, 255)"

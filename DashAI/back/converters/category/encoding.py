from typing import Final

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.core.utils import MultilingualString
from DashAI.back.static.icons import Icon


class EncodingConverter(BaseConverter):
    """Base class for converters that encode categorical features into numeric form.

    Encoding converters transform non-numeric columns into a representation
    that machine learning models can process. Examples include OneHotEncoder,
    OrdinalEncoder, LabelEncoder, and LabelBinarizer.

    Use these converters when the dataset contains string or categorical columns
    that must be converted before model training.
    """

    CATEGORY = MultilingualString(en="Encoding", es="Codificación")
    ICON: Final[str] = Icon.Dns.value
    COLOR: Final[str] = "rgb(138, 43, 226)"

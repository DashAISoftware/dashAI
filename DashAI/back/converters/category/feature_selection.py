from typing import Final

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.core.utils import MultilingualString
from DashAI.back.static.icons import Icon


class FeatureSelectionConverter(BaseConverter):
    """Base class for converters that select a subset of features from the dataset.

    Feature selection converters remove low-relevance columns based on
    statistical tests, thresholds, or rankings. Examples include SelectKBest,
    SelectPercentile, GenericUnivariateSelect, SelectFDR, SelectFPR, and
    SelectFWE.

    Use these converters to reduce overfitting, speed up training, and improve
    model interpretability by retaining only the most informative features.
    """

    CATEGORY = MultilingualString(
        en="Feature Selection",
        es="Selección de Características",
        pt="Seleção de Características",
        de="Merkmalsauswahl",
    )
    ICON: Final[str] = Icon.FilterList.value
    COLOR: Final[str] = "rgb(255, 206, 86)"

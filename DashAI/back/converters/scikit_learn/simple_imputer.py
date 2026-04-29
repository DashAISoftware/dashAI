from sklearn.impute import SimpleImputer as SimpleImputerOperation

from DashAI.back.converters.category.basic_preprocessing import (
    BasicPreprocessingConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    bool_field,
    enum_field,
    float_field,
    int_field,
    none_type,
    schema_field,
    string_field,
    union_type,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float, Integer


class SimpleImputerSchema(BaseSchema):
    """Schema for configuring the SimpleImputer converter.

    Wraps ``sklearn.impute.SimpleImputer`` and exposes strategy selection,
    fill value, copy behaviour, indicator stacking, and empty-feature
    handling as schema fields validated before being forwarded to the
    underlying scikit-learn estimator.
    """

    strategy: schema_field(
        enum_field(
            [
                "mean",
                "median",
                ["most_frequent", "constant"][0],
                "most_frequent",
                "constant",
            ]
        ),
        "mean",
        description=MultilingualString(
            en="The imputation strategy.",
            es="La estrategia de imputación.",
        ),
    )  # type: ignore
    fill_value: schema_field(
        none_type(union_type(int_field(), union_type(float_field(), string_field()))),
        None,
        description=MultilingualString(
            en="The value to replace missing values with.",
            es="El valor para reemplazar los valores faltantes.",
        ),
    )  # type: ignore
    add_indicator: schema_field(
        bool_field(),
        False,
        description=MultilingualString(
            en="If True, a MissingIndicator transform will stack onto output.",
            es=("Si es True, se apilará un MissingIndicator sobre la salida."),
        ),
    )  # type: ignore
    keep_empty_features: schema_field(
        bool_field(),
        False,
        description=MultilingualString(
            en="If True, empty features will be kept.",
            es="Si es True, se mantendrán las características vacías.",
        ),
    )  # type: ignore


class SimpleImputer(
    BasicPreprocessingConverter, SklearnWrapper, SimpleImputerOperation
):
    """Fill missing values using a simple univariate per-column strategy.

    Each feature is imputed independently using one of four strategies:

    * ``"mean"`` — replace missing values with the column mean (numeric only).
    * ``"median"`` — replace with the column median (numeric only).
    * ``"most_frequent"`` — replace with the most common value (works with
      strings and numeric data).
    * ``"constant"`` — replace with a fixed ``fill_value`` supplied by the
      user.

    Columns with all-missing values are handled according to the
    ``keep_empty_features`` flag. When ``add_indicator=True``, a
    ``MissingIndicator`` binary matrix is stacked onto the output. All
    output columns are typed as ``Float64`` in DashAI regardless of the
    original column type.

    Wraps ``sklearn.impute.SimpleImputer``.

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.impute.SimpleImputer.html
    """

    TAGS = ["imputation", "missing-data", "mixed"]
    SCHEMA = SimpleImputerSchema
    DESCRIPTION = MultilingualString(
        en=(
            "Univariate imputer for completing missing values with simple "
            "strategies. Replace missing values using a descriptive statistic "
            "(e.g. mean, median, or most frequent) along each column, or using "
            "a constant value."
        ),
        es=(
            "Imputador univariante para completar valores faltantes con "
            "estrategias simples. Reemplaza valores faltantes usando una "
            "estadística descriptiva (p. ej., media, mediana o más frecuente) "
            "por columna, o usando un valor constante."
        ),
    )
    DISPLAY_NAME = MultilingualString(en="Simple Imputer", es="Imputador Simple")
    IMAGE_PREVIEW = "simple_imputer.png"

    metadata = {
        "allowed_types": [Float, Integer, Categorical],
        "allowed_dtypes": [],
    }

    def __init__(self, **kwargs):
        """Initialize the SimpleImputer converter.

        Parameters
        ----------
        **kwargs
            Configuration keyword arguments matching the converter's
            schema fields. Forwarded to the underlying scikit-learn class.
        """
        super().__init__(**kwargs)

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Return the DashAI data type produced by this converter for a column.

        Parameters
        ----------
        column_name : str, optional
            Not used; all output columns share the
            same type. Defaults to None.

        Returns
        -------
        DashAIDataType
            A Float type backed by ``pyarrow.float64()``.
        """
        import pyarrow as pa

        return Float(arrow_type=pa.float64())

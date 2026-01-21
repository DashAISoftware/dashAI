import pyarrow as pa
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
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class SimpleImputerSchema(BaseSchema):
    strategy: schema_field(
        enum_field(
            [
                "mean",
                "median",
                "most_frequent, constant".split(", ")[0],
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
    use_copy: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en="If True, a copy of X will be created.",
            es="Si es True, se creará una copia de X.",
        ),
        alias=MultilingualString(en="copy", es="copiar"),
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
    """SciKit-Learn's SimpleImputer wrapper for DashAI."""

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
    CATEGORY = MultilingualString(
        en="Basic Preprocessing", es="Preprocesamiento Básico"
    )
    DISPLAY_NAME = MultilingualString(en="Simple Imputer", es="Imputador Simple")
    IMAGE_PREVIEW = "simple_imputer.png"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for imputed data."""
        return Float(arrow_type=pa.float64())

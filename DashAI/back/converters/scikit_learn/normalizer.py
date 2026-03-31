from sklearn.preprocessing import Normalizer as NormalizerOperation

from DashAI.back.converters.category.scaling_and_normalization import (
    ScalingAndNormalizationConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import bool_field, enum_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class NormalizerSchema(BaseSchema):
    norm: schema_field(
        enum_field(["l1", "l2", "max"]),
        "l2",
        description=MultilingualString(
            en="The norm to use to normalize each non-zero sample.",
            es="La norma a usar para normalizar cada muestra no nula.",
        ),
    )  # type: ignore
    use_copy: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en="Set to False to perform inplace row normalization.",
            es="Ponlo en False para normalizar filas in situ.",
        ),
        alias=MultilingualString(en="copy", es="copiar"),
    )  # type: ignore


class Normalizer(ScalingAndNormalizationConverter, SklearnWrapper, NormalizerOperation):
    """Normalize each sample (row) to unit norm.

    Unlike column-wise scalers, this transformer operates row-wise: each
    data point is scaled independently so that its norm (L1, L2, or max)
    equals 1. Useful for text classification or clustering algorithms that
    use the dot product or cosine similarity between samples.

    Wraps scikit-learn's ``Normalizer``.
    """

    SCHEMA = NormalizerSchema
    DESCRIPTION = MultilingualString(
        en="Normalize samples individually to unit norm.",
        es="Normaliza muestras individualmente a norma unitaria.",
    )
    DISPLAY_NAME = MultilingualString(en="Normalizer", es="Normalizador")
    IMAGE_PREVIEW = "normalizer.png"

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

from sklearn.preprocessing import MaxAbsScaler as MaxAbsScalerOperation

from DashAI.back.converters.category.scaling_and_normalization import (
    ScalingAndNormalizationConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import bool_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class MaxAbsScalerSchema(BaseSchema):
    """Schema for Max Abs Scaler hyperparameters."""

    use_copy: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en="Set to False to perform inplace scaling.",
            es="Ponlo en False para realizar el escalado in situ.",
        ),
        alias=MultilingualString(en="copy", es="copiar"),
    )  # type: ignore


class MaxAbsScaler(
    ScalingAndNormalizationConverter, SklearnWrapper, MaxAbsScalerOperation
):
    """Scale each feature by its maximum absolute value to the range [-1, 1].

    This scaler does not shift or center the data, so it preserves sparsity
    in sparse matrices. Suitable for data already centered at zero.

    Wraps scikit-learn's ``MaxAbsScaler``.
    """

    SCHEMA = MaxAbsScalerSchema
    DESCRIPTION = MultilingualString(
        en="Scale each feature by its maximum absolute value.",
        es="Escala cada característica por su valor absoluto máximo.",
    )
    DISPLAY_NAME = MultilingualString(en="Max Abs Scaler", es="Escalador Max Abs")
    IMAGE_PREVIEW = "max_abs_scaler.png"

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

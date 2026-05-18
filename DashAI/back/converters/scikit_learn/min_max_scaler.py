from sklearn.preprocessing import MinMaxScaler as MinMaxScalerOperation

from DashAI.back.converters.category.scaling_and_normalization import (
    ScalingAndNormalizationConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import bool_field, float_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float, Integer


class MinMaxScalerSchema(BaseSchema):
    """Schema for MinMaxScaler hyperparameters.

    Configures the target feature range, clipping behaviour, and copy semantics
    for sklearn's ``MinMaxScaler``. The ``min_range`` and ``max_range`` fields
    are combined into the ``feature_range`` tuple passed to the underlying
    scikit-learn class.
    """

    min_range: schema_field(
        float_field(ge=0),
        0,
        description=MultilingualString(
            en="The minimum value of the range to scale the data to.",
            es="El valor mínimo del rango al que escalar los datos.",
            pt="O valor mínimo do intervalo para escalonar os dados.",
        ),
    )  # type: ignore
    max_range: schema_field(
        float_field(ge=0),
        1,
        description=MultilingualString(
            en="The maximum value of the range to scale the data to.",
            es="El valor máximo del rango al que escalar los datos.",
            pt="O valor máximo do intervalo para escalonar os dados.",
        ),
    )  # type: ignore
    clip: schema_field(
        bool_field(),
        False,
        description=MultilingualString(
            en="Set to True to clip the data to the feature range.",
            es="Ponlo en True para recortar los datos al rango de características.",
            pt=(
                "Defina como True para recortar os dados ao intervalo "
                "de características."
            ),
        ),
    )  # type: ignore


class MinMaxScaler(
    ScalingAndNormalizationConverter, SklearnWrapper, MinMaxScalerOperation
):
    """Scale each feature to a fixed range, by default [0, 1].

    For each feature column the transformation is::

        x_scaled = (x - x_min) / (x_max - x_min) * (max - min) + min

    where ``x_min`` and ``x_max`` are the per-feature minimum and maximum
    observed during fitting, and ``min``/``max`` are the bounds of the
    configured ``feature_range``.

    Unlike ``StandardScaler``, this scaler is sensitive to outliers because
    the range is anchored to the observed extremes. It is appropriate when
    the downstream model requires bounded inputs (e.g. neural networks with
    sigmoid activations, k-nearest neighbours, or image pixel values that
    must lie in [0, 1]).

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.MinMaxScaler.html
    """

    SCHEMA = MinMaxScalerSchema
    DESCRIPTION = MultilingualString(
        en="Transform features by scaling each feature to a given range.",
        es="Transforma características escalándolas a un rango dado.",
        pt="Transforma características escalonando cada uma para um intervalo dado.",
    )
    DISPLAY_NAME = MultilingualString(
        en="Min-Max Scaler",
        es="Escalador Min-Max",
        pt="Normalizador Min-Max",
    )
    IMAGE_PREVIEW = "min_max_scaler.png"

    metadata = {
        "allowed_types": [Float, Integer],
        "allowed_dtypes": [],
    }

    def __init__(self, **kwargs):
        """Initialize the MinMaxScaler converter.

        Parameters
        ----------
        **kwargs
            Configuration keyword arguments matching the converter's
            schema fields. ``min_range`` and ``max_range`` are extracted and
            combined into the ``feature_range`` tuple expected by
            scikit-learn; remaining kwargs are forwarded to the underlying
            scikit-learn class.
        """
        self.min_range = kwargs.pop("min_range", 0)
        self.max_range = kwargs.pop("max_range", 1)
        kwargs["feature_range"] = (self.min_range, self.max_range)
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

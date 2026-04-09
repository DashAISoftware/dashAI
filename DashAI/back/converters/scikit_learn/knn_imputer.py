from sklearn.impute import KNNImputer as KNNImputerOperation

from DashAI.back.converters.category.basic_preprocessing import (
    BasicPreprocessingConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    bool_field,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class KNNImputerSchema(BaseSchema):
    """Schema for configuring the KNNImputer converter.

    Wraps ``sklearn.impute.KNNImputer`` and exposes the number of neighbours,
    distance weighting, distance metric, copy behaviour, indicator stacking,
    and empty-feature handling as schema fields validated before being
    forwarded to the underlying scikit-learn estimator.
    """

    n_neighbors: schema_field(
        int_field(ge=1),
        5,
        description=MultilingualString(
            en="The number of nearest neighbors to use for imputation.",
            es="Número de vecinos más cercanos a usar para la imputación.",
        ),
    )  # type: ignore
    weights: schema_field(
        enum_field(["uniform", "distance"]),
        "uniform",
        description=MultilingualString(
            en="The weight function to use for imputation.",
            es="La función de peso a usar para la imputación.",
        ),
    )  # type: ignore
    metric: schema_field(
        enum_field(["nan_euclidean"]),
        "nan_euclidean",
        description=MultilingualString(
            en="The metric to use for imputation.",
            es="La métrica a usar para la imputación.",
        ),
    )  # type: ignore
    add_indicator: schema_field(
        bool_field(),
        False,
        description=MultilingualString(
            en="If True, a MissingIndicator transform will stack onto output.",
            es="Si es True, se apilará un MissingIndicator sobre la salida.",
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


class KNNImputer(BasicPreprocessingConverter, SklearnWrapper, KNNImputerOperation):
    """Fill missing values by averaging over the K nearest complete neighbours.

    For each sample that contains missing entries, the ``n_neighbors`` nearest
    complete samples (those without any missing value in the imputed feature)
    are located using the ``nan_euclidean`` distance, which handles partially
    observed vectors by ignoring the missing dimensions during distance
    computation. The imputed value is then either the uniform mean or the
    distance-weighted mean of those neighbours, depending on the ``weights``
    parameter.

    Unlike ``SimpleImputer``, which computes a single global statistic per
    column, KNN imputation is instance-based and preserves the local
    correlation structure of the data. All output columns are typed as
    ``Float64`` in DashAI.

    Wraps ``sklearn.impute.KNNImputer``.

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.impute.KNNImputer.html
    """

    SCHEMA = KNNImputerSchema
    DESCRIPTION = MultilingualString(
        en=("Imputation for completing missing values using k-Nearest Neighbors."),
        es=(
            "Imputación para completar valores faltantes utilizando "
            "k-Vecinos Más Cercanos."
        ),
    )
    DISPLAY_NAME = MultilingualString(en="KNN Imputer", es="Imputador KNN")
    IMAGE_PREVIEW = "knn_imputer.png"

    metadata = {
        "allowed_dtypes": ["int64", "float64", "float32"],
        "restricted_dtypes": [],
    }

    def __init__(self, **kwargs):
        """Initialize the KNNImputer converter.

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

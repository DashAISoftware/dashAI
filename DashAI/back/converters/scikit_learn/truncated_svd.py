from sklearn.decomposition import TruncatedSVD as TruncatedSVDOperation

from DashAI.back.api.utils import create_random_state
from DashAI.back.converters.category.dimensionality_reduction import (
    DimensionalityReductionConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    enum_field,
    float_field,
    int_field,
    none_type,
    schema_field,
    union_type,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class TruncatedSVDSchema(BaseSchema):
    """Schema for Truncated SVD hyperparameters."""

    n_components: schema_field(
        int_field(gt=0),
        2,
        description=MultilingualString(
            en="Desired dimensionality of output data.",
            es="Dimensionalidad deseada de los datos de salida.",
        ),
    )  # type: ignore
    algorithm: schema_field(
        enum_field(["arpack", "randomized"]),
        "randomized",
        description=MultilingualString(
            en="SVD solver to use.",
            es="Método SVD a utilizar.",
        ),
    )  # type: ignore
    n_iter: schema_field(
        int_field(gt=0),
        5,
        description=MultilingualString(
            en="Number of iterations for randomized SVD solver.",
            es="Número de iteraciones para el método SVD aleatorizado.",
        ),
    )  # type: ignore
    n_oversamples: schema_field(
        int_field(gt=0),
        10,
        description=MultilingualString(
            en="Number of power iterations used in randomized SVD solver.",
            es=(
                "Número de iteraciones de potencia utilizadas en el método "
                "SVD aleatorizado."
            ),
        ),
    )  # type: ignore
    power_iteration_normalizer: schema_field(
        enum_field(["auto", "QR", "LU", "none"]),
        "auto",
        description=MultilingualString(
            en="Method to normalize the eigenvectors.",
            es="Método para normalizar los eigenvectores.",
        ),
    )  # type: ignore
    random_state: schema_field(
        none_type(union_type(int_field(), enum_field(["RandomState"]))),
        None,
        description=MultilingualString(
            en=(
                "Used during randomized svd. Pass an int for reproducible "
                "results across multiple function calls."
            ),
            es=(
                "Usado durante SVD aleatorizado. Pasa un entero para obtener "
                "resultados reproducibles en múltiples ejecuciones."
            ),
        ),
    )  # type: ignore
    tol: schema_field(
        float_field(ge=0),
        0.0,
        description=MultilingualString(
            en="Tolerance for ARPACK.",
            es="Tolerancia para ARPACK.",
        ),
    )  # type: ignore


class TruncatedSVD(
    DimensionalityReductionConverter, SklearnWrapper, TruncatedSVDOperation
):
    """Reduce dimensionality using Truncated Singular Value Decomposition.

    Similar to PCA but works directly on sparse matrices without centering the
    data first. This makes it suitable for TF-IDF or bag-of-words feature matrices
    where centering would destroy sparsity.

    Wraps scikit-learn's ``TruncatedSVD``.
    """

    SCHEMA = TruncatedSVDSchema
    DESCRIPTION = MultilingualString(
        en=(
            "This transformer performs linear dimensionality reduction by means "
            "of truncated singular value decomposition (SVD). Contrary to PCA, "
            "this estimator does not center the data before computing the "
            "singular value decomposition. This means it can work with sparse "
            "matrices efficiently."
        ),
        es=(
            "Este transformador realiza reducción lineal de dimensionalidad por "
            "medio de la descomposición en valores singulares truncada (SVD). "
            "A diferencia de PCA, este estimador no centra los datos antes de "
            "calcular la descomposición, lo que permite trabajar eficientemente "
            "con matrices dispersas."
        ),
    )
    SHORT_DESCRIPTION = MultilingualString(
        en="Dimensionality reduction using truncated SVD.",
        es="Reducción de dimensionalidad utilizando SVD truncado.",
    )
    DISPLAY_NAME = MultilingualString(en="Truncated SVD", es="SVD Truncado")
    IMAGE_PREVIEW = "truncated_svd.png"
    metadata = {}

    def __init__(self, **kwargs):
        """Initialize the TruncatedSVD converter.

        Parameters
        ----------
        **kwargs
            Configuration keyword arguments matching the converter's
            schema fields. Forwarded to the underlying scikit-learn class.
        """
        self.random_state = kwargs.pop("random_state", None)
        if self.random_state == "RandomState":
            self.random_state = create_random_state()
        kwargs["random_state"] = self.random_state

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

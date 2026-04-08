from sklearn.kernel_approximation import Nystroem as NystroemOperation

from DashAI.back.api.utils import create_random_state, parse_string_to_dict
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
    string_field,
    union_type,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class NystroemSchema(BaseSchema):
    """Configuration schema for the Nystroem converter.

    Defines and validates the hyperparameters passed to
    ``sklearn.kernel_approximation.Nystroem``.
    """

    kernel: schema_field(
        none_type(string_field()),
        "rbf",
        description=MultilingualString(
            en="The kernel to use for the approximation.",
            es="El kernel a usar para la aproximación.",
        ),
    )  # type: ignore
    gamma: schema_field(
        none_type(float_field(gt=0)),
        None,
        description=MultilingualString(
            en=(
                "Gamma parameter for RBF, laplacian, polynomial, exp chi2 "
                "and sigmoid kernels."
            ),
            es=(
                "Parámetro gamma para los kernels RBF, laplaciano, polinomial, "
                "chi2 exponencial y sigmoide."
            ),
        ),
    )  # type: ignore
    coef0: schema_field(
        none_type(float_field()),
        None,
        description=MultilingualString(
            en="The coef0 parameter for polynomial and sigmoid kernels.",
            es="Parámetro coef0 para los kernels polinomial y sigmoide.",
        ),
    )  # type: ignore
    degree: schema_field(
        none_type(float_field(ge=1)),
        None,
        description=MultilingualString(
            en="The degree of the polynomial kernel.",
            es="El grado del kernel polinomial.",
        ),
    )  # type: ignore
    kernel_params: schema_field(
        none_type(string_field()),
        None,
        description=MultilingualString(
            en="Additional parameters (kwargs) for the kernel function.",
            es="Parámetros adicionales (kwargs) para la función kernel.",
        ),
    )  # type: ignore
    n_components: schema_field(
        int_field(ge=1),
        2,
        description=MultilingualString(
            en="The number of features to construct.",
            es="El número de características a construir.",
        ),
    )  # type: ignore
    random_state: schema_field(
        none_type(union_type(int_field(), enum_field(["RandomState"]))),
        None,
        description=MultilingualString(
            en=(
                "Seed of the pseudo random number generator to use when "
                "shuffling the data."
            ),
            es=("Semilla del generador pseudoaleatorio usado al mezclar los datos."),
        ),
    )  # type: ignore
    n_jobs: schema_field(
        none_type(int_field()),
        None,
        description=MultilingualString(
            en="Number of parallel jobs to run.",
            es="Número de trabajos paralelos a ejecutar.",
        ),
    )  # type: ignore


class Nystroem(DimensionalityReductionConverter, SklearnWrapper, NystroemOperation):
    """Approximate a kernel feature map using the Nystroem method.

    The Nystroem method constructs an explicit low-dimensional feature map
    `phi(x)` that approximates an arbitrary kernel `k(x, x') = <phi(x), phi(x')>`,
    enabling the use of kernel methods with linear-complexity training algorithms.
    It works by sub-sampling ``n_components`` landmark points from the training
    data, evaluating the kernel between all training samples and these landmarks,
    and then normalising the resulting matrix using the Cholesky factor of the
    kernel matrix evaluated on the landmarks alone.

    The approximation quality improves with ``n_components``: as
    n_components → n_samples the approximation becomes exact. In practice a
    small number of landmarks (e.g. a few hundred) is often sufficient.
    Combining Nystroem with a linear model (e.g. SGDClassifier) provides a
    scalable alternative to kernel SVMs for large datasets.

    Key properties:

    - Supports any kernel available in scikit-learn (RBF, polynomial, sigmoid,
      chi2, linear, etc.) as well as callable kernels via ``kernel_params``.
    - Unsupervised: no labels required at fit time.
    - Output dimensionality equals ``n_components``, which is independent of
      the number of input features.
    - The ``gamma``, ``coef0``, and ``degree`` parameters are passed directly
      to the chosen kernel function.

    Wraps scikit-learn's ``Nystroem``.

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.kernel_approximation.Nystroem.html
    - [2] Williams, C. K. I. & Seeger, M. (2001). "Using the Nyström method to
        speed up kernel machines." Advances in Neural Information Processing
        Systems 13 (NIPS 2000), 682-688.
    """

    SCHEMA = NystroemSchema
    DESCRIPTION = MultilingualString(
        en=(
            "Approximate a kernel map using a subset of the training data. "
            "Constructs an approximate feature map for an arbitrary kernel "
            "using a subset of the data as basis."
        ),
        es=(
            "Aproxima un mapa de kernel usando un subconjunto de los datos de "
            "entrenamiento. Construye un mapa de características aproximado para "
            "un kernel arbitrario usando un subconjunto de datos como base."
        ),
    )
    DISPLAY_NAME = MultilingualString(
        en="Nystroem Approximation", es="Aproximación Nystroem"
    )
    IMAGE_PREVIEW = "nystroem.png"

    metadata = {
        "allowed_dtypes": ["int64", "float64", "float32"],
        "restricted_dtypes": [],
    }

    def __init__(self, **kwargs):
        """Initialize the Nystroem converter.

        Parameters
        ----------
        **kwargs
            Configuration keyword arguments matching the converter's
            schema fields. Forwarded to the underlying scikit-learn class.
        """
        self.kernel_params = kwargs.pop("kernel_params", None)
        if self.kernel_params is not None:
            self.kernel_params = parse_string_to_dict(self.kernel_params)
        kwargs["kernel_params"] = self.kernel_params

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

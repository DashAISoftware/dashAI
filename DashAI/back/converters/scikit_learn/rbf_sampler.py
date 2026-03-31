from sklearn.kernel_approximation import RBFSampler as RBFSamplerOperation

from DashAI.back.api.utils import create_random_state
from DashAI.back.converters.category.polynomial_kernel import PolynomialKernelConverter
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


class RBFSamplerSchema(BaseSchema):
    """Schema for configuring the RBFSampler converter.

    Wraps ``sklearn.kernel_approximation.RBFSampler`` and exposes the RBF
    bandwidth parameter ``gamma``, the number of random Fourier features
    ``n_components``, and the random seed as schema fields validated before
    being forwarded to the underlying scikit-learn estimator.
    """

    gamma: schema_field(
        union_type(enum_field(["scale"]), float_field(gt=0)),
        "scale",
        description=MultilingualString(
            en="Parameter of the RBF kernel.",
            es="Parámetro del kernel RBF.",
        ),
    )  # type: ignore
    n_components: schema_field(
        int_field(ge=1),
        100,
        description=MultilingualString(
            en="The number of features to construct.",
            es="El número de características a construir.",
        ),
    )  # type: ignore
    random_state: schema_field(
        none_type(union_type(int_field(), enum_field(["RandomState"]))),
        0,
        description=MultilingualString(
            en=(
                "Pseudo-random number generator to control the generation of the "
                "random weights and random offset when fitting the training data. "
                "Pass an int for reproducible output across multiple function calls."
            ),
            es=(
                "Generador pseudoaleatorio para controlar pesos y desplazamientos "
                "aleatorios al ajustar los datos. Pasa un entero para obtener "
                "resultados reproducibles."
            ),
        ),
    )  # type: ignore


class RBFSampler(PolynomialKernelConverter, SklearnWrapper, RBFSamplerOperation):
    """Approximate the RBF (Gaussian) kernel feature map via random Fourier features.

    The Radial Basis Function (RBF) kernel is one of the most widely used
    kernels in kernel-based learning methods such as SVMs. Computing it
    directly scales quadratically with the number of training samples.

    This converter implements the random Fourier feature approximation of
    Rahimi & Recht (2007) [2]: random weights are sampled from the Fourier
    transform of the RBF kernel (a Gaussian distribution), and the input
    features are mapped to ``n_components`` sinusoidal features. A linear
    model trained on the resulting representation approximates a kernel
    machine at a fraction of the cost.

    The ``gamma`` parameter controls the bandwidth of the RBF kernel:
    ``K(x, y) = exp(-gamma * ||x - y||²)``. When set to ``"scale"``, it is
    computed from the training data as ``1 / (n_features * X.var())``.

    Output columns are typed as ``Float64`` in DashAI.

    Wraps ``sklearn.kernel_approximation.RBFSampler``.

    References
    ----------
    [1] https://scikit-learn.org/stable/modules/generated/sklearn.kernel_approximation.RBFSampler.html
    [2] Rahimi, A. & Recht, B. (2007). Random Features for Large-Scale Kernel
        Machines. Advances in Neural Information Processing Systems, 20.
    """

    SCHEMA = RBFSamplerSchema
    DESCRIPTION = MultilingualString(
        en=(
            "Approximates the feature map of an RBF kernel by Monte Carlo "
            "approximation of its Fourier transform."
        ),
        es=(
            "Aproxima el mapa de características de un kernel RBF mediante "
            "la aproximación de Monte Carlo de su transformada de Fourier."
        ),
    )
    DISPLAY_NAME = MultilingualString(en="RBF Sampler", es="Muestreador RBF")
    IMAGE_PREVIEW = "rbf_sampler.png"

    def __init__(self, **kwargs):
        """Initialise the RBF sampler, resolving the ``"RandomState"`` sentinel.

        If ``random_state`` is the string ``"RandomState"``, a fresh
        ``numpy.random.RandomState`` instance is created in its place before
        being forwarded to sklearn's ``RBFSampler``.

        Parameters
        ----------
        **kwargs : dict
            random_state : int, ``"RandomState"``, or None, optional
                Seed for reproducibility.  The special string ``"RandomState"``
                generates a fresh random state. Default ``None``.
            Additional keys are forwarded to
            ``sklearn.kernel_approximation.RBFSampler``.
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
            Not used; all output columns share the same type. Defaults to None.

        Returns
        -------
        DashAIDataType
            A Float type backed by ``pyarrow.float64()``.
        """
        import pyarrow as pa

        return Float(arrow_type=pa.float64())

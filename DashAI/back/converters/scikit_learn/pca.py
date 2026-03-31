from sklearn.decomposition import PCA as PCAOPERATION

from DashAI.back.api.utils import create_random_state
from DashAI.back.converters.category.dimensionality_reduction import (
    DimensionalityReductionConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    bool_field,
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


class PCASchema(BaseSchema):
    """Schema for PCA hyperparameters."""

    n_components: schema_field(
        none_type(
            union_type(
                union_type(int_field(ge=1), float_field(gt=0.0, lt=1.0)),
                enum_field(["mle"]),
            ),
        ),
        2,
        description=MultilingualString(
            en="Number of components to keep. If None, all components are kept.",
            es=(
                "Número de componentes a conservar. Si es None, se conservan "
                "todas las componentes."
            ),
        ),
    )  # type: ignore
    use_copy: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en=(
                "If False, data passed to fit are overwritten. Use "
                "fit_transform(X) instead of fit(X).transform(X)."
            ),
            es=(
                "Si es False, los datos pasados a fit se sobrescriben. Usa "
                "fit_transform(X) en lugar de fit(X).transform(X)."
            ),
        ),
        alias=MultilingualString(en="copy", es="copiar"),
    )  # type: ignore
    whiten: schema_field(
        bool_field(),
        False,
        description=MultilingualString(
            en=(
                "When True the components_ are scaled to ensure uncorrelated "
                "outputs with unit variances. May improve downstream estimators."
            ),
            es=(
                "Cuando es True las componentes se escalan para asegurar salidas "
                "no correlacionadas con varianzas unitarias. Puede mejorar "
                "estimadores posteriores."
            ),
        ),
    )  # type: ignore
    svd_solver: schema_field(
        enum_field(["auto", "full", "covariance_eigh", "arpack", "randomized"]),
        "auto",
        description=MultilingualString(
            en=(
                "Solver to use for eigendecomposition. 'auto' elige el más "
                "apropiado según los datos."
            ),
            es=(
                "Método para la descomposición propia. 'auto' elige el más "
                "apropiado según los datos."
            ),
        ),
    )  # type: ignore
    tol: schema_field(
        float_field(ge=0.0),
        0.0,
        description=MultilingualString(
            en="Tolerance for singular values when svd_solver == 'arpack'.",
            es="Tolerancia para valores singulares cuando svd_solver == 'arpack'.",
        ),
    )  # type: ignore
    iterated_power: schema_field(
        union_type(int_field(ge=1), enum_field(["auto"])),
        "auto",
        description=MultilingualString(
            en=(
                "Number of iterations for the power method when "
                "svd_solver == 'randomized'."
            ),
            es=(
                "Número de iteraciones para el método de potencia cuando "
                "svd_solver == 'randomized'."
            ),
        ),
    )  # type: ignore
    n_oversamples: schema_field(
        int_field(ge=1),
        10,
        description=MultilingualString(
            en="Number of power iterations used when svd_solver == 'randomized'.",
            es="Número de iteraciones de potencia cuando svd_solver == 'randomized'.",
        ),
    )  # type: ignore
    power_iteration_normalizer: schema_field(
        none_type(enum_field(["auto", "QR", "LU"])),
        "auto",
        description=MultilingualString(
            en=(
                "How the power iteration normalizer should be computed: 'auto', "
                "QR o LU. No usado por ARPACK."
            ),
            es=(
                "Cómo se calcula el normalizador de iteración de potencia: "
                "'auto', QR o LU. No se usa con ARPACK."
            ),
        ),
    )  # type: ignore
    random_state: schema_field(
        none_type(union_type(int_field(), enum_field(["RandomState"]))),
        None,
        description=MultilingualString(
            en=(
                "Used when 'arpack' or 'randomized' solvers are used. Pass an int "
                "for reproducible results."
            ),
            es=(
                "Usado con los métodos 'arpack' o 'randomized'. Pasa un entero "
                "para resultados reproducibles."
            ),
        ),
    )  # type: ignore


class PCA(DimensionalityReductionConverter, SklearnWrapper, PCAOPERATION):
    """Reduce dimensionality using Principal Component Analysis.

    Projects the input feature space into a lower-dimensional subspace that
    captures the directions of maximum variance. Each output component is a
    linear combination of the original features, ordered by explained variance.

    Wraps scikit-learn's ``PCA``.
    """

    SCHEMA = PCASchema
    DESCRIPTION = MultilingualString(
        en=(
            "Principal Component Analysis (PCA) is a dimensionality reduction "
            "technique used to simplify complex datasets while retaining as much "
            "variability as possible."
        ),
        es=(
            "El Análisis de Componentes Principales (PCA) es una técnica de "
            "reducción de dimensionalidad usada para simplificar conjuntos de "
            "datos complejos conservando tanta variabilidad como sea posible."
        ),
    )
    SHORT_DESCRIPTION = MultilingualString(
        en="Dimensionality reduction using PCA.",
        es="Reducción de dimensionalidad usando PCA.",
    )
    DISPLAY_NAME = MultilingualString(
        en="Principal Component Analysis (PCA)",
        es="Análisis de Componentes Principales (PCA)",
    )
    IMAGE_PREVIEW = "pca.png"
    metadata = {}

    def __init__(self, **kwargs):
        """Initialize the PCA converter.

        Handles the ``"RandomState"`` sentinel for ``random_state`` by converting
        it to a new ``numpy.RandomState`` instance at initialization time.

        Parameters
        ----------
        **kwargs
            Configuration keyword arguments matching ``PCASchema`` fields.
            If ``random_state`` is ``"RandomState"``, a fresh ``numpy.RandomState``
            instance is created automatically.
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

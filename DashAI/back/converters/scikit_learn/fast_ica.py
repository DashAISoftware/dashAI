import pyarrow as pa
from sklearn.decomposition import FastICA as FastICAOperation

from DashAI.back.api.utils import (
    create_random_state,
    parse_string_to_dict,
    parse_string_to_list,
)
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
    string_field,
    union_type,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class FastICASchema(BaseSchema):
    n_components: schema_field(
        none_type(int_field(ge=1)),
        None,
        description=MultilingualString(
            en="Number of components to extract.",
            es="Número de componentes a extraer.",
        ),
    )  # type: ignore
    algorithm: schema_field(
        enum_field(["parallel", "deflation"]),
        "parallel",
        description=MultilingualString(
            en="Apply parallel or deflational algorithm for FastICA.",
            es="Aplica el algoritmo paralelo o deflacional para FastICA.",
        ),
    )  # type: ignore
    # Deprecated since version 1.1
    whiten: schema_field(
        none_type(
            union_type(
                enum_field(["arbitrary-variance", "unit-variance"]), bool_field()
            )
        ),
        "unit-variance",
        description=MultilingualString(
            en="If True, the data is whitened.",
            es="Si es True, los datos se blanquean.",
        ),
    )  # type: ignore
    fun: schema_field(
        enum_field(["logcosh", "exp", "cube"]),
        "logcosh",
        description=MultilingualString(
            en=(
                "Functional form of the G function used in the approximation "
                "to neg-entropy."
            ),
            es=(
                "Forma funcional de la función G utilizada en la aproximación "
                "a la neg-entropía."
            ),
        ),
    )  # type: ignore
    fun_args: schema_field(
        none_type(string_field()),
        None,
        description=MultilingualString(
            en="Arguments to the G function.",
            es="Argumentos de la función G.",
        ),
    )  # type: ignore
    max_iter: schema_field(
        int_field(ge=1),
        200,
        description=MultilingualString(
            en="Maximum number of iterations to perform.",
            es="Número máximo de iteraciones a realizar.",
        ),
    )  # type: ignore
    tol: schema_field(
        float_field(ge=0.0),
        1e-04,
        description=MultilingualString(
            en="Tolerance on update at each iteration.",
            es="Tolerancia en la actualización en cada iteración.",
        ),
    )  # type: ignore
    w_init: schema_field(
        none_type(string_field()),
        None,
        description=MultilingualString(
            en="Initial guess for the unmixing matrix.",
            es="Estimación inicial de la matriz de separación.",
        ),
    )  # type: ignore
    whiten_solver: schema_field(
        enum_field(["eigh", "svd"]),
        "svd",
        description=MultilingualString(
            en="The solver to use for whitening.",
            es="Método a utilizar para el blanqueo.",
        ),
    )  # type: ignore
    random_state: schema_field(
        none_type(union_type(int_field(), enum_field(["RandomState"]))),
        None,
        description=MultilingualString(
            en=(
                "Used to initialize w_init when not specified, with a normal "
                "distribution. Pass an int for reproducible results."
            ),
            es=(
                "Usado para inicializar w_init cuando no se especifica, con "
                "una distribución normal. Pasa un entero para resultados "
                "reproducibles."
            ),
        ),
    )  # type: ignore


class FastICA(DimensionalityReductionConverter, SklearnWrapper, FastICAOperation):
    """Scikit-learn's FastICA wrapper for DashAI."""

    SCHEMA = FastICASchema
    DESCRIPTION = MultilingualString(
        en="FastICA: a fast algorithm for Independent Component Analysis.",
        es=(
            "FastICA: un algoritmo rápido para "
            "el Análisis de Componentes Independientes."
        ),
    )
    DISPLAY_NAME = MultilingualString(en="Fast ICA", es="Fast ICA")
    IMAGE_PREVIEW = "fast_ica.png"

    def __init__(self, **kwargs):
        self.fun_args = kwargs.pop("fun_args", None)
        if self.fun_args is not None:
            self.fun_args = parse_string_to_dict(self.fun_args)
        kwargs["fun_args"] = self.fun_args

        self.w_init = kwargs.pop("w_init", None)
        if self.w_init is not None:
            self.w_init = [parse_string_to_list(self.w_init)]
        kwargs["w_init"] = self.w_init

        self.random_state = kwargs.pop("random_state", None)
        if self.random_state == "RandomState":
            self.random_state = create_random_state()
        kwargs["random_state"] = self.random_state

        super().__init__(**kwargs)

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for transformed data."""
        return Float(arrow_type=pa.float64())

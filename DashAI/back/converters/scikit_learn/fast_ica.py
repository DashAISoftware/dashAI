from sklearn.decomposition import FastICA as FastICAOperation

from DashAI.back.api.utils import (
    create_random_state,
    parse_string_to_dict,
    parse_string_to_list,
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


class FastICASchema(BaseSchema):
    n_components: schema_field(
        none_type(int_field(ge=1)),
        None,
        "Number of components to extract.",
    )  # type: ignore
    algorithm: schema_field(
        enum_field(["parallel", "deflation"]),
        "parallel",
        "Apply parallel or deflational algorithm for FastICA.",
    )  # type: ignore
    # Deprecated since version 1.1
    whiten: schema_field(
        none_type(
            union_type(
                enum_field(["arbitrary-variance", "unit-variance"]), bool_field()
            )
        ),
        "unit-variance",
        "If True, the data is whitened.",
    )  # type: ignore
    fun: schema_field(
        enum_field(
            ["logcosh", "exp", "cube"]
        ),  # {‘logcosh’, ‘exp’, ‘cube’} or callable
        "logcosh",
        (
            "The functional form of the G function used in "
            "the approximation to neg-entropy."
        ),
    )  # type: ignore
    fun_args: schema_field(
        none_type(string_field()),  # {"logcosh": 1.0, "exp": 1.0, "cube": 1.0},
        None,
        "Arguments to the G function.",
    )  # type: ignore
    max_iter: schema_field(
        int_field(ge=1),
        200,
        "Maximum number of iterations to perform.",
    )  # type: ignore
    tol: schema_field(
        float_field(ge=0.0),
        1e-04,
        "Tolerance on update at each iteration.",
    )  # type: ignore
    w_init: schema_field(
        none_type(string_field()),  # array-like of shape (n_components, n_components)
        None,
        "Initial guess for the unmixing matrix.",
    )  # type: ignore
    whiten_solver: schema_field(
        enum_field(["eigh", "svd"]),
        "svd",
        "The solver to use for whitening.",
    )  # type: ignore
    random_state: schema_field(
        none_type(
            union_type(int_field(), enum_field(["RandomState"]))
        ),  # int, RandomState instance or None
        None,
        "Used to initialize w_init when not specified, with a normal distribution. "
        "Pass an int, for reproducible results across multiple function calls.",
    )  # type: ignore


class FastICA(SklearnWrapper, FastICAOperation):
    """Scikit-learn's FastICA wrapper for DashAI."""

    SCHEMA = FastICASchema
    DESCRIPTION = "FastICA: a fast algorithm for Independent Component Analysis."

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

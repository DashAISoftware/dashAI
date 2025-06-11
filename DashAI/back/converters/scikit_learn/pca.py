from sklearn.decomposition import PCA as PCAOPERATION

from DashAI.back.api.utils import create_random_state
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


class PCASchema(BaseSchema):
    n_components: schema_field(
        none_type(
            union_type(
                union_type(int_field(ge=1), float_field(gt=0.0, lt=1.0)),
                enum_field(["mle"]),
            ),
        ),
        2,
        "Number of components to keep. If None, all components are kept.",
    )  # type: ignore
    use_copy: schema_field(
        bool_field(),
        True,
        (
            "If False, data passed to fit are overwritten and running "
            "fit(X).transform(X) will not yield the expected results, "
            "use fit_transform(X) instead."
        ),
        alias="copy",
    )  # type: ignore
    whiten: schema_field(
        bool_field(),
        False,
        (
            "When True (False by default) the components_ vectors are multiplied "
            "by the square root of n_samples and then divided by the singular values "
            "to ensure uncorrelated outputs with unit component-wise variances. "
            "Whitening will remove some information from the transformed signal "
            "(the relative variance scales of the components) but can sometime "
            "improve the predictive accuracy of the downstream estimators by "
            "making their data respect some hard-wired assumptions."
        ),
    )  # type: ignore
    svd_solver: schema_field(
        enum_field(["auto", "full", "covariance_eigh", "arpack", "randomized"]),
        "auto",
        (
            "The solver to use for the eigendecomposition. If 'auto', it will "
            "choose the most appropriate solver based on the type of data passed."
        ),
    )  # type: ignore
    tol: schema_field(
        float_field(ge=0.0),
        0.0,
        ("Tolerance for singular values computed by " "svd_solver == 'arpack'."),
    )  # type: ignore
    iterated_power: schema_field(
        union_type(int_field(ge=1), enum_field(["auto"])),
        "auto",
        (
            "Number of iterations for the power method computed by "
            "svd_solver == 'randomized'."
        ),
    )  # type: ignore
    n_oversamples: schema_field(
        int_field(ge=1),
        10,
        "Number of power iterations used when svd_solver == 'randomized'.",
    )  # type: ignore
    power_iteration_normalizer: schema_field(
        none_type(enum_field(["auto", "QR", "LU"])),
        "auto",
        (
            "Whether the power iteration normalizer should be computed with QR "
            "(the 'auto' option), "
            "LU decomposition ('LU') or left untouched ('QR'). Not used by ARPACK."
        ),
    )  # type: ignore
    random_state: schema_field(
        none_type(
            union_type(int_field(), enum_field(["RandomState"]))
        ),  # int, RandomState instance or None
        None,
        (
            "Used when the ‘arpack’ or ‘randomized’ solvers are used. "
            "Pass an int for reproducible results across multiple function calls."
        ),
    )  # type: ignore


class PCA(SklearnWrapper, PCAOPERATION):
    """Scikit-learn's PCA wrapper for DashAI."""

    SCHEMA = PCASchema
    DESCRIPTION = "Principal component analysis (PCA)."

    def __init__(self, **kwargs):
        self.random_state = kwargs.pop("random_state", None)
        if self.random_state == "RandomState":
            self.random_state = create_random_state()
        kwargs["random_state"] = self.random_state

        super().__init__(**kwargs)

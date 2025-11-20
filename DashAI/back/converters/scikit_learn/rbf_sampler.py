import pyarrow as pa
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
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class RBFSamplerSchema(BaseSchema):
    gamma: schema_field(
        union_type(enum_field(["scale"]), float_field(gt=0)),
        "scale",
        "Parameter of the RBF kernel.",
    )  # type: ignore
    n_components: schema_field(
        int_field(ge=1),
        100,
        "The number of features to construct.",
    )  # type: ignore
    random_state: schema_field(
        none_type(
            union_type(int_field(), enum_field(["RandomState"]))
        ),  # int, RandomState instance or None
        0,
        (
            "Pseudo-random number generator to control the generation of the "
            "random weights and random offset when fitting the training data. "
            "Pass an int for reproducible output across multiple function calls."
        ),
    )  # type: ignore


class RBFSampler(PolynomialKernelConverter, SklearnWrapper, RBFSamplerOperation):
    """Scikit-learn's RBFSampler wrapper for DashAI."""

    SCHEMA = RBFSamplerSchema
    DESCRIPTION = (
        "Approximates the feature map of an RBF kernel by Monte Carlo "
        "approximation of its Fourier transform."
    )
    CATEGORY = "Polynomial & Kernel Methods"
    DISPLAY_NAME = "RBF Sampler"
    IMAGE_PREVIEW = "rbf_sampler.png"

    def __init__(self, **kwargs):
        self.random_state = kwargs.pop("random_state", None)
        if self.random_state == "RandomState":
            self.random_state = create_random_state()
        kwargs["random_state"] = self.random_state

        super().__init__(**kwargs)

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for transformed data."""
        return Float(arrow_type=pa.float64())

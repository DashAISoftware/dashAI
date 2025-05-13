from sklearn.kernel_approximation import (
    AdditiveChi2Sampler as AdditiveChi2SamplerOperation,
)

from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    float_field,
    int_field,
    none_type,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema


class AdditiveChi2SamplerSchema(BaseSchema):
    sample_steps: schema_field(
        int_field(ge=1),
        2,
        "The number of sample steps (shuffling) to perform.",
    )  # type: ignore
    sample_interval: schema_field(
        none_type(float_field(ge=1.0)),
        None,
        "The number of samples to generate between each original sample.",
    )  # type: ignore


class AdditiveChi2Sampler(SklearnWrapper, AdditiveChi2SamplerOperation):
    """Scikit-learn's AdditiveChi2Sampler wrapper for DashAI."""

    SCHEMA = AdditiveChi2SamplerSchema
    DESCRIPTION = (
        "Uses sampling the fourier transform of the kernel characteristic "
        "at regular intervals."
    )

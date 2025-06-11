from imblearn.under_sampling import RandomUnderSampler

from DashAI.back.converters.imbalanced_learn_wrapper import ImbalancedLearnWrapper
from DashAI.back.core.schema_fields import (
    enum_field,
    float_field,
    int_field,
    none_type,
    schema_field,
    union_type,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema


class RUSchema(BaseSchema):
    sampling_strategy: schema_field(
        union_type(float_field(gt=0.0, le=1.0), enum_field(["auto"])),
        "auto",
        "Sampling strategy (float or 'auto') to reduce majority class.",
    )  # type: ignore
    random_state: schema_field(
        none_type(int_field()),
        None,
        "Seed for reproducibility.",
    )  # type: ignore


class RandomUnderSamplerConverter(ImbalancedLearnWrapper, RandomUnderSampler):
    SCHEMA = RUSchema
    DESCRIPTION = (
        "Randomly remove samples from the majority class to balance the dataset."
    )

    def __init___(self, **kwargs):
        super(RandomUnderSamplerConverter, self).__init__(**kwargs)

from imblearn.over_sampling import SMOTE

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


class SMOTESchema(BaseSchema):
    sampling_strategy: schema_field(
        union_type(float_field(gt=0.0, le=1.0), enum_field(["auto"])),
        "auto",
        "Sampling strategy (float or 'auto') to determine minority class size.",
    )  # type: ignore
    random_state: schema_field(
        none_type(int_field()),
        None,
        "Seed for reproducibility.",
    )  # type: ignore
    k_neighbors: schema_field(
        int_field(ge=1),
        5,
        "Number of neighbors to use for generating synthetic samples.",
    )  # type: ignore


class SMOTEConverter(ImbalancedLearnWrapper, SMOTE):
    SCHEMA = SMOTESchema
    DESCRIPTION = "SMOTE: Synthetic Minority Over-sampling Technique."

    def __init___(self, **kwargs):
        super(SMOTEConverter, self).__init__(**kwargs)

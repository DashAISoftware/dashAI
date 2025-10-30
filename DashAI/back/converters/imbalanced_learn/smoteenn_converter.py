from imblearn.combine import SMOTEENN
from imblearn.over_sampling import SMOTE

from DashAI.back.converters.category.sampling import SamplingConverter
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


class SMOTEENNSchema(BaseSchema):
    sampling_strategy: schema_field(
        union_type(float_field(gt=0.0, le=1.0), enum_field(["auto"])),
        "auto",
        "Sampling strategy to apply SMOTE and clean the dataset.",
    )  # type: ignore
    random_state: schema_field(
        none_type(int_field()),
        None,
        "Seed used for reproducibility.",
    )  # type: ignore
    k_neighbors: schema_field(
        int_field(ge=1),
        5,
        "Number of neighbors used by SMOTE.",
    )  # type: ignore


class SMOTEENNConverter(SamplingConverter, ImbalancedLearnWrapper, SMOTEENN):
    SCHEMA = SMOTEENNSchema
    DESCRIPTION = "SMOTEENN: SMOTE with noise reduction via Edited Nearest Neighbors."
    DISPLAY_NAME = "SMOTE-ENN (Hybrid Sampling)"
    IMAGE_PREVIEW = "smoteenn.png"
    CATEGORY = "Resampling & Class Balancing"

    def __init__(self, **kwargs):
        self.smote = SMOTE(
            sampling_strategy=kwargs.get("sampling_strategy", "auto"),
            random_state=kwargs.get("random_state"),
            k_neighbors=kwargs.get("k_neighbors"),
        )

        super().__init__(
            smote=self.smote,
            sampling_strategy=kwargs.get("sampling_strategy", "auto"),
            random_state=kwargs.get("random_state"),
        )

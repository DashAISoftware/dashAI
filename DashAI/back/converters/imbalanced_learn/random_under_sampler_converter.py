from imblearn.under_sampling import RandomUnderSampler

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
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType


class RUSchema(BaseSchema):
    sampling_strategy: schema_field(
        union_type(float_field(gt=0.0, le=1.0), enum_field(["auto"])),
        "auto",
        description=MultilingualString(
            en="Sampling strategy (float or 'auto') to reduce majority class.",
            es=(
                "Estrategia de muestreo (float o 'auto') para reducir la clase "
                "mayoritaria."
            ),
        ),
    )  # type: ignore
    random_state: schema_field(
        none_type(int_field()),
        None,
        description=MultilingualString(
            en="Seed for reproducibility.",
            es="Semilla para reproducibilidad.",
        ),
    )  # type: ignore


class RandomUnderSamplerConverter(
    SamplingConverter, ImbalancedLearnWrapper, RandomUnderSampler
):
    SCHEMA = RUSchema
    DESCRIPTION = MultilingualString(
        en="Randomly remove samples from the majority class to balance the dataset.",
        es="Elimina aleatoriamente muestras de la clase mayoritaria para balancear.",
    )
    CATEGORY = MultilingualString(
        en="Resampling & Class Balancing", es="Remuestreo y Balanceo de Clases"
    )
    DISPLAY_NAME = MultilingualString(
        en="Random Under-Sampler", es="Submuestreador Aleatorio"
    )
    IMAGE_PREVIEW = "random_under_sampler.png"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """
        RandomUnderSampler preserves input column types.
        Type handling is done in ImbalancedLearnWrapper.transform().
        """
        raise NotImplementedError(
            "RandomUnderSampler preserves input types. "
            "Types are handled in the transform method."
        )

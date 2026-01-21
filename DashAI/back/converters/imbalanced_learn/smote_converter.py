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
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType


class SMOTESchema(BaseSchema):
    sampling_strategy: schema_field(
        union_type(float_field(gt=0.0, le=1.0), enum_field(["auto"])),
        "auto",
        description=MultilingualString(
            en=(
                "Sampling strategy (float or 'auto') to determine minority "
                "class size."
            ),
            es=(
                "Estrategia de muestreo (float o 'auto') para determinar el "
                "tamaño de la clase minoritaria."
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
    k_neighbors: schema_field(
        int_field(ge=1),
        5,
        description=MultilingualString(
            en="Number of neighbors to use for generating synthetic samples.",
            es="Número de vecinos para generar muestras sintéticas.",
        ),
    )  # type: ignore


class SMOTEConverter(SamplingConverter, ImbalancedLearnWrapper, SMOTE):
    SCHEMA = SMOTESchema
    DESCRIPTION = MultilingualString(
        en="SMOTE: Synthetic Minority Over-sampling Technique.",
        es="SMOTE: Técnica de Sobre-muestreo de la Minoría Sintética.",
    )
    CATEGORY = MultilingualString(
        en="Resampling & Class Balancing", es="Remuestreo y Balanceo de Clases"
    )
    DISPLAY_NAME = MultilingualString(
        en="SMOTE (Oversampling)", es="SMOTE (Sobre-muestreo)"
    )
    IMAGE_PREVIEW = "smote.png"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """
        SMOTE preserves input column types.
        Type handling is done in ImbalancedLearnWrapper.transform().
        """
        raise NotImplementedError(
            "SMOTE preserves input types. Types are handled in the transform method."
        )

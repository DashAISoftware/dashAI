from imblearn.combine import SMOTEENN

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


class SMOTEENNSchema(BaseSchema):
    sampling_strategy: schema_field(
        union_type(float_field(gt=0.0, le=1.0), enum_field(["auto"])),
        "auto",
        description=MultilingualString(
            en="Sampling strategy to apply SMOTE and clean the dataset.",
            es=(
                "Estrategia de muestreo para aplicar SMOTE y limpiar el "
                "conjunto de datos."
            ),
        ),
    )  # type: ignore
    random_state: schema_field(
        none_type(int_field()),
        None,
        description=MultilingualString(
            en="Seed used for reproducibility.",
            es="Semilla usada para reproducibilidad.",
        ),
    )  # type: ignore
    k_neighbors: schema_field(
        int_field(ge=1),
        5,
        description=MultilingualString(
            en="Number of neighbors used by SMOTE.",
            es="Número de vecinos utilizados por SMOTE.",
        ),
    )  # type: ignore


class SMOTEENNConverter(SamplingConverter, ImbalancedLearnWrapper, SMOTEENN):
    SCHEMA = SMOTEENNSchema
    DESCRIPTION = MultilingualString(
        en=("SMOTEENN: SMOTE with noise reduction via Edited Nearest Neighbors."),
        es=(
            "SMOTEENN: SMOTE con reducción de ruido mediante Vecinos Más "
            "Cercanos Editados."
        ),
    )
    DISPLAY_NAME = MultilingualString(
        en="SMOTE-ENN (Hybrid Sampling)", es="SMOTE-ENN (Muestreo Híbrido)"
    )
    IMAGE_PREVIEW = "smoteenn.png"

    def __init__(self, **kwargs):
        from imblearn.over_sampling import SMOTE

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

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """
        SMOTEENN preserves input column types.
        Type handling is done in ImbalancedLearnWrapper.transform().
        """
        raise NotImplementedError(
            "SMOTEENN preserves input types. Types are handled in the transform method."
        )

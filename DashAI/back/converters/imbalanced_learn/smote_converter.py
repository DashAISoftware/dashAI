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
    """Schema for SMOTEConverter hyperparameters."""

    sampling_strategy: schema_field(
        union_type(float_field(gt=0.0, le=1.0), enum_field(["auto"])),
        "auto",
        description=MultilingualString(
            en=(
                "Sampling strategy (float or 'auto') to determine minority class size."
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
    """Balances class distribution by generating synthetic minority-class samples.

    Creates new samples by interpolating between existing minority-class examples
    and their k-nearest neighbours. Wraps imbalanced-learn's ``SMOTE``.
    """

    SCHEMA = SMOTESchema
    DESCRIPTION = MultilingualString(
        en="SMOTE: Synthetic Minority Over-sampling Technique.",
        es="SMOTE: Técnica de Sobre-muestreo de la Minoría Sintética.",
    )
    DISPLAY_NAME = MultilingualString(
        en="SMOTE (Oversampling)", es="SMOTE (Sobre-muestreo)"
    )
    IMAGE_PREVIEW = "smote.png"

    def __init__(self, **kwargs):
        """Initialise by forwarding kwargs to the imbalanced-learn wrapper.

        Parameters
        ----------
        **kwargs : dict
            Keyword arguments forwarded to :class:`ImbalancedLearnWrapper`.
        """
        super().__init__(**kwargs)

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Not implemented; type preservation is handled in ``transform``.

        Raises
        ------
        NotImplementedError
            Always, because type determination is delegated to ``transform``.
        """
        raise NotImplementedError(
            "SMOTE preserves input types. Types are handled in the transform method."
        )

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
    """Schema for SMOTEConverter hyperparameters.

    Configures the sampling strategy, random seed, and neighbourhood size for
    imbalanced-learn's ``SMOTE`` over-sampler. The key parameter is
    ``sampling_strategy``, which controls how many synthetic samples are created
    relative to the majority class.
    """

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

    SMOTE (Synthetic Minority Over-sampling Technique) addresses class imbalance
    by creating new minority-class examples via linear interpolation between each
    minority sample and one of its ``k`` nearest minority-class neighbours. Unlike
    simple random over-sampling (which duplicates existing rows), SMOTE generates
    novel samples in the feature space, improving classifier generalisation.

    The technique is applied only during training; the test split is never resampled.
    All schema parameters are forwarded to imbalanced-learn's ``SMOTE`` estimator.

    References
    ----------
    - [1] Chawla, N.V. et al. (2002). "SMOTE: Synthetic Minority Over-sampling
           Technique." Journal of Artificial Intelligence Research, 16, 321-357.
           https://arxiv.org/abs/1106.1813
    - [2] https://imbalanced-learn.org/stable/references/generated/imblearn.over_sampling.SMOTE.html
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

    metadata = {
        "allowed_dtypes": ["int64", "float64", "float32"],
        "restricted_dtypes": [],
    }

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

        SMOTE preserves the types of all input columns; type assignment is
        performed directly in ``transform`` rather than here.

        Parameters
        ----------
        column_name : str or None, optional
            Name of the column whose output type is queried. Ignored because
            this method always raises. Default ``None``.

        Raises
        ------
        NotImplementedError
            Always, because type determination is delegated to ``transform``.
        """
        raise NotImplementedError(
            "SMOTE preserves input types. Types are handled in the transform method."
        )

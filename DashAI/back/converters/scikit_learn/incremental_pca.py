from sklearn.decomposition import IncrementalPCA as IncrementalPCAOperation

from DashAI.back.converters.category.dimensionality_reduction import (
    DimensionalityReductionConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    bool_field,
    int_field,
    none_type,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString


class IncrementalPCASchema(BaseSchema):
    n_components: schema_field(
        none_type(int_field(ge=1)),
        2,
        description=MultilingualString(
            en="Number of components to keep.",
            es="Número de componentes a conservar.",
        ),
    )  # type: ignore
    whiten: schema_field(
        bool_field(),
        False,
        description=MultilingualString(
            en=(
                "When True the components_ are scaled to ensure uncorrelated "
                "outputs with unit variances."
            ),
            es=(
                "Cuando es True las componentes se escalan para asegurar salidas "
                "no correlacionadas con varianzas unitarias."
            ),
        ),
    )  # type: ignore
    use_copy: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en=(
                "If False, data passed to fit are overwritten. Use "
                "fit_transform(X) instead."
            ),
            es=(
                "Si es False, los datos pasados a fit se sobrescriben. Usa "
                "fit_transform(X) en su lugar."
            ),
        ),
        alias=MultilingualString(en="copy", es="copiar"),
    )  # type: ignore
    batch_size: schema_field(
        none_type(int_field(ge=1)),
        None,
        description=MultilingualString(
            en="The number of samples to use for each batch.",
            es="Número de muestras a usar por lote.",
        ),
    )  # type: ignore


class IncrementalPCA(
    DimensionalityReductionConverter, SklearnWrapper, IncrementalPCAOperation
):
    """Scikit-learn's IncrementalPCA wrapper for DashAI."""

    SCHEMA = IncrementalPCASchema
    DESCRIPTION = MultilingualString(
        en=(
            "Incremental PCA (IPCA) is typically used as a replacement for PCA "
            "when the dataset is too large to fit in memory."
        ),
        es=(
            "El PCA incremental (IPCA) se usa típicamente como reemplazo de PCA "
            "cuando el conjunto de datos es demasiado grande para caber en memoria."
        ),
    )
    SHORT_DESCRIPTION = MultilingualString(
        en="Dimensionality reduction using Incremental PCA.",
        es="Reducción de dimensionalidad usando PCA incremental.",
    )
    DISPLAY_NAME = MultilingualString(en="Incremental PCA", es="PCA Incremental")
    IMAGE_PREVIEW = "incremental_pca.png"

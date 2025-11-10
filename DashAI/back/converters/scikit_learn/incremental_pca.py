import pyarrow as pa
from sklearn.decomposition import IncrementalPCA as IncrementalPCAOperation

from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    bool_field,
    int_field,
    none_type,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class IncrementalPCASchema(BaseSchema):
    n_components: schema_field(
        none_type(int_field(ge=1)),
        2,
        "Number of components to keep.",
    )  # type: ignore
    whiten: schema_field(
        bool_field(),
        False,
        (
            "When True (False by default) the components_ vectors "
            "are multiplied by the square root of n_samples and then "
            "divided by the singular values to ensure uncorrelated "
            "outputs with unit component-wise variances."
        ),
    )  # type: ignore
    use_copy: schema_field(
        bool_field(),
        True,
        (
            "If False, data passed to fit are overwritten and running "
            "fit(X).transform(X) will not yield the expected results, "
            "use fit_transform(X) instead."
        ),
        alias="copy",
    )  # type: ignore
    batch_size: schema_field(
        none_type(int_field(ge=1)),
        None,
        "The number of samples to use for each batch.",
    )  # type: ignore


class IncrementalPCA(SklearnWrapper, IncrementalPCAOperation):
    """Scikit-learn's IncrementalPCA wrapper for DashAI."""

    SCHEMA = IncrementalPCASchema
    DESCRIPTION = "Incremental principal components analysis (IPCA)."
    DISPLAY_NAME = "Incremental PCA"

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for transformed data."""
        return Float(arrow_type=pa.float64())

from sklearn.feature_selection import SelectFwe as SelectFweOperation

from DashAI.back.converters.category.feature_selection import FeatureSelectionConverter
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import float_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float, Integer


class SelectFweSchema(BaseSchema):
    """Configuration schema for the SelectFwe converter.

    Defines and validates the hyperparameters passed to
    ``sklearn.feature_selection.SelectFwe``.
    """

    alpha: schema_field(
        float_field(ge=0.0, le=1.0),
        0.05,
        description=MultilingualString(
            en="The highest uncorrected p-value for features to be kept.",
            es=(
                "El p-valor sin corregir más alto para que una característica "
                "sea conservada."
            ),
            pt=(
                "O p-valor não corrigido mais alto para que uma característica "
                "seja mantida."
            ),
        ),
    )  # type: ignore


class SelectFwe(FeatureSelectionConverter, SklearnWrapper, SelectFweOperation):
    """Select features while controlling the Family-Wise Error Rate (FWE).

    SelectFwe applies the Bonferroni correction to the p-values produced by a
    univariate scoring function: a feature is retained only if its raw p-value
    is at most ``alpha / n_features``. This guarantees that the probability of
    making even one false positive among all selected features is bounded by
    ``alpha``, providing the strongest multiple-testing guarantee of the three
    p-value-based filter selectors (FPR, FDR, FWE).

    FWE control is most appropriate when any single false positive is costly,
    for example in confirmatory studies, safety-critical applications, or
    settings where downstream analysis of each selected feature is expensive.
    Because the correction grows more conservative as the number of features
    increases, it may discard many truly informative features in very
    high-dimensional problems; in such cases FDR control may be preferable.

    Key properties:

    - Supervised: requires the target array ``y`` at fit time.
    - ``alpha`` is the family-wise significance level in [0, 1]; typical values
      are 0.05 or 0.01.
    - Most conservative of the three p-value-based filters at the same
      ``alpha``; tends to retain fewer features than FDR or FPR.
    - The number of retained features is data-driven and not fixed in advance.

    Wraps scikit-learn's ``SelectFwe``.

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.SelectFwe.html
    """

    SCHEMA = SelectFweSchema
    DESCRIPTION = MultilingualString(
        en="Filter: Select features according to a family-wise error rate test.",
        es=(
            "Filtro: Selecciona características según una prueba de tasa de "
            "error familiar (FWE)."
        ),
        pt=(
            "Filtro: Seleciona características de acordo com um teste de taxa "
            "de erro familiar (FWE)."
        ),
    )
    SUPERVISED = True
    DISPLAY_NAME = MultilingualString(
        en="Select FWE", es="Seleccionar FWE", pt="Seleção por FWE"
    )
    IMAGE_PREVIEW = "select_fwe.png"
    metadata = {"allowed_types": [Float, Integer], "allowed_dtypes": []}

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Return the DashAI data type produced by this converter for a column.

        Parameters
        ----------
        column_name : str, optional
            Not used; all output columns share the
            same type. Defaults to None.

        Returns
        -------
        DashAIDataType
            A Float type backed by ``pyarrow.float64()``.
        """
        import pyarrow as pa

        return Float(arrow_type=pa.float64())

    def __init__(self, **kwargs):
        """Initialize the SelectFwe converter.

        Parameters
        ----------
        **kwargs
            Configuration keyword arguments matching the converter's
            schema fields. Forwarded to the underlying scikit-learn class.
        """
        super().__init__(**kwargs)

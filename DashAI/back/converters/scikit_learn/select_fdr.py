from sklearn.feature_selection import SelectFdr as SelectFdrOperation

from DashAI.back.converters.category.feature_selection import FeatureSelectionConverter
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import float_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class SelectFdrSchema(BaseSchema):
    """Configuration schema for the SelectFdr converter.

    Defines and validates the hyperparameters passed to
    ``sklearn.feature_selection.SelectFdr``.
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
        ),
    )  # type: ignore


class SelectFdr(FeatureSelectionConverter, SklearnWrapper, SelectFdrOperation):
    """Select features by controlling the expected False Discovery Rate (FDR).

    SelectFdr applies the Benjamini-Hochberg procedure to the p-values produced
    by a univariate scoring function, retaining only those features whose
    (adjusted) p-value is at most ``alpha``. The FDR criterion bounds the
    expected proportion of selected features that are actually uninformative,
    offering a less conservative rejection policy than Family-Wise Error control
    while still providing statistical guarantees.

    This filter is well suited to high-dimensional settings (e.g. genomics,
    metabolomics) where many features are tested simultaneously and a small
    fraction of false positives among the selected set is acceptable in
    exchange for higher sensitivity.

    Key properties:

    - Supervised: requires the target array ``y`` at fit time.
    - ``alpha`` is the target FDR level in [0, 1]; typical values are 0.05
      or 0.10.
    - Less conservative than FWE (Bonferroni) correction: retains more features
      at the same nominal ``alpha`` when the number of tests is large.
    - The number of retained features is data-driven and not fixed in advance.

    Wraps scikit-learn's ``SelectFdr``.

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.SelectFdr.html
    """

    SCHEMA = SelectFdrSchema
    DESCRIPTION = MultilingualString(
        en="Filter: Select features according to a false discovery rate test.",
        es=(
            "Filtro: Selecciona características según una prueba de tasa de "
            "falsos descubrimientos (FDR)."
        ),
    )
    SUPERVISED = True
    DISPLAY_NAME = MultilingualString(en="Select FDR", es="Seleccionar FDR")
    IMAGE_PREVIEW = "select_fdr.png"
    metadata = {
        "allowed_dtypes": ["int64", "float64", "float32"],
        "restricted_dtypes": [],
    }

    def __init__(self, **kwargs):
        """Initialize the SelectFdr converter.

        Parameters
        ----------
        **kwargs
            Configuration keyword arguments matching the converter's
            schema fields. Forwarded to the underlying scikit-learn class.
        """
        super().__init__(**kwargs)

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

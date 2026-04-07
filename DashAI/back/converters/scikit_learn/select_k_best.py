from sklearn.feature_selection import SelectKBest as SelectKBestOperation

from DashAI.back.converters.category.feature_selection import FeatureSelectionConverter
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    enum_field,
    int_field,
    schema_field,
    union_type,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class SelectKBestSchema(BaseSchema):
    """Configuration schema for the SelectKBest converter.

    Defines and validates the hyperparameters passed to
    ``sklearn.feature_selection.SelectKBest``.
    """

    k: schema_field(
        union_type(enum_field(["all"]), int_field(ge=1)),
        10,
        description=MultilingualString(
            en="Number of top features to select.",
            es="Número de características superiores a seleccionar.",
        ),
    )  # type: ignore


class SelectKBest(FeatureSelectionConverter, SklearnWrapper, SelectKBestOperation):
    """Select the K highest-scoring features using a univariate statistical test.

    SelectKBest evaluates each input feature independently against the target
    variable using a scoring function (e.g. ``f_classif`` for ANOVA F-statistic,
    ``chi2`` for chi-squared, or ``mutual_info_classif`` for mutual information),
    then retains the ``k`` features with the highest scores, discarding the rest.

    This filter method is computationally cheap and can substantially reduce
    dimensionality before feeding data to a more expensive estimator. It is
    particularly useful as a first-pass feature selection step in classification
    and regression pipelines.

    Key properties:

    - Supervised: requires the target array ``y`` at fit time.
    - Setting ``k='all'`` is a no-op that passes every feature through;
      useful for pipeline grid searches where ``k`` is a tuned parameter.
    - Feature ranking is based solely on univariate statistics; it does not
      account for feature interactions.
    - The choice of scoring function should match the problem type
      (classification vs. regression) and the scale of the features.

    Wraps scikit-learn's ``SelectKBest``.

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.SelectKBest.html
    """

    SCHEMA = SelectKBestSchema
    DESCRIPTION = MultilingualString(
        en="Select features according to the k highest scores.",
        es="Selecciona características según las k puntuaciones más altas.",
    )
    SUPERVISED = True
    DISPLAY_NAME = MultilingualString(en="Select K Best", es="Seleccionar K Mejores")
    IMAGE_PREVIEW = "select_k_best.png"
    metadata = {
        "allowed_dtypes": ["int64", "float64", "float32"],
        "restricted_dtypes": [],
    }

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
        """Initialize the SelectKBest converter.

        Patches ``_get_tags`` to advertise ``requires_y=True`` so that the
        pipeline passes the target array at fit time, then delegates to the
        parent initializer.

        Parameters
        ----------
        **kwargs
            Configuration keyword arguments matching the converter's
            schema fields. Forwarded to the underlying scikit-learn class.
        """
        if callable(self._get_tags):
            original_get_tags = self._get_tags
            self._get_tags = lambda *a, **k: {
                **original_get_tags(*a, **k),
                "requires_y": True,
            }
        else:
            self._get_tags = {**self._get_tags, "requires_y": True}
        super().__init__(**kwargs)

from sklearn.preprocessing import OneHotEncoder as OneHotEncoderOperation

from DashAI.back.api.utils import cast_string_to_type, parse_string_to_list
from DashAI.back.converters.category.encoding import EncodingConverter
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    enum_field,
    float_field,
    int_field,
    none_type,
    schema_field,
    string_field,
    union_type,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Integer


class OneHotEncoderSchema(BaseSchema):
    """Schema for OneHotEncoder hyperparameters.

    Configures the category handling, output dtype, unknown-value strategy,
    infrequent-category grouping, and feature-name combining behaviour for
    sklearn's ``OneHotEncoder``. The ``categories`` field accepts ``"auto"``
    or an explicit list string; ``drop`` controls whether one indicator column
    per feature is dropped to avoid multicollinearity.
    """

    categories: schema_field(
        string_field(),
        "auto",
        description=MultilingualString(
            en="The categories of each feature.",
            es="Las categorías de cada característica.",
        ),
    )  # type: ignore
    drop: schema_field(
        none_type(string_field()),
        None,
        description=MultilingualString(
            en=("Specifies a methodology to drop one of the categories per feature."),
            es=(
                "Especifica una metodología para eliminar una categoría por "
                "característica."
            ),
        ),
    )  # type: ignore
    dtype: schema_field(
        enum_field(["int", "np.float32", "np.float64"]),
        "np.float64",
        description=MultilingualString(
            en="Desired dtype of output.",
            es="Tipo de dato de salida deseado.",
        ),
    )  # type: ignore
    handle_unknown: schema_field(
        enum_field(["error", "ignore", "infrequent_if_exist"]),
        "error",
        description=MultilingualString(
            en=("How to handle unknown categories during transform."),
            es=("Cómo manejar categorías desconocidas durante la transformación."),
        ),
    )  # type: ignore
    min_frequency: schema_field(
        none_type(union_type(int_field(ge=0), float_field(ge=0.0, le=1.0))),
        None,
        description=MultilingualString(
            en="Minimum frequency of a category to be considered as frequent.",
            es="Frecuencia mínima para considerar una categoría como frecuente.",
        ),
    )  # type: ignore
    max_categories: schema_field(
        none_type(int_field(ge=1)),
        None,
        description=MultilingualString(
            en="Maximum number of categories to encode.",
            es="Número máximo de categorías a codificar.",
        ),
    )  # type: ignore
    feature_name_combiner: schema_field(
        enum_field(["concat"]),
        "concat",
        description=MultilingualString(
            en="Method used to combine feature names.",
            es="Método usado para combinar nombres de características.",
        ),
    )  # type: ignore


class OneHotEncoder(EncodingConverter, SklearnWrapper, OneHotEncoderOperation):
    """Encode categorical columns as binary indicator (one-hot) vectors.

    For each input feature column every unique category value becomes a
    separate binary output column. Given a feature with ``k`` categories the
    encoding produces ``k`` columns (or ``k - 1`` when ``drop`` is set) where
    exactly one column is 1 and the rest are 0:

    * **Nominal categories without order** — one-hot encoding treats all
      categories as equidistant, which is appropriate for unordered labels
      such as city names or product types.
    * **Avoiding the dummy-variable trap** — the ``drop`` parameter can
      remove one indicator column per feature so that the resulting matrix
      has full rank, which is required by unregularized linear models.
    * **Infrequent categories** — ``min_frequency`` and ``max_categories``
      can group rare values into a single ``infrequent_categories`` bin,
      reducing dimensionality.

    The total number of output columns equals the sum of unique category
    counts across all encoded input columns (minus dropped columns).

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OneHotEncoder.html
    """

    SCHEMA = OneHotEncoderSchema
    DESCRIPTION = MultilingualString(
        en="Encode categorical integer features as a one-hot numeric array.",
        es=(
            "Codifica características categóricas enteras como un arreglo "
            "numérico one-hot."
        ),
    )
    DISPLAY_NAME = MultilingualString(en="One-Hot Encoder", es="Codificador One-Hot")
    IMAGE_PREVIEW = "one_hot_encoder.png"

    def __init__(self, **kwargs):
        """Initialize the OneHotEncoder converter.

        Parameters
        ----------
        **kwargs
            Configuration keyword arguments matching the converter's
            schema fields. String representations of ``categories`` and
            ``drop`` are parsed into lists when they are not sentinel values;
            ``dtype`` strings are cast to NumPy types; ``sparse_output`` is
            forced to ``False`` for pandas compatibility. Remaining kwargs
            are forwarded to the underlying scikit-learn class.
        """
        self.categories = kwargs.pop("categories", "auto")
        if self.categories != "auto":
            self.categories = [parse_string_to_list(self.categories)]
        kwargs["categories"] = self.categories

        self.drop = kwargs.pop("drop", None)
        if self.drop is not None and self.drop != "first" and self.drop != "if_binary":
            self.drop = [parse_string_to_list(self.drop)]
        kwargs["drop"] = self.drop

        self.dtype = kwargs.pop("dtype", "np.float64")
        self.dtype = cast_string_to_type(self.dtype)
        kwargs["dtype"] = self.dtype

        # Pandas output does not support sparse data. Set sparse_output=False
        self.sparse_output = kwargs.pop("sparse_output", False)
        kwargs["sparse_output"] = self.sparse_output

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
            An Integer type backed by ``pyarrow.int64()``,
            representing the binary indicator values (0 or 1).
        """
        import pyarrow as pa

        return Integer(arrow_type=pa.int64())

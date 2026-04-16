from sklearn.preprocessing import OrdinalEncoder as OrdinalEncoderOperation

from DashAI.back.api.utils import cast_string_to_type
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
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.dashai_data_type import DashAIDataType


class OrdinalEncoderSchema(BaseSchema):
    """Schema for OrdinalEncoder hyperparameters.

    Configures the category ordering, output dtype, unknown-value handling,
    and infrequent-category grouping for sklearn's ``OrdinalEncoder``. The
    ``handle_unknown`` field determines whether an unseen category at
    transform time raises an error or is replaced by a sentinel value
    specified in ``unknown_value``.
    """

    categories: schema_field(
        string_field(),
        "auto",
        description=MultilingualString(
            en="Categories (unique values) per feature.",
            es="Categorías (valores únicos) por característica.",
        ),
    )  # type: ignore
    dtype: schema_field(
        enum_field(["np.int32", "np.int64", "np.float32", "np.float64"]),
        "np.float64",
        description=MultilingualString(
            en="Desired dtype of output.",
            es="Tipo de dato de salida deseado.",
        ),
    )  # type: ignore
    handle_unknown: schema_field(
        enum_field(["error", "use_encoded_value"]),
        "error",
        description=MultilingualString(
            en=(
                "Whether to raise an error or use a specific encoded value when "
                "an unknown category is seen."
            ),
            es=(
                "Si se debe lanzar un error o usar un valor codificado específico "
                "cuando se vea una categoría desconocida."
            ),
        ),
    )  # type: ignore
    unknown_value: schema_field(
        none_type(enum_field(["int", "np.nan"])),
        None,
        description=MultilingualString(
            en="The value to use for unknown categories.",
            es="El valor a usar para categorías desconocidas.",
        ),
    )  # type: ignore
    # Added in version 1.3
    min_frequency: schema_field(
        none_type(union_type(int_field(ge=1), float_field(ge=0.0, le=1.0))),
        None,
        description=MultilingualString(
            en="Minimum frequency of a category to be considered as frequent.",
            es="Frecuencia mínima para considerar una categoría como frecuente.",
        ),
    )  # type: ignore
    # Added in version 1.3
    max_categories: schema_field(
        none_type(int_field(ge=1)),
        None,
        description=MultilingualString(
            en="Maximum number of categories to encode.",
            es="Número máximo de categorías a codificar.",
        ),
    )  # type: ignore


class OrdinalEncoder(EncodingConverter, SklearnWrapper, OrdinalEncoderOperation):
    """Encode categorical feature columns as integer ordinal codes.

    For each input feature column every unique category value is mapped to a
    contiguous integer starting at 0. Given categories ``["cold", "warm",
    "hot"]`` sorted alphabetically the default mapping would be
    ``cold -> 0``, ``hot -> 1``, ``warm -> 2``; a custom category list can
    be supplied to impose a domain-specific order.

    Unlike ``OneHotEncoder``, ordinal encoding produces a single output
    column per input column and implicitly encodes a numerical order between
    the categories. This makes it appropriate when:

    * The categories have a meaningful rank (e.g. education level, severity
      score, shirt size).
    * The downstream model can exploit ordinal structure (e.g. tree-based
      models such as gradient-boosted trees or random forests).

    For unordered nominal categories, ``OneHotEncoder`` is typically
    preferred because ordinal codes introduce a spurious ordering.

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OrdinalEncoder.html
    """

    SCHEMA = OrdinalEncoderSchema
    DESCRIPTION = MultilingualString(
        en="Encode categorical features as an integer array.",
        es="Codifica características categóricas como un arreglo de enteros.",
    )
    DISPLAY_NAME = MultilingualString(en="Ordinal Encoder", es="Codificador Ordinal")
    IMAGE_PREVIEW = "ordinal_encoder.png"

    metadata = {
        "allowed_dtypes": ["string"],
        "restricted_dtypes": [],
    }

    def __init__(self, **kwargs):
        """Initialize the OrdinalEncoder converter.

        Parameters
        ----------
        **kwargs
            Configuration keyword arguments matching the converter's
            schema fields. ``dtype``, ``unknown_value``, and
            ``min_frequency`` string values are cast to their corresponding
            NumPy or Python types before being forwarded to the underlying
            scikit-learn class.
        """
        self.dtype = kwargs.pop("dtype", "np.float64")
        self.dtype = cast_string_to_type(self.dtype)
        kwargs["dtype"] = self.dtype

        self.unknown_value = kwargs.pop("unknown_value", None)
        if self.unknown_value is not None:
            self.unknown_value = cast_string_to_type(self.unknown_value)
        kwargs["unknown_value"] = self.unknown_value

        self.min_frequency = kwargs.pop("min_frequency", None)
        if self.min_frequency is not None:
            self.min_frequency = cast_string_to_type(self.min_frequency)
        kwargs["min_frequency"] = self.min_frequency

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
            A placeholder ``Categorical`` type with two string
            values (``"0"`` and ``"1"``). The actual category values are not
            reflected at schema-declaration time; the real categories are
            available after fitting via ``self.categories_``.
        """
        import pyarrow as pa

        # Return a placeholder categorical type
        # The actual categories will be set by sklearn_wrapper's transform method
        return Categorical(values=pa.array(["0", "1"]))

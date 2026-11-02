from typing import TYPE_CHECKING, Dict, List, Union

from DashAI.back.converters.category.encoding import EncodingConverter
from DashAI.back.converters.drop_source_columns import AddColumnsConverterSchema
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import enum_field, schema_field
from DashAI.back.core.schema_fields.utils import schema_placeholder_defaults
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Integer

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
    from DashAI.back.preprocessing.structure_types import ColumnItem


class LabelEncoderSchema(AddColumnsConverterSchema):
    """Schema for LabelEncoder hyperparameters.

    sklearn's ``LabelEncoder`` has no hyperparameters. DashAI's adds one:
    what to do with a label not seen in ``fit``.
    """

    handle_unknown: schema_field(
        enum_field(["error", "use_encoded_value"]),
        # Strict, as the notebook uses it: there it may be fitted on a subset
        # of rows and applied to all of them, and what it writes is saved. A
        # session encodes an unseen label instead (``SESSION_PARAMS``).
        "error",
        description=MultilingualString(
            en=(
                "Whether to raise an error or encode as -1 a label not seen during fit."
            ),
            es=(
                "Si lanzar un error o codificar como -1 una etiqueta que no se "
                "vio durante el ajuste."
            ),
            pt=(
                "Se deve gerar um erro ou codificar como -1 um rótulo não visto "
                "durante o ajuste."
            ),
            de=(
                "Ob bei einer beim Anpassen nicht gesehenen Kategorie ein Fehler "
                "ausgelöst oder sie als -1 kodiert wird."
            ),
            zh="对拟合时未见过的标签是报错还是编码为 -1。",
        ),
    )  # type: ignore


class LabelEncoder(EncodingConverter, SklearnWrapper):
    """Encode categorical labels as contiguous integer codes in [0, n_classes - 1].

    Each unique label value is mapped to a unique integer in ascending order
    of the sorted class list. For example, given classes ``["cat", "dog",
    "fish"]`` the mapping is ``cat -> 0``, ``dog -> 1``, ``fish -> 2``.

    Unlike ``OrdinalEncoder`` (which operates on feature columns),
    ``LabelEncoder`` is designed for target label columns. It is typically
    applied to the output column before training classifiers that require
    numeric class indices (e.g. gradient-boosted trees, support vector
    machines, or any model that indexes a class-weight array). The DashAI
    implementation extends the sklearn behaviour to support multiple columns
    and to preserve ``NaN`` values during transformation.

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.LabelEncoder.html
    """

    SCHEMA = LabelEncoderSchema
    DESCRIPTION = MultilingualString(
        en="Encode target labels with value between 0 and n_classes-1.",
        es="Codifica etiquetas objetivo con valores entre 0 y n_clases-1.",
        pt="Codifica rótulos alvo com valores entre 0 e n_classes-1.",
        de="Zielgrößen mit Werten zwischen 0 und n_Klassen-1 kodieren.",
        zh="将目标标签编码为 0 到 n_classes-1 之间的值。",
    )
    SHORT_DESCRIPTION = MultilingualString(
        en="Convert categorical labels to numeric values",
        es="Convierte etiquetas categóricas a valores numéricos",
        pt="Converte rótulos categóricos em valores numéricos",
        de="Kategoriale Zielgrößen in numerische Werte umwandeln",
        zh="将类别标签转换为数值",
    )
    DISPLAY_NAME = MultilingualString(
        en="Label Encoder",
        es="Codificador de Etiquetas",
        pt="Codificador de Rótulos",
        de="Zielgrößen-Kodierer",
        zh="标签编码器",
    )
    IMAGE_PREVIEW = "label_encoder.png"

    PREFIX = "le_"
    ONE_COLUMN_PER_INPUT = True

    UNKNOWN_HINT = 'set "handle_unknown" to "use_encoded_value" to encode them as -1'

    # A session fits its converters on the training rows only, so a label
    # seen only in validation, test or the rows to predict is the normal
    # case, not an accident: it gets -1.
    SESSION_PARAMS = {"handle_unknown": "use_encoded_value"}

    metadata = {
        "changes_data_types": True,
        "allowed_types": [Categorical],
        "allowed_dtypes": [],
    }

    def __init__(self, **kwargs):
        """Initialize the LabelEncoder converter.

        Initializes the per-column encoder registry (``self.encoders``) and the
        list of fitted columns (``self.fitted_columns``). Note that ``kwargs``
        are not forwarded to the underlying scikit-learn class.

        Parameters
        ----------
        **kwargs
            Configuration keyword arguments matching the converter's
            schema fields. A field left out takes its schema default, as the
            form would have sent it. Not forwarded to the parent class.
        """
        super().__init__()
        kwargs = {**schema_placeholder_defaults(type(self)), **kwargs}
        self.handle_unknown = kwargs["handle_unknown"]
        self.encoders = {}
        self.fitted_columns = []

    def _encodes(self, item: "ColumnItem") -> bool:
        """Whether ``fit`` will encode a scope column.

        ``fit`` only encodes columns stored as strings, so a Categorical
        column of numeric labels (e.g. dtype int64) gets no encoded copy.
        """
        return item.type == "Text" or item.dtype == "string"

    def unseen_values(self, x: "DashAIDataset") -> Dict[str, List[str]]:
        """The labels of each fitted column of ``x`` that ``fit`` did not see.

        Parameters
        ----------
        x : DashAIDataset
            Rows of the converter's scope, as ``transform`` would get them.

        Returns
        -------
        dict
            Column name to its unseen labels as sorted strings, only for the
            columns that have any.
        """
        frame = x.to_pandas()
        unseen = {}
        for col in self.fitted_columns:
            if col not in frame.columns:
                continue
            values = frame[col].dropna()
            known = self.encoders[col].classes_
            new = sorted({str(v) for v in values[~values.isin(known)]})
            if new:
                unseen[col] = new
        return unseen

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Return the DashAI data type produced by this converter for a column.

        Parameters
        ----------
        column_name : str, optional
            Not used. Defaults to None.

        Returns
        -------
        DashAIDataType
            An Integer type backed by ``pyarrow.int64()``, representing the
            contiguous integer label codes produced by the encoder.
        """
        import pyarrow as pa

        return Integer(arrow_type=pa.int64())

    def fit(self, x: "DashAIDataset", y: Union["DashAIDataset", None] = None):
        """Fit a LabelEncoder for each eligible column in the dataset.

        Only columns with string, object, or category dtype (or a matching
        DashAI type) are processed. NaN values are masked out before fitting.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset whose categorical/string columns will be encoded.
        y : DashAIDataset or None, optional
            Ignored. Present for API compatibility. Default ``None``.

        Returns
        -------
        LabelEncoderConverter
            The fitted converter instance (``self``).
        """
        from sklearn.preprocessing import LabelEncoder as LabelEncoderOperation

        x_pandas = x.to_pandas()

        for col in x_pandas.columns:
            # Check if column type is in allowed_dtypes using DashAI types
            col_type = x.types.get(col)
            col_dtype = col_type.dtype if hasattr(col_type, "dtype") else None

            # Allow string dtype or if it's a string-like pandas dtype
            is_allowed = col_dtype in self.metadata["allowed_dtypes"] or x_pandas[
                col
            ].dtype.name in ["object", "category", "string"]

            if is_allowed:
                mask = x_pandas[col].notna()
                if mask.any():
                    encoder = LabelEncoderOperation()
                    encoder.fit(x_pandas.loc[mask, col])
                    self.encoders[col] = encoder
                    self.fitted_columns.append(col)

        return self

    def transform(
        self, x: "DashAIDataset", y: Union["DashAIDataset", None] = None
    ) -> "DashAIDataset":
        """Apply fitted label encoders and append encoded columns with a prefix.

        Encodes each fitted column and appends the result as a new
        ``encoded_<col>`` column. The original column is left unchanged. A
        label the encoder did not see in ``fit`` is encoded as ``-1`` with
        ``handle_unknown="use_encoded_value"``; with ``"error"``, it raises.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset. Columns not seen during ``fit`` are left unchanged.
        y : DashAIDataset or None, optional
            Ignored. Present for API compatibility. Default ``None``.

        Returns
        -------
        DashAIDataset
            Dataset with original columns preserved plus new ``encoded_*``
            columns appended containing the integer label codes.
        """
        import pyarrow as pa

        from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

        x_pandas = x.to_pandas()

        combined_table = x.arrow_table
        combined_types = dict(x.types)

        # Pickled before the option existed, an encoder only knew -1.
        treat = getattr(self, "handle_unknown", "use_encoded_value") == (
            "use_encoded_value"
        )
        for col in self.fitted_columns:
            if col not in x_pandas.columns:
                continue
            series = x_pandas[col].copy()
            mask = series.notna()
            # A label not seen in fit gets -1, like the ordinal encoder's
            # unknown value: the encoder is never refitted on the rows it
            # encodes. Strict, every label goes to sklearn, which refuses it.
            seen = mask & series.isin(self.encoders[col].classes_) if treat else mask
            if seen.any():
                series.loc[seen] = self.encoders[col].transform(series.loc[seen])
            series.loc[mask & ~seen] = -1
            prefixed = f"{self.PREFIX}{col}"
            combined_table = combined_table.append_column(
                prefixed, pa.array(series.tolist(), type=pa.int64())
            )
            combined_types[prefixed] = self.get_output_type(col)

        return DashAIDataset(combined_table, types=combined_types, splits=x.splits)

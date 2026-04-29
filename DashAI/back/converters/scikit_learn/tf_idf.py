from typing import TYPE_CHECKING, Optional

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.converters.category.advanced_preprocessing import (
    AdvancedPreprocessingConverter,
)
from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    enum_field,
    int_field,
    none_type,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float, Text

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class TFIDFConverterSchema(BaseSchema):
    """Schema for configuring the TFIDFConverter.

    Wraps ``sklearn.feature_extraction.text.TfidfVectorizer`` and exposes
    vocabulary size, casing, stop-word removal, and n-gram range as schema
    fields validated before being forwarded to the underlying scikit-learn
    estimator.
    """

    max_features: schema_field(
        int_field(gt=0),
        placeholder=1000,
        description=MultilingualString(
            en=("Maximum number of features (most frequent terms) to keep."),
            es=(
                "Número máximo de características (términos más frecuentes) "
                "a conservar."
            ),
        ),
    )  # type: ignore
    lowercase: schema_field(
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en=("Whether to convert all characters to lowercase before tokenizing."),
            es=("Si se debe convertir todo a minúsculas antes de tokenizar."),
        ),
    )  # type: ignore
    stop_words: schema_field(
        none_type(enum_field(["english"])),
        placeholder=None,
        description=MultilingualString(
            en="Stop word set to remove. Use 'english' or None.",
            es="Conjunto de stopwords a eliminar. Usa 'english' o None.",
        ),
    )  # type: ignore
    lower_bound_ngrams: schema_field(
        int_field(gt=0, le=5),
        placeholder=1,
        description=MultilingualString(
            en=("Lower bound for n-grams to be extracted. Must be <= upper bound."),
            es=(
                "Límite inferior de n-grams a extraer. Debe ser <= al límite superior."
            ),
        ),
    )  # type: ignore
    upper_bound_ngrams: schema_field(
        int_field(gt=0, le=5),
        placeholder=1,
        description=MultilingualString(
            en=("Upper bound for n-grams to be extracted. Must be >= lower bound."),
            es=(
                "Límite superior de n-grams a extraer. Debe ser >= al límite inferior."
            ),
        ),
    )  # type: ignore


class TFIDFConverter(AdvancedPreprocessingConverter, BaseConverter):
    """Convert raw text documents into a matrix of TF-IDF weighted features.

    TF-IDF (Term Frequency - Inverse Document Frequency) re-weights raw token
    counts so that terms that appear frequently in a specific document but
    rarely across the whole corpus receive a higher score, while common
    stop-like terms are down-weighted. Each document is represented as a
    floating-point vector of TF-IDF scores, one dimension per vocabulary term.

    The TF-IDF score for term *t* in document *d* is:

        tfidf(t, d) = tf(t, d) x log((1 + n) / (1 + df(t))) + 1

    where *n* is the total number of documents and *df(t)* is the number of
    documents containing *t* (scikit-learn's ``smooth_idf=True`` default).

    Optional preprocessing steps include lower-casing, stop-word removal, and
    n-gram extraction. The result is a floating-point DashAI dataset with one
    column per vocabulary term.

    Internally wraps ``sklearn.feature_extraction.text.TfidfVectorizer``.

    The TF-IDF weighting scheme was introduced as a core technique in
    information retrieval by Salton & McGill (1983) [2].

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html
    - [2] Salton, G. & McGill, M. J. (1983). Introduction to Modern Information
        Retrieval. McGraw-Hill.
    """

    TAGS = ["text", "encoding", "sparse"]
    SCHEMA = TFIDFConverterSchema
    DISPLAY_NAME = MultilingualString(en="TF-IDF", es="TF-IDF")
    IMAGE_PREVIEW = "tf_idf.png"

    metadata = {
        "allowed_types": [Text],
        "allowed_dtypes": [],
    }
    DESCRIPTION = MultilingualString(
        en=(
            "Converts text into a TF-IDF representation with one column per "
            "token (TF-IDF weight per token)."
        ),
        es=(
            "Convierte texto en una representación TF-IDF con una columna por "
            "token (peso TF-IDF por token)."
        ),
    )

    def __init__(self, **kwargs):
        """Initialise the TF-IDF converter and configure the vectorizer.

        Parameters
        ----------
        **kwargs : dict
            max_features : int, optional
                Maximum vocabulary size. Default ``1000``.
            lowercase : bool, optional
                Convert all text to lowercase before tokenizing. Default ``True``.
            stop_words : str or list, optional
                Stop-word list to remove. Default ``"english"``.
            lower_bound_ngrams : int, optional
                Minimum n-gram size. Default ``1``.
            upper_bound_ngrams : int, optional
                Maximum n-gram size. Default ``1``.
        """
        super().__init__()
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.vectorizer = TfidfVectorizer(
            max_features=kwargs.get("max_features", 1000),
            lowercase=kwargs.get("lowercase", True),
            stop_words=kwargs.get("stop_words"),
            ngram_range=(
                kwargs.get("lower_bound_ngrams", 1),
                kwargs.get("upper_bound_ngrams", 1),
            ),
        )
        self.fitted = False

    def fit(self, x: "DashAIDataset", y=None) -> "TFIDFConverter":
        """Fit TfidfVectorizer on the first text column of the dataset.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset. Only the first column is used for fitting.
        y : ignored
            Present for API compatibility.

        Returns
        -------
        TFIDFConverter
            The fitted converter instance (``self``).
        """
        X_df = x.to_pandas()
        texts = X_df.iloc[:, 0].astype(str)
        self.vectorizer.fit(texts)
        self.fitted = True
        return self

    def transform(self, x: "DashAIDataset", y=None) -> "DashAIDataset":
        """Transform text into TF-IDF weighted token columns.

        Appends one ``tfidf_<token>`` column per vocabulary term to the original
        dataset. The source text column is preserved unchanged.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset. The first column is vectorised.
        y : ignored
            Present for API compatibility.

        Returns
        -------
        DashAIDataset
            Original dataset with ``tfidf_*`` token-weight columns appended.

        Raises
        ------
        RuntimeError
            If :meth:`fit` has not been called yet.
        """
        import pyarrow as pa

        from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

        if not self.fitted:
            raise RuntimeError("The converter must be fitted before calling transform.")

        X_df = x.to_pandas()
        texts = X_df.iloc[:, 0].astype(str)

        tfidf_matrix = self.vectorizer.transform(texts)
        feature_names = self.vectorizer.get_feature_names_out()
        output_type = self.get_output_type()

        combined_table = x.arrow_table
        combined_types = dict(x.types)

        tfidf_array = tfidf_matrix.toarray()
        for i, token in enumerate(feature_names):
            prefixed = f"tfidf_{token}"
            combined_table = combined_table.append_column(
                prefixed, pa.array(tfidf_array[:, i].tolist(), type=pa.float64())
            )
            combined_types[prefixed] = output_type

        return DashAIDataset(combined_table, types=combined_types, splits=x.splits)

    def get_output_type(self, column_name: Optional[str] = None) -> DashAIDataType:
        """Return the DashAI data type produced by this converter for a column.

        The output of this converter is a set of float columns, one per
        vocabulary term, containing the TF-IDF weights produced by
        ``TfidfVectorizer``.

        Parameters
        ----------
        column_name : str, optional
            The column name to look up in the fitted vectoriser. When provided
            and the vectoriser has been fitted, the returned type reflects the
            actual fitted vocabulary. Defaults to None.

        Returns
        -------
        DashAIDataType
            A Float type for each TF-IDF weight column.
        """
        import pyarrow as pa

        return Float(arrow_type=pa.float64())

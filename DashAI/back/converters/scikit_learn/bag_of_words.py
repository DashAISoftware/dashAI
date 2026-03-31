from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class BagOfWordsConverterSchema(BaseSchema):
    """Schema for configuring the BagOfWordsConverter.

    Wraps ``sklearn.feature_extraction.text.CountVectorizer`` and exposes
    vocabulary size, casing, stop-word removal, and n-gram range as schema
    fields validated before being forwarded to the underlying scikit-learn
    estimator.
    """

    max_features: schema_field(
        int_field(gt=0),
        placeholder=1000,
        description=MultilingualString(
            en="Maximum number of features (most frequent words) to keep.",
            es=(
                "Número máximo de características (palabras más frecuentes) "
                "a conservar."
            ),
        ),
    )  # type: ignore
    lowercase: schema_field(
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en="Whether to convert all characters to lowercase before tokenizing.",
            es="Si se debe convertir todo a minúsculas antes de tokenizar.",
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
            en="Lower bound for n-grams. Must be <= upper bound.",
            es="Límite inferior de n-grams. Debe ser <= al límite superior.",
        ),
    )  # type: ignore
    upper_bound_ngrams: schema_field(
        int_field(gt=0, le=5),
        placeholder=1,
        description=MultilingualString(
            en="Upper bound for n-grams. Must be >= lower bound.",
            es="Límite superior de n-grams. Debe ser >= al límite inferior.",
        ),
    )  # type: ignore


class BagOfWordsConverter(AdvancedPreprocessingConverter, BaseConverter):
    """Convert raw text documents into a matrix of token occurrence counts.

    The Bag-of-Words (BoW) model represents each document as a fixed-length
    vector of word counts, discarding word order and grammar. During ``fit``
    a vocabulary of up to ``max_features`` terms is built from the training
    corpus. During ``transform`` each document is mapped to that vocabulary,
    producing one integer-valued column per token.

    Optional preprocessing steps include lower-casing, stop-word removal, and
    n-gram extraction (unigrams, bigrams, …). The result is a sparse integer
    matrix converted to a DashAI dataset with one column per vocabulary term.

    Internally wraps ``sklearn.feature_extraction.text.CountVectorizer``.

    The BoW representation is one of the foundational techniques in information
    retrieval described in Salton & McGill (1983) [2].

    References
    ----------
    [1] https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.CountVectorizer.html
    [2] Salton, G. & McGill, M. J. (1983). Introduction to Modern Information
        Retrieval. McGraw-Hill.
    """

    SCHEMA = BagOfWordsConverterSchema
    DISPLAY_NAME = MultilingualString(en="Bag of Words", es="Bolsa de Palabras")
    IMAGE_PREVIEW = "bag_of_words.png"
    DESCRIPTION = MultilingualString(
        en=(
            "Converts text into a Bag-of-Words representation with one column "
            "per token (frequency per token)."
        ),
        es=(
            "Convierte texto en una representación de Bolsa de Palabras con una "
            "columna por token (frecuencia por token)."
        ),
    )

    def __init__(self, **kwargs):
        """Initialise the bag-of-words converter and configure the vectorizer.

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
        from sklearn.feature_extraction.text import CountVectorizer

        self.vectorizer = CountVectorizer(
            max_features=kwargs.get("max_features", 1000),
            lowercase=kwargs.get("lowercase", True),
            stop_words=kwargs.get("stop_words", "english"),
            ngram_range=(
                kwargs.get("lower_bound_ngrams", 1),
                kwargs.get("upper_bound_ngrams", 1),
            ),
        )
        self.fitted = False

    def fit(self, x: "DashAIDataset", y=None) -> "BagOfWordsConverter":
        """Fit CountVectorizer to the input text."""
        X_df = x.to_pandas()
        texts = X_df.iloc[:, 0].astype(str)
        self.vectorizer.fit(texts)
        self.fitted = True
        return self

    def transform(self, x: "DashAIDataset", y=None) -> "DashAIDataset":
        """Transform text into Bag-of-Words frequency columns."""
        import pandas as pd

        from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset

        if not self.fitted:
            raise RuntimeError("The converter must be fitted before calling transform.")

        X_df = x.to_pandas()
        texts = X_df.iloc[:, 0].astype(str)

        bow_matrix = self.vectorizer.transform(texts)
        feature_names = self.vectorizer.get_feature_names_out()

        # One column per token (frequency)
        df_bow = pd.DataFrame(bow_matrix.toarray(), columns=feature_names)

        return to_dashai_dataset(df_bow)

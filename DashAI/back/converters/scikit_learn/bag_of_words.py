import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer

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
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)


class BagOfWordsConverterSchema(BaseSchema):
    """Schema for BagOfWordsConverter hyperparameters."""

    max_features: schema_field(
        int_field(gt=0),
        placeholder=1000,
        description="Maximum number of features (most frequent words) to keep.",
    )  # type: ignore
    lowercase: schema_field(
        bool_field(),
        placeholder=True,
        description="Whether to convert all characters to lowercase before tokenizing.",
    )  # type: ignore
    stop_words: schema_field(
        none_type(enum_field(["english"])),
        placeholder=None,
        description="Stop word set to remove. Use 'english' or None.",
    )  # type: ignore
    lower_bound_ngrams: schema_field(
        int_field(gt=0, le=5),
        placeholder=1,
        description="Lower bound for n-grams to be extracted. Must be <= upper bound.",
    )  # type: ignore
    upper_bound_ngrams: schema_field(
        int_field(gt=0, le=5),
        placeholder=1,
        description="Upper bound for n-grams to be extracted. Must be >= lower bound.",
    )  # type: ignore


class BagOfWordsConverter(AdvancedPreprocessingConverter, BaseConverter):
    """
    Converts text into a Bag-of-Words representation with one column per token
    (frequency per token).
    """

    SCHEMA = BagOfWordsConverterSchema
    DISPLAY_NAME = "Bag of Words"
    IMAGE_PREVIEW = "bag_of_words.png"
    DESCRIPTION = (
        "Converts text into a Bag-of-Words representation "
        "with one column per token (frequency per token)."
    )

    def __init__(self, **kwargs):
        super().__init__()
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

    def fit(self, x: DashAIDataset, y=None) -> "BagOfWordsConverter":
        """Fit CountVectorizer to the input text."""
        X_df = x.to_pandas()
        texts = X_df.iloc[:, 0].astype(str)
        self.vectorizer.fit(texts)
        self.fitted = True
        return self

    def transform(self, x: DashAIDataset, y=None) -> DashAIDataset:
        """Transform text into Bag-of-Words frequency columns."""
        if not self.fitted:
            raise RuntimeError("The converter must be fitted before calling transform.")

        X_df = x.to_pandas()
        texts = X_df.iloc[:, 0].astype(str)

        bow_matrix = self.vectorizer.transform(texts)
        feature_names = self.vectorizer.get_feature_names_out()

        # One column per token (frequency)
        df_bow = pd.DataFrame(bow_matrix.toarray(), columns=feature_names)

        return to_dashai_dataset(df_bow)

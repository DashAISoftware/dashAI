from sklearn.feature_extraction.text import (
    TfidfVectorizer as TfidfVectorizerOperation,
)

from DashAI.back.api.utils import cast_float_and_int_types, parse_string_to_dict, parse_string_to_list
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    bool_field,
    enum_field,
    float_field,
    int_field,
    none_type,
    schema_field,
    string_field,
    union_type,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema


class TfidfVectorizerSchema(BaseSchema):
    input: schema_field(
        enum_field(["filename", "file", "content"]),
        "content",
        "Whether the input is a filename or the content itself.",
    )  # type: ignore
    encoding: schema_field(
        string_field(),
        "utf-8",
        "The encoding of the text.",
    )  # type: ignore
    decode_error: schema_field(
        enum_field(["strict", "ignore", "replace"]),
        "strict",
        "The error handling scheme to use for decoding errors.",
    )  # type: ignore
    strip_accents: schema_field(
        none_type(enum_field(["ascii", "unicode"])),  # {‘ascii’, ‘unicode’} or callable
        None,
        "Remove accents and perform other character normalization during the preprocessing step.",
    )  # type: ignore
    lowercase: schema_field(
        bool_field(),
        True,
        "Convert all characters to lowercase before tokenizing.",
    )  # type: ignore
    # preprocessor: schema_field(
    #     none_type(string_field()), # callable
    #     None,
    #     "Override the preprocessing (string transformation) stage while preserving the tokenizing and n-grams generation steps.",
    # )  # type: ignore
    # tokenizer: schema_field(
    #     none_type(string_field()),  # callable
    #     None,
    #     "Override the string tokenization step while preserving the preprocessing and n-grams generation steps.",
    # )  # type: ignore
    analyzer: schema_field(
        enum_field(
            ["word", "char", "char_wb"]
        ),  # {‘word’, ‘char’, ‘char_wb’} or callable
        "word",
        "Whether the feature should be made of word or character n-grams.",
    )  # type: ignore
    stop_words: schema_field(
        none_type(string_field()),  # {‘english’} or list
        None,
        "If ‘english’, a built-in stop word list for English is used.",
    )  # type: ignore
    token_pattern: schema_field(
        string_field(),
        r"(?u)\b\w\w+\b",
        "Regular expression denoting what constitutes a token.",
    )  # type: ignore
    ngram_min: schema_field(
        int_field(ge=1),
        None,
        "The minimum n-gram length.",
    )  # type: ignore
    ngram_max: schema_field(
        int_field(ge=1),
        None,
        "The maximum n-gram length.",
    )  # type: ignore
    max_df: schema_field(
        union_type(
            float_field(ge=0.0, le=1.0),
            int_field(ge=1),
        ),
        1.0,
        "When building the vocabulary ignore terms that have a document frequency strictly higher than the given threshold.",
    )  # type: ignore
    min_df: schema_field(
        union_type(
            float_field(ge=0.0, le=1.0),
            int_field(ge=1),
        ),
        1,
        "When building the vocabulary ignore terms that have a document frequency strictly lower than the given threshold.",
    )  # type: ignore
    max_features: schema_field(
        none_type(int_field(ge=1)),
        None,
        "If not None, build a vocabulary that only consider the top max_features ordered by term frequency across the corpus.",
    )  # type: ignore
    vocabulary: schema_field(
        none_type(string_field()), # Mapping or iterable
        None,
        "Mapping that maps terms to feature indices.",
    )  # type: ignore
    binary: schema_field(
        bool_field(),
        False,
        "If True, all non-zero term counts are set to 1.",
    )  # type: ignore
    dtype: schema_field(
        none_type(enum_field(["np.float64", "np.float32"])),  # dtype
        "np.float64",
        "The type of the matrix returned.",
    )  # type: ignore
    norm: schema_field(
        none_type(enum_field(["l1", "l2"])),
        "l2",
        "The norm used to normalize term vectors.",
    )  # type: ignore
    use_idf: schema_field(
        bool_field(),
        True,
        "Enable inverse-document-frequency reweighting.",
    )  # type: ignore
    smooth_idf: schema_field(
        bool_field(),
        True,
        "Smooth idf weights by adding one to document frequencies, as if an extra document was seen containing every term in the collection exactly once.",
    )  # type: ignore
    sublinear_tf: schema_field(
        bool_field(),
        False,
        "Apply sublinear tf scaling, i.e., replace tf with 1 + log(tf).",
    )  # type: ignore


class TfidfVectorizer(SklearnWrapper, TfidfVectorizerOperation):
    """Scikit-learn's TfidfVectorizer wrapper for DashAI."""

    SCHEMA = TfidfVectorizerSchema
    DESCRIPTION = (
        "Convert a collection of raw documents to a matrix of TF-IDF features."
    )

    def __init__(self, **kwargs):
        self.stop_words = kwargs.pop("stop_words", None)
        if self.stop_words != None and self.stop_words != "english":
            self.stop_words = [parse_string_to_list(self.stop_words)]
        kwargs["stop_words"] = self.stop_words

        self.ngram_min = kwargs.pop("ngram_min", 1)
        self.ngram_max = kwargs.pop("ngram_max", 1)
        kwargs["ngram_range"] = (self.ngram_min, self.ngram_max)

        self.vocabulary = kwargs.pop("vocabulary", None)
        if self.vocabulary != None:
            self.vocabulary = parse_string_to_dict(self.vocabulary)
        kwargs["vocabulary"] = self.vocabulary

        self.dtype = kwargs.pop("dtype", "np.float64")
        self.dtype = cast_float_and_int_types(self.dtype)
        kwargs["dtype"] = self.dtype
        
        super().__init__(**kwargs)

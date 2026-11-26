"""The converter catalogs a notebook and a model session are offered.

A net for moving the "runs in a session" rule from the session wizard's JSX
filter to the backend (RECONCILING_FORECASTING §9.4). Both lists below were
read in the running app, not derived from the code that filters them.

``SESSION_CATALOG`` is the set of converters the session wizard's converter
catalog (``SessionConvertersRightBar``) rendered on 2026-11-18, develop
``01e8b5a03``. It was read in a RegressionTask session over the seeded
``energy`` dataset, with the JSX filter still in place, from the
``/component/image/<name>/`` of each card. The backend served 76 converters
for datasets and the catalog rendered 74: the two it hid are
``ROWS_NOT_IN_SESSIONS``. ``DateRangeConverter`` came later, with this PR,
and is offered to a notebook only.

Lives under ``tests/back/api`` to reuse the ``client`` fixture, whose registry
is the real one.
"""

SESSION_CATALOG = {
    "AdditiveChi2Sampler", "AllMiniLML6V2Embedding", "AllMpnetBaseV2Embedding",
    "BagOfWordsConverter", "Binarizer", "CharacterReplacer", "Clustering",
    "ColumnArithmetic", "ColumnConcat", "ColumnRemover", "DateFeaturesConverter",
    "DistilBERTEmbedding", "E5MistralGGUFEmbedding", "FastICA",
    "GenericUnivariateSelect", "HarrierOSS06BEmbedding", "HarrierOSS270MEmbedding",
    "ImageEmbeddingConverter", "IncrementalPCA", "InstructorLargeEmbedding",
    "KNNImputer", "LaBSEEmbedding", "LabelEncoder", "MaxAbsScaler", "MinMaxScaler",
    "MissingIndicator", "MultiQAMiniLML6CosV1Embedding",
    "MultiQAMpnetBaseCosV1Embedding", "MultilingualE5BaseEmbedding",
    "MultilingualE5LargeEmbedding", "MultilingualE5SmallEmbedding", "NanRemover",
    "Normalizer", "NumericExpansion", "Nystroem", "OneHotEncoder",
    "OpusMtDeEnTranslator", "OpusMtEnDeTranslator", "OpusMtEnEsTranslator",
    "OpusMtEnFrTranslator", "OpusMtEnRoaTranslator", "OpusMtEnZhTranslator",
    "OpusMtEsEnTranslator", "OpusMtFrEnTranslator", "OpusMtRoaEnTranslator",
    "OpusMtZhEnTranslator", "OrdinalEncoder", "PCA",
    "ParaphraseMultilingualMiniLML12V2Embedding",
    "ParaphraseMultilingualMpnetBaseV2Embedding", "PolynomialFeatures",
    "Qwen3Embedding06B", "RBFSampler", "RandomUnderSamplerConverter",
    "RegexReplacer", "RoBERTaEmbedding", "SAM3SegmentConverter", "SMOTEConverter",
    "SMOTEENNConverter", "SelectFdr", "SelectFpr", "SelectFwe", "SelectKBest",
    "SelectPercentile", "SimpleImputer", "SkewedChi2Sampler", "StandardScaler",
    "Summarizer", "TFIDFConverter", "TextCleaner", "TokenizerConverter",
    "TruncatedSVD", "TypeCast", "VarianceThreshold",
}  # fmt: skip

#: Offered to a notebook, hidden from a session: they change the row count
#: with no split to apply to.
ROWS_NOT_IN_SESSIONS = {"TimeResamplerConverter", "TimeSeriesWindowConverter"}
#: Offered to a notebook, hidden from a session: NOTEBOOK_ONLY.
NOTEBOOK_ONLY = {"DateRangeConverter"}
NOT_IN_SESSIONS = ROWS_NOT_IN_SESSIONS | NOTEBOOK_ONLY


def _converter_names(client, **params) -> list:
    response = client.get(
        "/api/v1/component/",
        params={"select_types": ["Converter"], "data_kind": "dataset", **params},
    )
    assert response.status_code == 200, response.text
    return sorted(component["name"] for component in response.json())


def test_the_catalog_without_in_session_is_every_dataset_converter(client):
    """R1: a caller that does not ask for the session catalog sees all of them."""
    assert _converter_names(client) == sorted(SESSION_CATALOG | NOT_IN_SESSIONS)


def test_the_session_catalog_is_what_the_wizard_showed(client):
    """R2: moving the filter to the backend leaves the session list as it was."""
    assert _converter_names(client, in_session=True) == sorted(SESSION_CATALOG)


def test_the_two_rules_of_what_runs_in_a_session_stay_one(client):
    """Guard: the row rule and the notebook-only rule are two reasons for one
    predicate. Touching either must not let the converters the other keeps
    out back into a session, neither in the catalog nor in the structure."""
    from DashAI.back.preprocessing.column_ref import ConverterStep, RawColumnRef
    from DashAI.back.preprocessing.structure import infer_structure
    from tests.back.api.test_date_range_converter_acceptance import (
        load_dataset_types,
    )

    offered = set(_converter_names(client, in_session=True))
    assert not NOT_IN_SESSIONS & offered
    assert {"NanRemover", "SMOTEConverter"} <= offered

    registry = client.app.container["component_registry"]
    for name in sorted(NOT_IN_SESSIONS):
        result = infer_structure(
            dataset_types=load_dataset_types(),
            candidates=["a", "b"],
            target=[],
            steps=[ConverterStep(converter=name, scope=[RawColumnRef(name="a")])],
            component_registry=registry,
        )
        assert result.steps[0].error is not None, name
        assert result.steps[0].error.code in ("rows_not_supported", "notebook_only")

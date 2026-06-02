from typing import Dict

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense._sentence_transformer_embedding import (
    _SentenceTransformerEmbedding,
)
from DashAI.back.models.RAG.retrievers.dense._hf_metadata_utils import (
    build_retriever_metadata,
)
from DashAI.back.models.RAG.retrievers.dense.huggingface_dense_retriever import (
    METRICS,
    HuggingFaceDenseRetriever,
)

TRUNCATE = "truncate"
AGGREGATE = "aggregate"

ST_MODELS: Dict[str, dict] = {
    "sentence-transformers/all-MiniLM-L6-v2": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "sentence-transformers/all-MiniLM-L12-v2": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "sentence-transformers/all-mpnet-base-v2": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "sentence-transformers/all-distilroberta-v1": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "sentence-transformers/multi-qa-mpnet-base-dot-v1": {
        "languages": ["en"],
        "max_seq_length": 512,
        "normalize_default": False,
    },
    "sentence-transformers/multi-qa-mpnet-base-cos-v1": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "sentence-transformers/multi-qa-distilbert-dot-v1": {
        "languages": ["en"],
        "max_seq_length": 512,
        "normalize_default": False,
    },
    "sentence-transformers/multi-qa-distilbert-cos-v1": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "sentence-transformers/multi-qa-MiniLM-L6-dot-v1": {
        "languages": ["en"],
        "max_seq_length": 512,
        "normalize_default": False,
    },
    "sentence-transformers/multi-qa-MiniLM-L6-cos-v1": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "sentence-transformers/msmarco-bert-base-dot-v5": {
        "languages": ["en"],
        "max_seq_length": 512,
        "normalize_default": False,
    },
    "sentence-transformers/msmarco-distilbert-dot-v5": {
        "languages": ["en"],
        "max_seq_length": 512,
        "normalize_default": False,
    },
    "sentence-transformers/msmarco-distilbert-base-tas-b": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "sentence-transformers/msmarco-distilbert-cos-v5": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "sentence-transformers/msmarco-MiniLM-L12-cos-v5": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "sentence-transformers/msmarco-MiniLM-L6-cos-v5": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
        "max_seq_length": 512,
    },
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
        "max_seq_length": 512,
    },
    "sentence-transformers/distiluse-base-multilingual-cased-v2": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
        "max_seq_length": 512,
    },
    "sentence-transformers/distiluse-base-multilingual-cased-v1": {
        "languages": [
            "en", "es", "fr", "de", "it", "nl", "pt", "ar", "zh", "ja",
            "ko", "pl", "ru", "tr", "multi",
        ],
        "max_seq_length": 512,
    },
    "sentence-transformers/allenai-specter": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
}

ST_MODEL_NAMES = list(ST_MODELS.keys())


class SentenceTransformerDenseRetrieverSchema(BaseSchema):
    model_name: schema_field(
        enum_field(ST_MODEL_NAMES),
        placeholder="sentence-transformers/all-MiniLM-L6-v2",
        description=MultilingualString(
            en="Sentence Transformer model for embedding generation.",
            es="Modelo Sentence Transformer para generación de embeddings.",
        ),
    )  # type: ignore

    overflow_strategy: schema_field(
        enum_field([TRUNCATE, AGGREGATE]),
        placeholder=TRUNCATE,
        description=MultilingualString(
            en="Strategy for chunks exceeding model max sequence length.",
            es="Estrategia para fragmentos que exceden la longitud máxima del modelo.",
        ),
    )  # type: ignore

    normalize: schema_field(
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en="Whether to L2-normalize the output embeddings.",
            es="Si normalizar con L2 los embeddings de salida.",
        ),
    )  # type: ignore

    device: schema_field(
        enum_field(["cpu", "cuda"]),
        placeholder="cpu",
        description=MultilingualString(
            en="Device to run the model on.",
            es="Dispositivo para ejecutar el modelo.",
        ),
    )  # type: ignore

    similarity_metric: schema_field(
        enum_field(enum=METRICS),
        placeholder="cosine",
        description=MultilingualString(
            en="Distance metric for comparing dense vectors.",
            es="Métrica de distancia para comparar vectores densos.",
        ),
    )  # type: ignore

    top_k: schema_field(
        int_field(gt=0),
        placeholder=5,
        description=MultilingualString(
            en="Number of chunks to select.",
            es="Número de fragmentos a seleccionar.",
        ),
    )  # type: ignore


class SentenceTransformerDenseRetriever(HuggingFaceDenseRetriever):
    FLAGS: list[str] = []
    SCHEMA = SentenceTransformerDenseRetrieverSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Sentence Transformers",
        es="Sentence Transformers",
    )
    DESCRIPTION: str = MultilingualString(
        en="Dense retriever using Sentence Transformer embeddings (mean pooling + L2 normalization).",
        es="Recuperador denso que usa embeddings Sentence Transformer (mean pooling + normalización L2).",
    )

    @classmethod
    def get_metadata(cls):
        return build_retriever_metadata(ST_MODELS, "SentenceTransformers", len(ST_MODEL_NAMES))

    def _create_embedding(self) -> _SentenceTransformerEmbedding:
        model_name = self.params.pop("model_name")
        device = self.params.pop("device")
        overflow_strategy = self.params.pop("overflow_strategy")
        normalize = self.params.pop("normalize")
        model_info = ST_MODELS[model_name]
        return _SentenceTransformerEmbedding(
            model_name=model_name,
            device=device,
            model_max_length=model_info["max_seq_length"],
            overflow_strategy=overflow_strategy,
            normalize=normalize if model_info.get("normalize_default", True) else normalize,
        )

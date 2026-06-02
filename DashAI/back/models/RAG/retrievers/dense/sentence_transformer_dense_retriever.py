from typing import Dict

from DashAI.back.core.schema_fields import (
    BaseSchema,
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

ST_MODELS: Dict[str, dict] = {
    "sentence-transformers/all-MiniLM-L6-v2": {
        "languages": ["en"],
    },
    "sentence-transformers/all-mpnet-base-v2": {
        "languages": ["en"],
    },
    "sentence-transformers/multi-qa-mpnet-base-dot-v1": {
        "languages": ["en"],
    },
    "sentence-transformers/all-distilroberta-v1": {
        "languages": ["en"],
    },
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
    },
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
    },
    "sentence-transformers/distiluse-base-multilingual-cased-v2": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
    },
    "sentence-transformers/distiluse-base-multilingual-cased-v1": {
        "languages": [
            "en", "es", "fr", "de", "it", "nl", "pt", "ar", "zh", "ja",
            "ko", "pl", "ru", "tr", "multi",
        ],
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

    max_length: schema_field(
        int_field(ge=1),
        placeholder=512,
        description=MultilingualString(
            en="Maximum sequence length for tokenization.",
            es="Longitud máxima de secuencia para tokenización.",
        ),
    )  # type: ignore

    batch_size: schema_field(
        int_field(ge=1),
        placeholder=32,
        description=MultilingualString(
            en="Number of samples to process at once.",
            es="Número de muestras a procesar a la vez.",
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
        max_length = self.params.pop("max_length")
        self.params.pop("batch_size")
        return _SentenceTransformerEmbedding(
            model_name=model_name,
            device=device,
            max_length=max_length,
        )

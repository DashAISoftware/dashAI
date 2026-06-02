from typing import Dict

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense._e5_embedding import _E5Embedding
from DashAI.back.models.RAG.retrievers.dense._hf_metadata_utils import (
    build_retriever_metadata,
)
from DashAI.back.models.RAG.retrievers.dense.huggingface_dense_retriever import (
    METRICS,
    HuggingFaceDenseRetriever,
)

E5_MODELS: Dict[str, dict] = {
    "intfloat/e5-small-v2": {
        "languages": ["en"],
    },
    "intfloat/e5-large-v2": {
        "languages": ["en"],
    },
    "intfloat/multilingual-e5-large": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
    },
    "intfloat/multilingual-e5-base": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
    },
    "intfloat/multilingual-e5-small": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
    },
}

E5_MODEL_NAMES = list(E5_MODELS.keys())


class E5DenseRetrieverSchema(BaseSchema):
    model_name: schema_field(
        enum_field(E5_MODEL_NAMES),
        placeholder="intfloat/e5-small-v2",
        description=MultilingualString(
            en="E5 model for embedding generation (uses query/passage prefixes).",
            es="Modelo E5 para generación de embeddings (usa prefijos query/passage).",
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


class E5DenseRetriever(HuggingFaceDenseRetriever):
    FLAGS: list[str] = []
    SCHEMA = E5DenseRetrieverSchema
    DISPLAY_NAME: str = MultilingualString(
        en="E5 Embedding Retriever",
        es="Recuperador por Embeddings E5",
    )
    DESCRIPTION: str = MultilingualString(
        en="Dense retriever using E5 embeddings with average pooling + L2 normalization + query/passage prefixes.",
        es="Recuperador denso que usa embeddings E5 con average pooling + normalización L2 + prefijos query/passage.",
    )

    @classmethod
    def get_metadata(cls):
        return build_retriever_metadata(E5_MODELS, "E5", len(E5_MODEL_NAMES))

    def _create_embedding(self) -> _E5Embedding:
        model_name = self.params.pop("model_name")
        device = self.params.pop("device")
        max_length = self.params.pop("max_length")
        self.params.pop("batch_size")
        return _E5Embedding(
            model_name=model_name,
            device=device,
            max_length=max_length,
        )

from typing import Dict, List

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense._e5_embedding import _E5Embedding
from DashAI.back.models.RAG.embeddings.dense._overflow_handler import (
    AGGREGATE,
    TRUNCATE,
)
from DashAI.back.models.RAG.embeddings.dense_embedding import DenseEmbedding

E5_MODELS: Dict[str, dict] = {
    "intfloat/e5-small-v2": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "intfloat/e5-large-v2": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "intfloat/multilingual-e5-large": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
        "max_seq_length": 512,
    },
    "intfloat/multilingual-e5-base": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
        "max_seq_length": 512,
    },
    "intfloat/multilingual-e5-small": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
        "max_seq_length": 512,
    },
    "intfloat/e5-mistral-7b-instruct": {
        "languages": ["en"],
        "max_seq_length": 4096,
    },
}

E5_MODEL_NAMES = list(E5_MODELS.keys())


class E5EmbeddingSchema(BaseSchema):
    model_name: schema_field(
        enum_field(E5_MODEL_NAMES),
        placeholder="intfloat/e5-small-v2",
        description=MultilingualString(
            en="E5 model for embedding generation (uses query/passage prefixes).",
            es="Modelo E5 para generación de embeddings (usa prefijos query/passage).",
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

    device: schema_field(
        enum_field(["cpu", "cuda"]),
        placeholder="cpu",
        description=MultilingualString(
            en="Device to run the model on.",
            es="Dispositivo para ejecutar el modelo.",
        ),
    )  # type: ignore


class E5Embedding(DenseEmbedding):
    SCHEMA = E5EmbeddingSchema
    FLAGS: list[str] = ["FAMILY:e5", "huggingface"]
    DISPLAY_NAME: str = MultilingualString(
        en="E5 Embedding",
        es="Embedding E5",
    )
    DESCRIPTION: str = MultilingualString(
        en="Dense embeddings using E5 models with average pooling + L2 normalization + query/passage prefixes.",
        es="Embeddings densos usando modelos E5 con average pooling + normalización L2 + prefijos query/passage.",
    )

    def __init__(self, **kwargs):
        self.params = self.validate_and_transform(kwargs)
        model_name = self.params["model_name"]
        device = self.params["device"]
        overflow_strategy = self.params.get("overflow_strategy", "truncate")
        model_info = E5_MODELS[model_name]
        self._embedding = _E5Embedding(
            model_name=model_name,
            device=device,
            model_max_length=model_info["max_seq_length"],
            overflow_strategy=overflow_strategy,
        )

    def load(self):
        self._embedding.load()

    def encode(self, text: str):
        return self._embedding.encode(text)

    def batch_encode(self, texts: List[str]):
        return self._embedding.batch_encode(texts)

    def save(self):
        pass

    def train(self, **kwargs):
        return

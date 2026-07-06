from typing import Dict, List

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense._overflow_handler import (
    AGGREGATE,
    TRUNCATE,
)
from DashAI.back.models.RAG.embeddings.dense._sentence_transformer_embedding import (
    _SentenceTransformerEmbedding,
)
from DashAI.back.models.RAG.embeddings.dense_embedding import DenseEmbedding

LABSE_MODELS: Dict[str, dict] = {
    "sentence-transformers/LaBSE": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "gu", "ka", "ku", "my", "sq", "multi",
        ],
        "max_seq_length": 512,
    },
}

LABSE_MODEL_NAMES = list(LABSE_MODELS.keys())


class LaBSEmbeddingSchema(BaseSchema):
    model_name: schema_field(
        enum_field(LABSE_MODEL_NAMES),
        placeholder="sentence-transformers/LaBSE",
        description=MultilingualString(
            en="LaBSE model for multilingual embedding generation (109 languages).",
            es="Modelo LaBSE para generación de embeddings multilingües (109 idiomas).",
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


class LaBSEmbedding(DenseEmbedding):
    SCHEMA = LaBSEmbeddingSchema
    FLAGS: list[str] = ["FAMILY:labse", "huggingface"]
    DISPLAY_NAME: str = MultilingualString(
        en="LaBSE Embedding",
        es="Embedding LaBSE",
    )
    DESCRIPTION: str = MultilingualString(
        en="Dense embeddings using LaBSE multilingual model (109 languages).",
        es="Embeddings densos usando el modelo multilingüe LaBSE (109 idiomas).",
    )

    def __init__(self, **kwargs):
        self.params = self.validate_and_transform(kwargs)
        model_name = self.params["model_name"]
        device = self.params["device"]
        overflow_strategy = self.params.get("overflow_strategy", "truncate")
        model_info = LABSE_MODELS[model_name]
        self._embedding = _SentenceTransformerEmbedding(
            model_name=model_name,
            device=device,
            model_max_length=model_info["max_seq_length"],
            overflow_strategy=overflow_strategy,
            normalize=True,
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

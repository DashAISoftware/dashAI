from typing import Dict, List

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense._bert_embedding import (
    CLS,
    CONCAT_2,
    CONCAT_3,
    CONCAT_4,
    MAX,
    MEAN,
    _BERTEmbedding,
)
from DashAI.back.models.RAG.embeddings.dense._overflow_handler import (
    AGGREGATE,
    TRUNCATE,
)
from DashAI.back.models.RAG.embeddings.dense_embedding import DenseEmbedding

DISTILBERT_POOLING_STRATEGIES = [CLS, MEAN, MAX, CONCAT_2, CONCAT_3, CONCAT_4]

DISTILBERT_MODELS: Dict[str, dict] = {
    "distilbert/distilbert-base-cased": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "distilbert/distilbert-base-uncased": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "distilbert/distilbert-base-multilingual-cased": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
        "max_seq_length": 512,
    },
    "distilbert/distilbert-roberta-base": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
}

DISTILBERT_MODEL_NAMES = list(DISTILBERT_MODELS.keys())


class DistilBERTEmbeddingSchema(BaseSchema):
    model_name: schema_field(
        enum_field(DISTILBERT_MODEL_NAMES),
        placeholder="distilbert/distilbert-base-cased",
        description=MultilingualString(
            en="DistilBERT model for embedding generation.",
            es="Modelo DistilBERT para generación de embeddings.",
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

    pooling_strategy: schema_field(
        enum_field(DISTILBERT_POOLING_STRATEGIES),
        placeholder=MEAN,
        description=MultilingualString(
            en="Pooling strategy to aggregate token embeddings.",
            es="Estrategia de pooling para agregar embeddings de tokens.",
        ),
    )  # type: ignore


class DistilBERTEmbedding(DenseEmbedding):
    SCHEMA = DistilBERTEmbeddingSchema
    FLAGS: list[str] = ["FAMILY:distilbert", "huggingface"]
    DISPLAY_NAME: str = MultilingualString(
        en="DistilBERT Embedding",
        es="Embedding DistilBERT",
    )
    DESCRIPTION: str = MultilingualString(
        en="Dense embeddings using DistilBERT models with configurable pooling.",
        es="Embeddings densos usando modelos DistilBERT con pooling configurable.",
    )

    def __init__(self, **kwargs):
        self.params = self.validate_and_transform(kwargs)
        model_name = self.params["model_name"]
        device = self.params["device"]
        overflow_strategy = self.params.get("overflow_strategy", "truncate")
        pooling_strategy = self.params["pooling_strategy"]
        model_info = DISTILBERT_MODELS[model_name]
        self._embedding = _BERTEmbedding(
            model_name=model_name,
            device=device,
            model_max_length=model_info["max_seq_length"],
            overflow_strategy=overflow_strategy,
            pooling_strategy=pooling_strategy,
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

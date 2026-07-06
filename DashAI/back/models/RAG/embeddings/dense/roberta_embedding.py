from typing import Dict, List

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense._bert_embedding import (
    MAX,
    MEAN,
    _BERTEmbedding,
)
from DashAI.back.models.RAG.embeddings.dense._overflow_handler import (
    AGGREGATE,
    TRUNCATE,
)
from DashAI.back.models.RAG.embeddings.dense_embedding import DenseEmbedding

ROBERTA_POOLING_STRATEGIES = [MEAN, MAX]

ROBERTA_MODELS: Dict[str, dict] = {
    "FacebookAI/roberta-base": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "FacebookAI/roberta-large": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "FacebookAI/xlm-roberta-base": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
        "max_seq_length": 512,
    },
    "FacebookAI/xlm-roberta-large": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
        "max_seq_length": 512,
    },
}

ROBERTA_MODEL_NAMES = list(ROBERTA_MODELS.keys())


class RoBERTaEmbeddingSchema(BaseSchema):
    model_name: schema_field(
        enum_field(ROBERTA_MODEL_NAMES),
        placeholder="FacebookAI/roberta-base",
        description=MultilingualString(
            en="RoBERTa / XLM-RoBERTa model for embedding generation.",
            es="Modelo RoBERTa / XLM-RoBERTa para generación de embeddings.",
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
        enum_field(ROBERTA_POOLING_STRATEGIES),
        placeholder=MEAN,
        description=MultilingualString(
            en="Pooling strategy to aggregate token embeddings. RoBERTa CLS token is not trained for similarity.",
            es="Estrategia de pooling para agregar embeddings de tokens. El token CLS de RoBERTa no está entrenado para similitud.",
        ),
    )  # type: ignore


class RoBERTaEmbedding(DenseEmbedding):
    SCHEMA = RoBERTaEmbeddingSchema
    FLAGS: list[str] = ["FAMILY:roberta", "huggingface"]
    DISPLAY_NAME: str = MultilingualString(
        en="RoBERTa Embedding",
        es="Embedding RoBERTa",
    )
    DESCRIPTION: str = MultilingualString(
        en="Dense embeddings using RoBERTa / XLM-RoBERTa models with mean/max pooling.",
        es="Embeddings densos usando modelos RoBERTa / XLM-RoBERTa con pooling mean/max.",
    )

    def __init__(self, **kwargs):
        self.params = self.validate_and_transform(kwargs)
        model_name = self.params["model_name"]
        device = self.params["device"]
        overflow_strategy = self.params.get("overflow_strategy", "truncate")
        pooling_strategy = self.params["pooling_strategy"]
        model_info = ROBERTA_MODELS[model_name]
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

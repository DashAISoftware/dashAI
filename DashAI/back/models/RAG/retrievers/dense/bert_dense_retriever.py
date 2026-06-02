from typing import Dict

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
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
from DashAI.back.models.RAG.retrievers.dense._hf_metadata_utils import (
    build_retriever_metadata,
)
from DashAI.back.models.RAG.retrievers.dense.huggingface_dense_retriever import (
    METRICS,
    HuggingFaceDenseRetriever,
)

BERT_POOLING_STRATEGIES = [CLS, MEAN, MAX, CONCAT_2, CONCAT_3, CONCAT_4]

BERT_MODELS: Dict[str, dict] = {
    "google-bert/bert-base-cased": {
        "languages": ["en"],
    },
    "google-bert/bert-base-uncased": {
        "languages": ["en"],
    },
    "google-bert/bert-large-cased": {
        "languages": ["en"],
    },
    "google-bert/bert-large-uncased": {
        "languages": ["en"],
    },
    "google-bert/bert-base-multilingual-cased": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
    },
    "google-bert/bert-base-multilingual-uncased": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
    },
}

BERT_MODEL_NAMES = list(BERT_MODELS.keys())


class BERTDenseRetrieverSchema(BaseSchema):
    model_name: schema_field(
        enum_field(BERT_MODEL_NAMES),
        placeholder="google-bert/bert-base-cased",
        description=MultilingualString(
            en="BERT model for embedding generation.",
            es="Modelo BERT para generación de embeddings.",
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

    pooling_strategy: schema_field(
        enum_field(BERT_POOLING_STRATEGIES),
        placeholder=MEAN,
        description=MultilingualString(
            en="Pooling strategy to aggregate token embeddings.",
            es="Estrategia de pooling para agregar embeddings de tokens.",
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


class BERTDenseRetriever(HuggingFaceDenseRetriever):
    FLAGS: list[str] = []
    SCHEMA = BERTDenseRetrieverSchema
    DISPLAY_NAME: str = MultilingualString(
        en="BERT Embedding Retriever",
        es="Recuperador por Embeddings BERT",
    )
    DESCRIPTION: str = MultilingualString(
        en="Dense retriever using BERT embeddings with configurable pooling (CLS, mean, max, concat layers).",
        es="Recuperador denso que usa embeddings BERT con pooling configurable (CLS, mean, max, concat layers).",
    )

    @classmethod
    def get_metadata(cls):
        return build_retriever_metadata(BERT_MODELS, "BERT", len(BERT_MODEL_NAMES))

    def _create_embedding(self) -> _BERTEmbedding:
        model_name = self.params.pop("model_name")
        device = self.params.pop("device")
        max_length = self.params.pop("max_length")
        pooling_strategy = self.params.pop("pooling_strategy")
        self.params.pop("batch_size")
        return _BERTEmbedding(
            model_name=model_name,
            device=device,
            max_length=max_length,
            pooling_strategy=pooling_strategy,
        )

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

TRUNCATE = "truncate"
AGGREGATE = "aggregate"

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


class LaBSEDenseRetrieverSchema(BaseSchema):
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


class LaBSEDenseRetriever(HuggingFaceDenseRetriever):
    FLAGS: list[str] = []
    SCHEMA = LaBSEDenseRetrieverSchema
    DISPLAY_NAME: str = MultilingualString(
        en="LaBSE Embedding Retriever",
        es="Recuperador por Embeddings LaBSE",
    )
    DESCRIPTION: str = MultilingualString(
        en="Dense retriever using LaBSE multilingual embeddings (109 languages).",
        es="Recuperador denso que usa embeddings multilingües LaBSE (109 idiomas).",
    )

    @classmethod
    def get_metadata(cls):
        return build_retriever_metadata(LABSE_MODELS, "LaBSE", len(LABSE_MODEL_NAMES))

    def _create_embedding(self) -> _SentenceTransformerEmbedding:
        model_name = self.params.pop("model_name")
        device = self.params.pop("device")
        overflow_strategy = self.params.pop("overflow_strategy")
        model_info = LABSE_MODELS[model_name]
        return _SentenceTransformerEmbedding(
            model_name=model_name,
            device=device,
            model_max_length=model_info["max_seq_length"],
            overflow_strategy=overflow_strategy,
            normalize=True,
        )

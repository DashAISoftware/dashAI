from typing import Dict

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    schema_field,
    string_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense._instructor_embedding import (
    _InstructorEmbedding,
)
from DashAI.back.models.RAG.retrievers.dense._hf_metadata_utils import (
    build_retriever_metadata,
)
from DashAI.back.models.RAG.retrievers.dense.huggingface_dense_retriever import (
    METRICS,
    HuggingFaceDenseRetriever,
)

INSTRUCTOR_MODELS: Dict[str, dict] = {
    "hkunlp/instructor-base": {
        "languages": ["en"],
    },
    "hkunlp/instructor-large": {
        "languages": ["en"],
    },
    "hkunlp/instructor-xl": {
        "languages": ["en"],
    },
}

INSTRUCTOR_MODEL_NAMES = list(INSTRUCTOR_MODELS.keys())


class InstructorDenseRetrieverSchema(BaseSchema):
    model_name: schema_field(
        enum_field(INSTRUCTOR_MODEL_NAMES),
        placeholder="hkunlp/instructor-base",
        description=MultilingualString(
            en="INSTRUCTOR model for instruction-tuned embedding generation.",
            es="Modelo INSTRUCTOR para generación de embeddings ajustados por instrucción.",
        ),
    )  # type: ignore

    instruction: schema_field(
        string_field(),
        placeholder="Represent the document for retrieval:",
        description=MultilingualString(
            en="Instruction text that guides the embedding model.",
            es="Texto de instrucción que guía al modelo de embedding.",
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


class InstructorDenseRetriever(HuggingFaceDenseRetriever):
    FLAGS: list[str] = []
    SCHEMA = InstructorDenseRetrieverSchema
    DISPLAY_NAME: str = MultilingualString(
        en="INSTRUCTOR Embedding Retriever",
        es="Recuperador por Embeddings INSTRUCTOR",
    )
    DESCRIPTION: str = MultilingualString(
        en="Dense retriever using INSTRUCTOR instruction-tuned embeddings.",
        es="Recuperador denso que usa embeddings INSTRUCTOR ajustados por instrucción.",
    )

    @classmethod
    def get_metadata(cls):
        return build_retriever_metadata(INSTRUCTOR_MODELS, "INSTRUCTOR", len(INSTRUCTOR_MODEL_NAMES))

    def _create_embedding(self) -> _InstructorEmbedding:
        model_name = self.params.pop("model_name")
        device = self.params.pop("device")
        instruction = self.params.pop("instruction")
        return _InstructorEmbedding(
            model_name=model_name,
            device=device,
            instruction=instruction,
        )

from typing import Dict, List

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    schema_field,
    string_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense._instructor_embedding import (
    _InstructorEmbedding,
)
from DashAI.back.models.RAG.embeddings.dense_embedding import DenseEmbedding

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


class InstructorEmbeddingSchema(BaseSchema):
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


class InstructorEmbedding(DenseEmbedding):
    SCHEMA = InstructorEmbeddingSchema
    FLAGS: list[str] = ["FAMILY:instructor", "huggingface"]
    DISPLAY_NAME: str = MultilingualString(
        en="INSTRUCTOR Embedding",
        es="Embedding INSTRUCTOR",
    )
    DESCRIPTION: str = MultilingualString(
        en="Dense embeddings using INSTRUCTOR instruction-tuned models.",
        es="Embeddings densos usando modelos INSTRUCTOR ajustados por instrucción.",
    )

    def __init__(self, **kwargs):
        self.params = self.validate_and_transform(kwargs)
        model_name = self.params["model_name"]
        device = self.params["device"]
        instruction = self.params["instruction"]
        self._embedding = _InstructorEmbedding(
            model_name=model_name,
            device=device,
            instruction=instruction,
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

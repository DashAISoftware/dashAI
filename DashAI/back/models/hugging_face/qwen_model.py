from typing import Any
from llama_cpp import Llama

from DashAI.back.core.schema_fields import (
    BaseSchema,
    int_field,
    schema_field,
)
from DashAI.back.models.base_generative_model import BaseGenerativeModel


class LLMGenerationSchema(BaseSchema):
    """Schema for Llama text generation model."""

    max_tokens: schema_field(
        int_field(ge=1),
        placeholder=100,
        description="Maximum number of tokens to generate.",
    )  # type: ignore


class QwenModel(BaseGenerativeModel):
    """Llama model for text generation using llama.cpp library."""

    SCHEMA = LLMGenerationSchema

    def __init__(self, **kwargs):
        kwargs = self.validate_and_transform(kwargs)
        self.model_id = "Qwen/Qwen2-0.5B-Instruct-GGUF"  # Repositorio de Hugging Face
        self.filename = "*q8_0.gguf"  # Archivo del modelo
        self.max_tokens = kwargs.pop("max_tokens", 100)

        # Descargar y cargar el modelo desde Hugging Face
        self.model = Llama.from_pretrained(
            repo_id=self.model_id, filename=self.filename, verbose=True
        )

    def generate(self, prompt: str) -> str:
        """Generate text based on prompts."""
        output = self.model(
            f"Q: {prompt} A:", max_tokens=self.max_tokens, stop=["\n", "Q:"], echo=True
        )
        return output["choices"][0]["text"]
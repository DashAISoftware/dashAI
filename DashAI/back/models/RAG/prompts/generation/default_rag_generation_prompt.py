from typing import Any

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    schema_field,
    string_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.prompts.generation.rag_generation_prompt import (
    RAGGenerationPrompt,
)

TEMPLATES = {
    "en": (
        "You are a helpful AI assistant with access to a set of retrieved "
        "documents.\n"
        "Use the documents below to support your answer. Prioritize "
        "information from the documents over your own knowledge. "
        "If the documents do not contain relevant information, say so "
        "clearly rather than guessing.\n"
        "\n"
        "User message:\n"
        "{input}\n"
        "\n"
        "Retrieved documents:\n"
        "{chunks}\n"
        "\n"
        "Answer the user's message based on the documents above."
    ),
    "es": (
        "Eres un asistente de IA con acceso a un conjunto de documentos "
        "recuperados.\n"
        "Usa los documentos a continuación para fundamentar tu respuesta. "
        "Prioriza la información de los documentos sobre tu propio "
        "conocimiento. Si los documentos no contienen información relevante, "
        "indícalo claramente en lugar de adivinar.\n"
        "\n"
        "Mensaje del usuario:\n"
        "{input}\n"
        "\n"
        "Documentos recuperados:\n"
        "{chunks}\n"
        "\n"
        "Responde al mensaje del usuario basándote en los documentos "
        "anteriores."
    ),
    "pt": (
        "Você é um assistente de IA com acesso a um conjunto de documentos "
        "recuperados.\n"
        "Use os documentos abaixo para fundamentar sua resposta. Priorize "
        "as informações dos documentos sobre seu próprio conhecimento. Se "
        "os documentos não contiverem informações relevantes, indique isso "
        "claramente em vez de adivinhar.\n"
        "\n"
        "Mensagem do usuário:\n"
        "{input}\n"
        "\n"
        "Documentos recuperados:\n"
        "{chunks}\n"
        "\n"
        "Responda à mensagem do usuário com base nos documentos acima."
    ),
}


class DefaultRAGGenerationPromptSchema(BaseSchema):
    language: schema_field(
        enum_field(enum=["en", "es", "pt"]),
        placeholder="en",
        description=MultilingualString(
            en="Language for the generated response.",
            es="Idioma de la respuesta generada.",
            pt="Idioma da resposta gerada.",
        ),
    )
    template: schema_field(
        string_field(),
        placeholder="",
        description="The prompt template with placeholders.",
    )


class DefaultRAGGenerationPrompt(RAGGenerationPrompt):
    """
    Default prompt template used in the language generation step of RAG.
    """

    SCHEMA = DefaultRAGGenerationPromptSchema
    DESCRIPTION: str = MultilingualString(
        en="Default prompt template used in the language generation step of RAG.",
        es="Plantilla de prompt predeterminada utilizada en el paso de generación de lenguaje de RAG.",
        pt="Modelo de prompt padrão usado na etapa de geração de linguagem do RAG.",
    )
    DISPLAY_NAME: str = MultilingualString(
        en="Default RAG Generation Prompt",
        es="Prompt de Generación RAG Predeterminado",
        pt="Prompt de Geração RAG Padrão",
    )

    metadata = {
        "name": "Default RAG Generation Prompt",
        "description": "Default prompt template used in the language generation step of RAG.",
        "type": "generation",
        "required_placeholders": RAGGenerationPrompt.required_placeholders,
        "optional_placeholders": RAGGenerationPrompt.optional_placeholders,
        "placeholder_descriptions": {
            "{input}": "The user input message.",
            "{chunks}": "The document chunks to be included in the context.",
        },
        "templates": TEMPLATES,
    }

    required_placeholders = ["{input}", "{chunks}"]
    optional_placeholders = []

    def __init__(self, **kwargs):
        self.language = kwargs.pop("language")
        self.template = kwargs.pop("template") or TEMPLATES.get(self.language, "")

    def format(self, input: str, chunks: str, **kwargs: Any) -> str:
        buffer = self.template
        buffer = buffer.replace("{input}", input)
        buffer = buffer.replace("{chunks}", chunks)
        return buffer

"""Default LLM filter evaluation prompt."""

from __future__ import annotations

from typing import Any

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    schema_field,
    string_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.exceptions import RAGPromptTemplateError
from DashAI.back.models.RAG.prompts.evaluation.llm_filter_prompt import (
    LLMFilterPrompt,
)

TEMPLATES = {
    "en": (
        "You are a retrieval result filter for a Retrieval-Augmented Generation "
        "system. From the numbered candidate chunks, select the best ones for "
        "answering the user message.\n"
        "\n"
        "User message:\n"
        "{input}\n"
        "\n"
        "Documents: {documents.names}\n"
        "\n"
        "Document description: {documents.description}\n"
        "\n"
        "Candidate chunks (each line shows its [number], document_id, position "
        "and text):\n"
        "{chunks}\n"
        "\n"
        "Select at most {topk} best chunks, best first.\n"
        "\n"
        "Respond by calling the function select_best_chunks with a single "
        "JSON object with this shape:\n"
        '{"selected_chunks": [<1-based candidate numbers>], '
        '"message": "<optional short user-facing sentence>", '
        '"justification": "<optional short rationale>"}\n'
        "\n"
        '- "selected_chunks" is required: 1-based indices into the numbered '
        "candidate list above, best first, unique, at most {topk} entries.\n"
        '- "message" is optional: one short user-facing sentence in the same '
        "language as this prompt describing what you selected.\n"
        '- "justification" is optional: one short sentence in the same language '
        "as this prompt explaining your selection.\n"
        "\n"
        "Invalid selections are rejected and must be retried: every selected "
        "index must be unique, in-range and at most {topk}, or the whole "
        "selection is rejected. Only select numbers that appear in the "
        "candidate list. Respond with ONLY one JSON object, with no markdown "
        "fences and no extra text."
    ),
    "es": (
        "Eres un filtro de resultados de recuperación para un sistema de "
        "Generación Aumentada por Recuperación. De los fragmentos candidatos "
        "numerados, selecciona los mejores para responder al mensaje del "
        "usuario.\n"
        "\n"
        "Mensaje del usuario:\n"
        "{input}\n"
        "\n"
        "Documentos: {documents.names}\n"
        "\n"
        "Descripción de los documentos: {documents.description}\n"
        "\n"
        "Fragmentos candidatos (cada línea muestra su [número], document_id, "
        "posición y texto):\n"
        "{chunks}\n"
        "\n"
        "Selecciona como máximo {topk} de los mejores fragmentos, los mejores "
        "primero.\n"
        "\n"
        "Responde llamando a la función select_best_chunks con un único "
        "objeto JSON con esta forma:\n"
        '{"selected_chunks": [<números de candidato basados en 1>], '
        '"message": "<frase breve opcional para el usuario>", '
        '"justification": "<justificación breve opcional>"}\n'
        "\n"
        '- "selected_chunks" es obligatorio: índices basados en 1 en la lista '
        "numerada de candidatos anterior, los mejores primero, únicos, como "
        "máximo {topk} entradas.\n"
        '- "message" es opcional: una frase breve para el usuario en el mismo '
        "idioma de este prompt describiendo lo que seleccionaste.\n"
        '- "justification" es opcional: una frase breve en el mismo idioma de '
        "este prompt explicando tu selección.\n"
        "\n"
        "Las selecciones inválidas se rechazan y deben reintentarse: cada "
        "índice seleccionado debe ser único, estar dentro del rango y ser como "
        "máximo {topk}, o se rechaza toda la selección. Selecciona solo números "
        "que aparezcan en la lista de candidatos. Responde ÚNICAMENTE con un "
        "objeto JSON, sin bloques de código y sin texto adicional."
    ),
    "pt": (
        "Você é um filtro de resultados de recuperação para um sistema de "
        "Geração Aumentada por Recuperação. Dos trechos candidatos numerados, "
        "selecione os melhores para responder à mensagem do usuário.\n"
        "\n"
        "Mensagem do usuário:\n"
        "{input}\n"
        "\n"
        "Documentos: {documents.names}\n"
        "\n"
        "Descrição dos documentos: {documents.description}\n"
        "\n"
        "Trechos candidatos (cada linha mostra seu [número], document_id, "
        "posição e texto):\n"
        "{chunks}\n"
        "\n"
        "Selecione no máximo {topk} dos melhores trechos, os melhores "
        "primeiro.\n"
        "\n"
        "Responda chamando a função select_best_chunks com um único objeto "
        "JSON com esta forma:\n"
        '{"selected_chunks": [<números de candidato baseados em 1>], '
        '"message": "<frase breve opcional para o usuário>", '
        '"justification": "<justificativa breve opcional>"}\n'
        "\n"
        '- "selected_chunks" é obrigatório: índices baseados em 1 na lista '
        "numerada de candidatos acima, os melhores primeiro, únicos, no máximo "
        "{topk} entradas.\n"
        '- "message" é opcional: uma frase breve para o usuário no mesmo idioma '
        "deste prompt descrevendo o que você selecionou.\n"
        '- "justification" é opcional: uma frase breve no mesmo idioma deste '
        "prompt explicando sua seleção.\n"
        "\n"
        "Seleções inválidas são rejeitadas e devem ser repetidas: cada índice "
        "selecionado deve ser único, estar dentro do intervalo e ser no máximo "
        "{topk}, ou toda a seleção é rejeitada. Selecione apenas números que "
        "apareçam na lista de candidatos. Responda APENAS com um objeto JSON, "
        "sem blocos de código e sem texto adicional."
    ),
}


class DefaultLLMFilterPromptSchema(BaseSchema):
    """Schema for the default LLM filter prompt.

    Attributes:
        language: Language code for the generated instructions (en, es, pt).
        template: The prompt template string with placeholders.
    """

    language: schema_field(
        enum_field(enum=["en", "es", "pt"]),
        placeholder="en",
        description=MultilingualString(
            en="Language for the generated instructions.",
            es="Idioma de las instrucciones generadas.",
            pt="Idioma das instruções geradas.",
            de="Sprache der generierten Anweisungen.",
            zh="生成指令的语言。",
        ),
    )
    template: schema_field(
        string_field(),
        placeholder="",
        description="The prompt template with placeholders.",
    )


class DefaultLLMFilterPrompt(LLMFilterPrompt):
    """Default prompt template for selecting the best candidate chunks."""

    SCHEMA = DefaultLLMFilterPromptSchema
    DESCRIPTION: str = MultilingualString(
        en="Default prompt template for selecting the best candidate chunks"
        " with a function call.",
        es="Plantilla de prompt predeterminada para seleccionar los mejores"
        " fragmentos candidatos con una llamada a función.",
        pt="Modelo de prompt padrão para selecionar os melhores trechos"
        " candidatos com uma chamada de função.",
        de="Standard-Prompt-Vorlage zur Auswahl der besten Kandidatenfragmente"
        " über einen Funktionsaufruf.",
        zh="通过函数调用选择最佳候选片段的默认提示词模板。",
    )
    DISPLAY_NAME: str = MultilingualString(
        en="Default LLM Filter Prompt",
        es="Prompt de Filtro LLM Predeterminado",
        pt="Prompt de Filtro LLM Padrão",
        de="Standard-LLM-Filter-Prompt",
        zh="默认 LLM 过滤提示词",
    )

    required_placeholders = LLMFilterPrompt.required_placeholders
    optional_placeholders = LLMFilterPrompt.optional_placeholders

    metadata = {
        "name": "Default LLM Filter Prompt",
        "description": "Default prompt template for selecting the best"
        " candidate chunks with the select_best_chunks function call.",
        "type": "evaluation",
        "technique": "filter",
        "required_placeholders": required_placeholders,
        "optional_placeholders": optional_placeholders,
        "placeholder_descriptions": {
            "{input}": "The current user message the selected chunks must answer.",
            "{chunks}": (
                "The numbered candidate chunks, one line per chunk carrying its "
                "1-based index, document_id, position and text."
            ),
            "{topk}": (
                "Optional maximum number of chunks to select; the whole line "
                "disappears when it is not provided."
            ),
            "{documents.names}": (
                "Optional comma-separated document names; the whole line "
                "disappears when it is not provided."
            ),
            "{documents.description}": (
                "Optional JSON document summary; the whole line disappears when "
                "it is not provided."
            ),
        },
        "templates": TEMPLATES,
    }

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the default filter prompt.

        Parameters
        ----------
        language : str
            Language code used to pick the default template ("en", "es", "pt").
        template : str, optional
            Override template. When omitted, the template for ``language`` is
            used.

        Raises
        ------
        RAGPromptTemplateError
            If no template is available for the language or the resolved
            template is missing required placeholders.
        """
        self.language = kwargs.pop("language")
        if "template" in kwargs:
            self.template = kwargs.pop("template")
        else:
            self.template = TEMPLATES.get(self.language, "")
        if not self.template:
            raise RAGPromptTemplateError(
                f"No template available for language: {self.language}"
            )
        self._validate()

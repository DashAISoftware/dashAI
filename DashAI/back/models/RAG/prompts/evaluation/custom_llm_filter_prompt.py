"""User-defined LLM filter evaluation prompt."""

from __future__ import annotations

from typing import Any

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.prompts.evaluation.llm_filter_prompt import (
    LLMFilterPrompt,
)


class CustomLLMFilterPrompt(LLMFilterPrompt):
    """User-defined prompt template for selecting the best candidate chunks."""

    DESCRIPTION: str = MultilingualString(
        en="User-defined prompt template for selecting the best candidate"
        " chunks with a function call.",
        es="Plantilla de prompt definida por el usuario para seleccionar los"
        " mejores fragmentos candidatos con una llamada a función.",
        pt="Modelo de prompt definido pelo usuário para selecionar os melhores"
        " trechos candidatos com uma chamada de função.",
        de="Benutzerdefinierte Prompt-Vorlage zur Auswahl der besten"
        " Kandidatenfragmente über einen Funktionsaufruf.",
        zh="通过函数调用选择最佳候选片段的用户定义提示词模板。",
    )
    DISPLAY_NAME: str = MultilingualString(
        en="Custom LLM Filter Prompt",
        es="Prompt de Filtro LLM Personalizado",
        pt="Prompt de Filtro LLM Personalizado",
        de="Benutzerdefinierter LLM-Filter-Prompt",
        zh="自定义 LLM 过滤提示词",
    )

    metadata = {
        "name": "Custom LLM Filter Prompt",
        "description": "User-defined prompt template for selecting the best"
        " candidate chunks with the select_best_chunks function call.",
        "type": "evaluation",
        "technique": "filter",
        "required_placeholders": LLMFilterPrompt.required_placeholders,
        "optional_placeholders": LLMFilterPrompt.optional_placeholders,
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
    }

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the custom filter prompt.

        Parameters
        ----------
        template : str
            The user-defined template. Must contain ``{input}`` and
            ``{chunks}``.

        Raises
        ------
        RAGPromptTemplateError
            If the template is missing a required placeholder.
        """
        self.template = kwargs.pop("template")
        self._validate()

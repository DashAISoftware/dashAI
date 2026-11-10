"""User-defined agentic retriever prompt."""

from __future__ import annotations

from typing import Any

from DashAI.back.models.RAG.prompts.evaluation.agentic_retriever_prompt import (
    AgenticRetrieverPrompt,
)


class CustomAgenticRetrieverPrompt(AgenticRetrieverPrompt):
    """User-defined prompt template for an agentic retriever."""

    metadata = {
        "name": "Custom Agentic Retriever Prompt",
        "description": "User-defined prompt template for judging retrieval"
        " sufficiency and choosing which retrievers to consult next.",
        "type": "evaluation",
        "technique": "retriever",
        "required_placeholders": AgenticRetrieverPrompt.required_placeholders,
        "optional_placeholders": AgenticRetrieverPrompt.optional_placeholders,
        "placeholder_descriptions": {
            "{input}": "The current user message the chunks must answer.",
            "{chunks}": (
                "The chunks under evaluation, one line per chunk carrying its "
                "document_id, position and text; a preformatted string is kept "
                "verbatim."
            ),
            "{pool_size}": (
                "Optional candidate pool size; the whole line disappears when "
                "it is not provided."
            ),
            "{topk}": (
                "Optional maximum number of retrievable chunks; the whole line "
                "disappears when it is not provided."
            ),
            "{retriever.description}": (
                "Optional JSON catalog of the retrievers; the whole line "
                "disappears when it is not provided."
            ),
            "{documents.names}": (
                "Optional comma-separated document names; the whole line "
                "disappears when it is not provided."
            ),
            "{documents.description}": (
                "Optional JSON document summary; the whole line disappears "
                "when it is not provided."
            ),
        },
    }

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the custom agentic retriever prompt.

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

"""Abstract contract for LLM filter evaluation prompts.

A filter prompt renders the user message plus a numbered list of candidate
chunks and asks the model to select the best ones. It never declares a ``TYPE``
of its own: every concrete prompt registers under the generic ``"Prompt"`` type
via :class:`~DashAI.back.models.RAG.prompts.base_prompt.BasePrompt`.
"""

from __future__ import annotations

from collections.abc import Sequence

from DashAI.back.models.RAG.exceptions import RAGPromptTemplateError
from DashAI.back.models.RAG.prompts.base_prompt import BasePrompt
from DashAI.back.models.RAG.prompts.evaluation.chunk_prompt_rendering import (
    format_chunks,
    format_documents,
    render_template,
)
from DashAI.back.models.RAG.retrievers.retrieval_contracts import (
    ChunkPayload,
    DocumentSummary,
)


class LLMFilterPrompt(BasePrompt):
    """Base contract for prompts used by the LLM filter retriever.

    Templates are rendered with plain literal ``.replace`` calls rather than
    ``str.format`` because the strict JSON output contract embedded in the
    templates contains braces that ``str.format`` would try to interpret.

    Optional placeholders vanish together with the whole physical line that
    contains their token when no value is supplied, so a top-k sentence or a
    document summary disappears entirely instead of leaving a dangling
    fragment.
    """

    required_placeholders = ["{input}", "{chunks}"]
    optional_placeholders = [
        "{topk}",
        "{documents.names}",
        "{documents.description}",
    ]

    metadata = {
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
                "Optional comma-separated names of the documents in the corpus; "
                "the whole line disappears when it is not provided."
            ),
            "{documents.description}": (
                "Optional JSON summary of the documents (id, name, chunk count "
                "and pages); the whole line disappears when it is not provided."
            ),
        },
    }

    def _validate(self) -> None:
        """Ensure the resolved template carries every required placeholder.

        Raises
        ------
        RAGPromptTemplateError
            If a required placeholder is missing.
        """
        if not self.validate_template(self.template):
            raise RAGPromptTemplateError(
                "Template is missing required placeholders:"
                f" {self.required_placeholders}"
            )

    def format(
        self,
        input: str,
        chunks: str | Sequence[ChunkPayload],
        top_k: int | None = None,
        documents: Sequence[DocumentSummary] | None = None,
    ) -> str:
        """Render the prompt for the filter stage.

        The retriever passes structured data only; this method owns every piece
        of prompt formatting.

        Parameters
        ----------
        input : str
            The current user message.
        chunks : str | Sequence[Mapping[str, Any]]
            Preformatted chunk text (kept verbatim) or structured chunk payloads
            with ``document_id``, ``position`` and ``text``. Structured payloads
            are numbered ``[1]``, ``[2]``, ... so the model can select them.
        top_k : int | None
            Optional maximum number of chunks to select.
        documents : Sequence[DocumentSummary] | None
            Optional document summaries; names and JSON are derived from them.

        Returns
        -------
        str
            The fully rendered prompt.

        Raises
        ------
        RAGPromptTemplateError
            If the template is missing required placeholders or a structured
            chunk payload is malformed.
        """
        self._validate()
        documents_names, documents_description = format_documents(documents)
        return render_template(
            self.template,
            {
                "{input}": input,
                "{chunks}": format_chunks(chunks),
            },
            {
                "{topk}": top_k,
                "{documents.names}": documents_names,
                "{documents.description}": documents_description,
            },
        )

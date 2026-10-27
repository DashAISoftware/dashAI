"""Abstract contract for retrieval sufficiency evaluation prompts.

An evaluation prompt renders the current user message plus the chunks already
retrieved into a single chat instruction that asks the model to decide whether
those chunks are enough to answer the message, and — when they are not — which
retrievers to consult next. It never declares a ``TYPE`` of its own: every
concrete prompt registers under the generic ``"Prompt"`` type via
:class:`~DashAI.back.models.RAG.prompts.base_prompt.BasePrompt`.
"""

from __future__ import annotations

from collections.abc import Sequence

from DashAI.back.models.RAG.exceptions import RAGPromptTemplateError
from DashAI.back.models.RAG.prompts.base_prompt import BasePrompt
from DashAI.back.models.RAG.prompts.evaluation.chunk_prompt_rendering import (
    format_chunks,
    format_documents,
    render_optional_value,
    render_template,
)
from DashAI.back.models.RAG.retrievers.retrieval_contracts import (
    ChunkPayload,
    DocumentSummary,
    RetrieverCatalog,
)


class RetrievalSufficiencyPrompt(BasePrompt):
    """Base contract for prompts used by the LLM-evaluated retrievers.

    Templates are rendered with plain literal ``.replace`` calls rather than
    ``str.format`` because the strict JSON output contract embedded in the
    templates contains braces that ``str.format`` would try to interpret.

    Optional placeholders vanish together with the whole physical line that
    contains their token when no value is supplied, so a child-retriever
    catalog or a pool-size sentence disappears entirely instead of leaving a
    dangling fragment of text.
    """

    required_placeholders = ["{input}", "{chunks}"]
    optional_placeholders = [
        "{pool_size}",
        "{topk}",
        "{round}",
        "{max_rounds}",
        "{remaining}",
        "{retriever.description}",
        "{documents.names}",
        "{documents.description}",
    ]

    metadata = {
        "type": "evaluation",
        "technique": "sufficiency",
        "required_placeholders": required_placeholders,
        "optional_placeholders": optional_placeholders,
        "placeholder_descriptions": {
            "{input}": "The current user message the retrieved chunks must answer.",
            "{chunks}": (
                "The chunks under evaluation, one line per chunk carrying its "
                "document_id, position and text; a preformatted string is kept "
                "verbatim."
            ),
            "{pool_size}": (
                "Optional total number of candidate chunks in the current pool; "
                "the whole line disappears when it is not provided."
            ),
            "{topk}": (
                "Optional maximum number of chunks the retriever may return; "
                "the whole line disappears when it is not provided."
            ),
            "{round}": (
                "Optional 1-based evaluation round number; the whole line "
                "disappears when it is not provided."
            ),
            "{max_rounds}": (
                "Optional maximum number of evaluation rounds; the whole line "
                "disappears when it is not provided."
            ),
            "{remaining}": (
                "Optional number of free pool slots left; the whole line "
                "disappears when it is not provided."
            ),
            "{retriever.description}": (
                "Optional JSON catalog of the child retrievers and their "
                "parameters; the whole line disappears when it is not provided."
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
        pool_size: int | None = None,
        top_k: int | None = None,
        retrievers: str | RetrieverCatalog | None = None,
        documents: Sequence[DocumentSummary] | None = None,
        round_number: int | None = None,
        max_rounds: int | None = None,
        remaining: int | None = None,
    ) -> str:
        """Render the prompt for the retrieval sufficiency stage.

        The retriever passes structured data only; this method owns every piece
        of prompt formatting.

        Parameters
        ----------
        input : str
            The current user message.
        chunks : str | Sequence[Mapping[str, Any]]
            Preformatted chunk text (kept verbatim) or structured chunk payloads
            with ``document_id``, ``position`` and ``text``.
        pool_size : int | None
            Optional candidate pool size.
        top_k : int | None
            Optional maximum number of retrievable chunks.
        retrievers : str | Mapping | None
            Optional 1-based retriever catalog, JSON-rendered.
        documents : Sequence[DocumentSummary] | None
            Optional document summaries; names and JSON are derived from them.
        round_number : int | None
            Optional 1-based evaluation round number.
        max_rounds : int | None
            Optional maximum number of evaluation rounds.
        remaining : int | None
            Optional number of free pool slots. When omitted and both
            ``pool_size`` and ``top_k`` are known, it is derived as
            ``max(top_k - pool_size, 0)``.

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
        if remaining is None and pool_size is not None and top_k is not None:
            remaining = max(top_k - pool_size, 0)
        return render_template(
            self.template,
            {
                "{input}": input,
                "{chunks}": format_chunks(chunks),
            },
            {
                "{pool_size}": pool_size,
                "{topk}": top_k,
                "{round}": round_number,
                "{max_rounds}": max_rounds,
                "{remaining}": remaining,
                "{retriever.description}": render_optional_value(retrievers),
                "{documents.names}": documents_names,
                "{documents.description}": documents_description,
            },
        )

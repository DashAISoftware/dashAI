"""Shared realistic test data for RAG benchmarks.

Uses real PDF papers from the ``RAG_benchmark/papers/`` directory at the
project root.  All data is loaded lazily — documents are discovered
dynamically at runtime (no hardcoded filenames).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from DashAI.back.types.value_types import Text

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_document import DashAIDocument

# ═══════════════════════════════════════════════════════════════════════
#  Benchmark papers discovery — dynamic, no hardcoded filenames
# ═══════════════════════════════════════════════════════════════════════

#: Parameters the pypdf loader is called with, shared with the pipeline
#: benchmarks so a chunker row and a pipeline row are parsed from the same
#: text shape.
DOCUMENT_LOADER_PARAMS: dict[str, Any] = {
    "strict": True,
    "granularity": "block",
    "extract_images": False,
}


def _get_papers_dir() -> Path:
    """Resolve the ``RAG_benchmark/papers/`` directory relative to this file."""
    return Path(__file__).resolve().parent.parent / "papers"


def discover_benchmark_paper_files(max_docs: int | None = None) -> list[Path]:
    """Discover all PDF papers in ``RAG_benchmark/papers/`` dynamically.

    No filenames are hardcoded — any PDF placed in the directory will be
    picked up. Files are sorted by path for deterministic ordering.

    Parameters
    ----------
    max_docs : int | None
        Limit the number of files returned (useful for quick tests).
        ``None`` means all papers.

    Returns
    -------
    list[Path]
        Sorted PDF paths.

    Raises
    ------
    FileNotFoundError
        If the papers directory does not exist.
    """
    papers_dir = _get_papers_dir()
    if not papers_dir.is_dir():
        raise FileNotFoundError(
            f"RAG_benchmark/papers directory not found at {papers_dir}"
        )

    pdf_files = sorted(
        p for p in papers_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"
    )
    if max_docs is not None:
        pdf_files = pdf_files[:max_docs]
    return pdf_files


def load_paper_documents(max_docs: int | None = None) -> dict[int, DashAIDocument]:
    """Parse the benchmark papers with the pypdf document loader.

    Uses the current DashAI document parser stack
    (``PypdfDocumentDataLoader``) with :data:`DOCUMENT_LOADER_PARAMS`.
    Results are indexed by document position.

    Parameters
    ----------
    max_docs : int | None
        Limit the number of documents.

    Returns
    -------
    dict[int, DashAIDocument]
        Mapping ``{doc_index: parsed_document}``.

    Raises
    ------
    FileNotFoundError
        If ``RAG_benchmark/papers`` holds no PDF to benchmark.
    """
    from DashAI.back.dataloaders.classes.pypdf_document_dataloader import (
        PypdfDocumentDataLoader,
    )

    files = discover_benchmark_paper_files(max_docs=max_docs)
    if not files:
        raise FileNotFoundError(
            "No benchmark papers found in RAG_benchmark/papers; every component "
            "benchmark needs at least one PDF."
        )
    loader = PypdfDocumentDataLoader()
    return {
        index: loader.load_document(str(file_path), dict(DOCUMENT_LOADER_PARAMS))
        for index, file_path in enumerate(files)
    }


def load_paper_texts(max_docs: int | None = None) -> dict[int, str]:
    """Extract full text from the benchmark papers with the pypdf loader.

    Joins the ``Text`` items of each parsed document with a blank line.
    Results are indexed by document position.

    Parameters
    ----------
    max_docs : int | None
        Limit the number of documents.

    Returns
    -------
    dict[int, str]
        Mapping ``{doc_index: extracted_text}``.

    Raises
    ------
    FileNotFoundError
        If ``RAG_benchmark/papers`` holds no PDF to benchmark.
    """
    return {
        index: "\n\n".join(document[Text]).strip()
        for index, document in load_paper_documents(max_docs=max_docs).items()
    }


# ═══════════════════════════════════════════════════════════════════════
#  Multi-turn conversation (realistic chat for LLM testing)
# ═══════════════════════════════════════════════════════════════════════

MULTI_TURN_CONVERSATION: list[dict[str, str]] = [
    {
        "role": "user",
        "content": (
            "Can you explain the key differences between SQL and NoSQL databases?"
        ),
    },
    {
        "role": "assistant",
        "content": (
            "SQL databases are relational, use structured schemas with tables, "
            "and support ACID transactions. They use SQL for querying and are "
            "ideal for applications requiring data integrity and complex joins. "
            "Examples include PostgreSQL and MySQL. NoSQL databases are "
            "non-relational, support flexible schemas, and are designed for "
            "horizontal scaling. They come in several types: document stores "
            "like MongoDB, key-value stores like Redis, column-family stores "
            "like Cassandra, and graph databases like Neo4j."
        ),
    },
    {
        "role": "user",
        "content": ("When would you choose NoSQL over SQL for a new project?"),
    },
    {
        "role": "assistant",
        "content": (
            "NoSQL is a good choice when: (1) you have rapidly evolving data "
            "schemas that would be costly to migrate in SQL, (2) you need "
            "horizontal scalability across many servers for high write "
            "throughput, (3) your data is naturally document-oriented or "
            "graph-structured, (4) you need very low latency for simple "
            "read/write operations without complex joins. However, if your "
            "application requires strong consistency guarantees, complex "
            "transactions, or relational queries, SQL remains the better choice."
        ),
    },
    {
        "role": "user",
        "content": ("What does the CAP theorem say about this trade-off?"),
    },
]

#: Follow-up message and history used by the query transformation benchmarks.
#: The message deliberately references the previous turn so that history-aware
#: rewriting/expansion/decomposition has something to resolve.
TRANSFORMATION_HISTORY: list[dict[str, str]] = [
    {
        "role": "user",
        "content": (
            "What are the main stages of a retrieval-augmented generation pipeline?"
        ),
    },
    {
        "role": "assistant",
        "content": (
            "A RAG pipeline loads documents, splits them into chunks, embeds and "
            "indexes the chunks, retrieves the most relevant chunks for a query, "
            "and passes them to a language model to generate the answer."
        ),
    },
]

TRANSFORMATION_MESSAGE = (
    "How does the retrieval stage make use of the embeddings built in the "
    "previous step, and what happens if the query does not match any chunk?"
)

# ═══════════════════════════════════════════════════════════════════════
#  Shared component import maps (de-duplicated from 4 files)
# ═══════════════════════════════════════════════════════════════════════

LLM_MAP: dict[str, tuple[str, str]] = {
    "Llama31_8BInstruct": (
        "DashAI.back.models.hugging_face.llama_model",
        "Llama31_8BInstruct",
    ),
    "Llama32_1BInstruct": (
        "DashAI.back.models.hugging_face.llama_model",
        "Llama32_1BInstruct",
    ),
    "Llama32_3BInstruct": (
        "DashAI.back.models.hugging_face.llama_model",
        "Llama32_3BInstruct",
    ),
    "Mistral7BInstructV03": (
        "DashAI.back.models.hugging_face.mistral_model",
        "Mistral7BInstructV03",
    ),
    "MistralNemoInstruct2407": (
        "DashAI.back.models.hugging_face.mistral_model",
        "MistralNemoInstruct2407",
    ),
    "Mixtral8x7BInstructQ4KM": (
        "DashAI.back.models.hugging_face.mixtral_model",
        "Mixtral8x7BInstructQ4KM",
    ),
    "Mixtral8x7BInstructQ2K": (
        "DashAI.back.models.hugging_face.mixtral_model",
        "Mixtral8x7BInstructQ2K",
    ),
    "Qwen25_05BInstruct": (
        "DashAI.back.models.hugging_face.qwen_model",
        "Qwen25_05BInstruct",
    ),
    "Qwen25_15BInstruct": (
        "DashAI.back.models.hugging_face.qwen_model",
        "Qwen25_15BInstruct",
    ),
    "Qwen25_3BInstruct": (
        "DashAI.back.models.hugging_face.qwen_model",
        "Qwen25_3BInstruct",
    ),
    "Qwen25_7BInstruct": (
        "DashAI.back.models.hugging_face.qwen_model",
        "Qwen25_7BInstruct",
    ),
    "SmolLM2_360MInstruct": (
        "DashAI.back.models.hugging_face.smol_lm_model",
        "SmolLM2_360MInstruct",
    ),
    "SmolLM2_17BInstruct": (
        "DashAI.back.models.hugging_face.smol_lm_model",
        "SmolLM2_17BInstruct",
    ),
    "Phi4MiniInstructModel": (
        "DashAI.back.models.hugging_face.phi_4_mini_instruct_model",
        "Phi4MiniInstructModel",
    ),
}

CHUNKER_MAP: dict[str, tuple[str, str]] = {
    "CharacterChunkModel": (
        "DashAI.back.models.RAG.chunking_models.character_chunk_model",
        "CharacterChunkModel",
    ),
    "RecursiveCharacterChunkModel": (
        "DashAI.back.models.RAG.chunking_models.recursive_character_chunk_model",
        "RecursiveCharacterChunkModel",
    ),
    "TokenChunkModel": (
        "DashAI.back.models.RAG.chunking_models.token_chunk_model",
        "TokenChunkModel",
    ),
}

PROMPT_MAP: dict[str, tuple[str, str]] = {
    "DefaultQueryRewritingPrompt": (
        "DashAI.back.models.RAG.prompts.transformation.default_query_rewriting_prompt",
        "DefaultQueryRewritingPrompt",
    ),
    "CustomQueryRewritingPrompt": (
        "DashAI.back.models.RAG.prompts.transformation.custom_query_rewriting_prompt",
        "CustomQueryRewritingPrompt",
    ),
    "DefaultQueryExpansionPrompt": (
        "DashAI.back.models.RAG.prompts.transformation.default_query_expansion_prompt",
        "DefaultQueryExpansionPrompt",
    ),
    "CustomQueryExpansionPrompt": (
        "DashAI.back.models.RAG.prompts.transformation.custom_query_expansion_prompt",
        "CustomQueryExpansionPrompt",
    ),
    "DefaultQueryDecompositionPrompt": (
        "DashAI.back.models.RAG.prompts.transformation.default_query_decomposition_prompt",
        "DefaultQueryDecompositionPrompt",
    ),
    "CustomQueryDecompositionPrompt": (
        "DashAI.back.models.RAG.prompts.transformation.custom_query_decomposition_prompt",
        "CustomQueryDecompositionPrompt",
    ),
    "DefaultRAGGenerationPrompt": (
        "DashAI.back.models.RAG.prompts.generation.default_RAG_generation_prompt",
        "DefaultRAGGenerationPrompt",
    ),
    "CustomRAGGenerationPrompt": (
        "DashAI.back.models.RAG.prompts.generation.custom_RAG_generation_prompt",
        "CustomRAGGenerationPrompt",
    ),
    "DefaultQARAGGenerationPrompt": (
        "DashAI.back.models.RAG.prompts.generation.default_QA_RAG_generation_prompt",
        "DefaultQARAGGenerationPrompt",
    ),
    "DefaultAgenticRetrieverPrompt": (
        "DashAI.back.models.RAG.prompts.evaluation.default_agentic_retriever_prompt",  # noqa: E501
        "DefaultAgenticRetrieverPrompt",
    ),
    "CustomAgenticRetrieverPrompt": (
        "DashAI.back.models.RAG.prompts.evaluation.custom_agentic_retriever_prompt",  # noqa: E501
        "CustomAgenticRetrieverPrompt",
    ),
    "DefaultAgenticRerankerPrompt": (
        "DashAI.back.models.RAG.prompts.evaluation.default_agentic_reranker_prompt",
        "DefaultAgenticRerankerPrompt",
    ),
    "CustomAgenticRerankerPrompt": (
        "DashAI.back.models.RAG.prompts.evaluation.custom_agentic_reranker_prompt",
        "CustomAgenticRerankerPrompt",
    ),
}

TRANSFORMATION_MAP: dict[str, tuple[str, str]] = {
    "LLMQueryRewriter": (
        "DashAI.back.models.RAG.transformation.rewriting",
        "LLMQueryRewriter",
    ),
    "LLMQueryExpander": (
        "DashAI.back.models.RAG.transformation.expansion",
        "LLMQueryExpander",
    ),
    "LLMQueryDecomposer": (
        "DashAI.back.models.RAG.transformation.decomposition",
        "LLMQueryDecomposer",
    ),
}

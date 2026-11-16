"""Component-level benchmarks for the registered RAG prompt templates.

Prompts have no LLM dependency: the benchmark isolates *prompt formatting* by
instantiating each registered prompt component and timing a single ``format``
render with fixed sample inputs. No model is loaded, nothing is downloaded and
no device is selected, so every config executes deterministically.

The matrix has 33 configs: 21 default-language variants (7 default classes ×
en/es/pt) plus 12 custom configs (6 custom classes × 2 genuine templates),
covering the transformation, generation, retrieval-sufficiency and LLM-filter
prompt families.
"""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any, Optional

from DashAI.back.models.RAG.prompts.evaluation.default_agentic_reranker_prompt import (
    TEMPLATES as FILTER_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.prompts.evaluation.default_agentic_retriever_prompt import (  # noqa: E501
    TEMPLATES as SUFFICIENCY_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.prompts.generation.default_QA_RAG_generation_prompt import (  # noqa: E501
    TEMPLATES as QA_GENERATION_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.prompts.generation.default_RAG_generation_prompt import (  # noqa: E501
    TEMPLATES as GENERATION_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.prompts.transformation.default_query_decomposition_prompt import (  # noqa: E501
    TEMPLATES as DECOMPOSITION_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.prompts.transformation.default_query_expansion_prompt import (  # noqa: E501
    TEMPLATES as EXPANSION_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.prompts.transformation.default_query_rewriting_prompt import (  # noqa: E501
    TEMPLATES as REWRITING_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.transformation.llm_query_transformation import (
    format_history,
)
from RAG_benchmark.app.benchmark_data import (
    PROMPT_MAP,
    TRANSFORMATION_HISTORY,
    TRANSFORMATION_MESSAGE,
)
from RAG_benchmark.app.benchmark_utils import (
    Timer,
    load_component_class,
    load_last_run_statuses,
    run_configs,
)

log = logging.getLogger(__name__)

#: Number of queries the expansion render requests (mirrors the runtime).
_EXPANSION_N = 3

#: Upper bound passed to the decomposition render (mirrors the runtime).
_DECOMPOSITION_N_MAX = 4

#: Fixed, deterministic generation render inputs.
GENERATION_SAMPLE_QUESTION = (
    "Which retrieval strategies work best for long technical documents?"
)

GENERATION_SAMPLE_CHUNKS = (
    "Dense retrieval encodes every chunk and the query into the same "
    "embedding space and ranks chunks by vector similarity, which handles "
    "paraphrases and synonyms well but can miss rare keywords.\n"
    "\n"
    "Sparse retrieval such as BM25 scores chunks by lexical overlap, so it "
    "stays precise on exact terms, identifiers and rare tokens while being "
    "less robust to wording changes."
)

GENERATION_SAMPLE_QUERIES = "chunking strategies; dense versus sparse retrieval"

#: Fixed, deterministic retrieval-sufficiency render inputs.
_EVALUATION_POOL_SIZE = 3
_EVALUATION_SUFFICIENCY_TOP_K = 10
_EVALUATION_ROUND = 1
_EVALUATION_MAX_ROUNDS = 3
_EVALUATION_REMAINING = 7

#: Fixed, deterministic LLM-filter render inputs.
_EVALUATION_FILTER_TOP_K = 5

#: 1-based retriever catalog handed to the sufficiency render.
_EVALUATION_SAMPLE_RETRIEVERS: dict[str, dict[str, Any]] = {
    "1": {"name": "BM25Retriever", "top_k": 5},
}

#: Document summaries handed to the evaluation renders (real contract keys).
_EVALUATION_SAMPLE_DOCUMENTS: list[dict[str, Any]] = [
    {"document_id": 0, "name": "paper.pdf", "chunks": 12, "pages": 3},
]

#: Prompt classes rendered by the generation stage (input/chunks/queries).
_GENERATION_CLASSES = frozenset(
    {
        "DefaultRAGGenerationPrompt",
        "CustomRAGGenerationPrompt",
        "DefaultQARAGGenerationPrompt",
    }
)

#: Class-name markers identifying the non-generation placeholder families.
_FAMILY_MARKERS: tuple[tuple[str, str], ...] = (
    ("AgenticRetriever", "sufficiency"),
    ("AgenticReranker", "filter"),
    ("Expansion", "expansion"),
    ("Decomposition", "decomposition"),
    ("Sufficiency", "sufficiency"),
    ("Filter", "filter"),
)

#: Placeholder tokens each family must resolve when rendered.
_FAMILY_TOKENS: dict[str, tuple[str, ...]] = {
    "generation": ("{input}", "{chunks}", "{queries}"),
    "expansion": ("{input}", "{history}", "{n}"),
    "decomposition": ("{input}", "{history}", "{n_max}"),
    "rewriting": ("{input}", "{history}"),
    "sufficiency": (
        "{input}",
        "{chunks}",
        "{pool_size}",
        "{topk}",
        "{round}",
        "{max_rounds}",
        "{remaining}",
        "{retriever.description}",
        "{documents.names}",
        "{documents.description}",
    ),
    "filter": (
        "{input}",
        "{chunks}",
        "{topk}",
        "{documents.names}",
        "{documents.description}",
    ),
}

#: Sample input each family's render must preserve verbatim.
_FAMILY_SAMPLE_INPUT: dict[str, str] = {
    "generation": GENERATION_SAMPLE_QUESTION,
    "sufficiency": GENERATION_SAMPLE_QUESTION,
    "filter": GENERATION_SAMPLE_QUESTION,
}

#: Genuine user-defined rewriting templates (1-to-1 transformation).
CUSTOM_REWRITING_TEMPLATES: tuple[str, str] = (
    (
        "Rewrite the current message as one self-contained search query for the "
        "document index. Fold in the conversation context only when the message "
        "depends on it.\n"
        "\n"
        "Earlier turns:\n"
        "{history}\n"
        "\n"
        "Current message:\n"
        "{input}\n"
        "\n"
        "Reply with the query only."
    ),
    (
        "Condense the conversation into the single information need the user is "
        "pursuing, then phrase it as a keyword-rich query for the document "
        "index. Drop greetings, filler and anything already answered.\n"
        "\n"
        "Conversation so far:\n"
        "{history}\n"
        "\n"
        "Message to rewrite:\n"
        "{input}\n"
        "\n"
        "Return one line: the query."
    ),
)

#: Genuine user-defined expansion templates (1-to-n transformation).
CUSTOM_EXPANSION_TEMPLATES: tuple[str, str] = (
    (
        "Produce {n} search queries covering the current message from "
        "complementary angles so retrieval finds more relevant passages. Keep one "
        "query close to the original wording.\n"
        "\n"
        "Earlier turns:\n"
        "{history}\n"
        "\n"
        "Current message:\n"
        "{input}\n"
        "\n"
        "List the queries as plain text, one per line."
    ),
    (
        "The current message is ambiguous on its own. Write {n} alternative "
        "queries that each resolve it differently against the conversation "
        "below, ordering them from the most likely interpretation to the least.\n"
        "\n"
        "Conversation so far:\n"
        "{history}\n"
        "\n"
        "Current message:\n"
        "{input}\n"
        "\n"
        "Write one query per line, no numbering."
    ),
)

#: Genuine user-defined decomposition templates (1-to-n transformation).
CUSTOM_DECOMPOSITION_TEMPLATES: tuple[str, str] = (
    (
        "Split the current question into the smallest useful set of independent "
        "sub-questions, each answerable by a separate document search. Use at "
        "most {n_max} sub-questions.\n"
        "\n"
        "Earlier turns:\n"
        "{history}\n"
        "\n"
        "Current message:\n"
        "{input}\n"
        "\n"
        "List the sub-questions as plain text, one per line."
    ),
    (
        "Break the current message into the atomic lookups a search engine must "
        "run to answer it, ordered from the most factual to the most "
        "interpretive. Emit no more than {n_max} sub-questions.\n"
        "\n"
        "Conversation so far:\n"
        "{history}\n"
        "\n"
        "Current message:\n"
        "{input}\n"
        "\n"
        "Write one sub-question per line, no numbering."
    ),
)

#: Genuine user-defined generation templates (input/chunks/queries).
CUSTOM_GENERATION_TEMPLATES: tuple[str, str] = (
    (
        "Answer the question using only the retrieved context below. If the "
        "context does not contain the answer, say so explicitly.\n"
        "\n"
        "Retrieved context:\n"
        "{chunks}\n"
        "\n"
        "Question: {input}\n"
        "Search queries used: {queries}"
    ),
    (
        "You are writing a short, verifiable answer for a technical audience. "
        "Use the passages below as the only source of truth and name the "
        "passage you relied on.\n"
        "\n"
        "Passages:\n"
        "{chunks}\n"
        "\n"
        "Question: {input}\n"
        "Queries that found these passages: {queries}\n"
        "\n"
        "Answer in at most four sentences."
    ),
)

#: Genuine user-defined retrieval-sufficiency templates (input/chunks + optionals).
CUSTOM_SUFFICIENCY_TEMPLATES: tuple[str, str] = (
    (
        "Decide whether the chunks below already answer the user message well "
        "enough to stop retrieving.\n"
        "\n"
        "User message:\n"
        "{input}\n"
        "\n"
        "Documents on file: {documents.names}\n"
        "\n"
        "Candidate chunks:\n"
        "{chunks}\n"
        "\n"
        "Pool size: {pool_size} of {topk} allowed chunks ({remaining} slots "
        "free, round {round} of {max_rounds}).\n"
        "\n"
        "Retrievers available:\n"
        "{retriever.description}\n"
        "\n"
        "Respond with the evaluate_retrieval_sufficiency JSON object only."
    ),
    (
        "You audit a retrieval pool before generation. Keep the pool only if it "
        "answers the user message completely; otherwise ask for the missing "
        "evidence from the catalog.\n"
        "\n"
        "User message:\n"
        "{input}\n"
        "\n"
        "Pool content:\n"
        "{chunks}\n"
        "\n"
        "Pool size: {pool_size} chunks, {remaining} free slots left in round "
        "{round} of {max_rounds} (cap {topk}).\n"
        "\n"
        "Document inventory:\n"
        "{documents.description}\n"
        "\n"
        "Retriever catalog:\n"
        "{retriever.description}\n"
        "\n"
        "Respond with the evaluate_retrieval_sufficiency JSON object only."
    ),
)

#: Genuine user-defined LLM-filter templates (input/chunks + optionals).
CUSTOM_FILTER_TEMPLATES: tuple[str, str] = (
    (
        "Pick the candidate chunks that best answer the user message and drop "
        "the rest. Fewer, better chunks beat a long list.\n"
        "\n"
        "User message:\n"
        "{input}\n"
        "\n"
        "Candidates:\n"
        "{chunks}\n"
        "\n"
        "Keep at most {topk} candidates, best first. Documents available: "
        "{documents.names}\n"
        "\n"
        "Respond with the select_best_chunks JSON object only."
    ),
    (
        "You are triaging search results. Number the candidates you would keep "
        "for the answer, in priority order, and ignore anything that only "
        "repeats the question.\n"
        "\n"
        "User message:\n"
        "{input}\n"
        "\n"
        "Candidate list:\n"
        "{chunks}\n"
        "\n"
        "Corpus:\n"
        "{documents.description}\n"
        "\n"
        "Return at most {topk} 1-based candidate numbers via select_best_chunks."
    ),
)

#: Default prompt classes with their technique and the language templates they
#: ship. Iterating over each module's ``TEMPLATES`` keeps the benchmark matrix
#: in sync with the real language keys.
_DEFAULT_PROMPT_CLASSES = (
    (
        "DefaultQueryRewritingPrompt",
        "rewriting",
        REWRITING_PROMPT_TEMPLATES,
    ),
    (
        "DefaultQueryExpansionPrompt",
        "expansion",
        EXPANSION_PROMPT_TEMPLATES,
    ),
    (
        "DefaultQueryDecompositionPrompt",
        "decomposition",
        DECOMPOSITION_PROMPT_TEMPLATES,
    ),
    (
        "DefaultRAGGenerationPrompt",
        "generation",
        GENERATION_PROMPT_TEMPLATES,
    ),
    (
        "DefaultQARAGGenerationPrompt",
        "generation",
        QA_GENERATION_PROMPT_TEMPLATES,
    ),
    (
        "DefaultAgenticRetrieverPrompt",
        "sufficiency",
        SUFFICIENCY_PROMPT_TEMPLATES,
    ),
    (
        "DefaultAgenticRerankerPrompt",
        "filter",
        FILTER_PROMPT_TEMPLATES,
    ),
)

#: Custom prompt classes with the two genuine templates each category renders.
_CUSTOM_PROMPT_CLASSES = (
    (
        "CustomQueryRewritingPrompt",
        "rewriting",
        CUSTOM_REWRITING_TEMPLATES,
    ),
    (
        "CustomQueryExpansionPrompt",
        "expansion",
        CUSTOM_EXPANSION_TEMPLATES,
    ),
    (
        "CustomQueryDecompositionPrompt",
        "decomposition",
        CUSTOM_DECOMPOSITION_TEMPLATES,
    ),
    (
        "CustomRAGGenerationPrompt",
        "generation",
        CUSTOM_GENERATION_TEMPLATES,
    ),
    (
        "CustomAgenticRetrieverPrompt",
        "sufficiency",
        CUSTOM_SUFFICIENCY_TEMPLATES,
    ),
    (
        "CustomAgenticRerankerPrompt",
        "filter",
        CUSTOM_FILTER_TEMPLATES,
    ),
)

#: Prefix of the custom config names (``custom-1``, ``custom-2``).
_CUSTOM_CONFIG_NAME_PREFIX = "custom"


def _prompt_family(component_class: str) -> str:
    """Return the placeholder family a prompt class belongs to.

    Parameters
    ----------
    component_class : str
        The prompt class name.

    Returns
    -------
    str
        ``"generation"``, ``"expansion"``, ``"decomposition"``,
        ``"sufficiency"``, ``"filter"`` or ``"rewriting"`` (the fallback for
        every transformation prompt that only takes ``input`` and ``history``).
    """
    if component_class in _GENERATION_CLASSES:
        return "generation"
    for marker, family in _FAMILY_MARKERS:
        if marker in component_class:
            return family
    return "rewriting"


PROMPT_CONFIGS = [
    {
        "component_class": component_class,
        "model_name": model_name,
        "config_name": language,
        "params": {
            "language": language,
            "template": templates[language],
        },
    }
    for component_class, model_name, templates in _DEFAULT_PROMPT_CLASSES
    for language in templates
] + [
    {
        "component_class": component_class,
        "model_name": model_name,
        "config_name": f"{_CUSTOM_CONFIG_NAME_PREFIX}-{index}",
        "params": {"template": template},
    }
    for component_class, model_name, templates in _CUSTOM_PROMPT_CLASSES
    for index, template in enumerate(templates, start=1)
]


def _render(prompt: Any, component_class: str, history_block: str) -> str:
    """Render one prompt exactly as the runtime does.

    Transformation prompts receive the fixed ``TRANSFORMATION_MESSAGE`` plus
    the caller-supplied formatted history block; expansion adds ``n`` and
    decomposition adds ``n_max``. Generation prompts receive the fixed sample
    question, chunks and queries. Evaluation prompts receive the sample
    question and chunks plus every optional value the retriever can supply
    (pool accounting, retriever catalog and document summaries), so no
    optional line is dropped by accident.

    Parameters
    ----------
    prompt : Any
        The instantiated prompt component.
    component_class : str
        The prompt class name (drives the family).
    history_block : str
        The already-formatted conversation history the transformation prompts
        embed. Precomputed by the caller so history formatting sits outside
        the measured render.

    Returns
    -------
    str
        The rendered prompt.
    """
    family = _prompt_family(component_class)
    if family == "generation":
        return prompt.format(
            input=GENERATION_SAMPLE_QUESTION,
            chunks=GENERATION_SAMPLE_CHUNKS,
            queries=GENERATION_SAMPLE_QUERIES,
        )
    if family == "sufficiency":
        return prompt.format(
            input=GENERATION_SAMPLE_QUESTION,
            chunks=GENERATION_SAMPLE_CHUNKS,
            pool_size=_EVALUATION_POOL_SIZE,
            top_k=_EVALUATION_SUFFICIENCY_TOP_K,
            round_number=_EVALUATION_ROUND,
            max_rounds=_EVALUATION_MAX_ROUNDS,
            remaining=_EVALUATION_REMAINING,
            retrievers=_EVALUATION_SAMPLE_RETRIEVERS,
            documents=_EVALUATION_SAMPLE_DOCUMENTS,
        )
    if family == "filter":
        return prompt.format(
            input=GENERATION_SAMPLE_QUESTION,
            chunks=GENERATION_SAMPLE_CHUNKS,
            top_k=_EVALUATION_FILTER_TOP_K,
            documents=_EVALUATION_SAMPLE_DOCUMENTS,
        )
    kwargs: dict[str, Any] = {
        "input": TRANSFORMATION_MESSAGE,
        "history": history_block,
    }
    if family == "expansion":
        kwargs["n"] = _EXPANSION_N
    elif family == "decomposition":
        kwargs["n_max"] = _DECOMPOSITION_N_MAX
    return prompt.format(**kwargs)


def _assert_prompt_rendered(rendered: Any, component_class: str) -> None:
    """Assert a rendered prompt resolved every family placeholder.

    Checks the render is a non-empty string, that the family's placeholder
    tokens are gone and that the fixed sample input text survives.

    Parameters
    ----------
    rendered : Any
        The value returned by a prompt ``format`` call.
    component_class : str
        The prompt class name (drives the placeholder set).

    Raises
    ------
    AssertionError
        If the render is empty, a family placeholder remains, or the sample
        input is missing. The message names the offending token.
    """
    assert isinstance(rendered, str), f"{component_class} did not render a string"
    assert rendered.strip(), f"{component_class} rendered an empty prompt"
    family = _prompt_family(component_class)
    for token in _FAMILY_TOKENS[family]:
        assert token not in rendered, (
            f"{component_class} left placeholder {token!r} in the rendered prompt"
        )
    sample_input = _FAMILY_SAMPLE_INPUT.get(family, TRANSFORMATION_MESSAGE)
    assert sample_input in rendered, (
        f"{component_class} rendered prompt is missing the sample input text"
    )


def _template_prefix(template: str) -> str:
    """Return the literal text that precedes a template's first placeholder.

    Parameters
    ----------
    template : str
        A prompt template, possibly starting with a placeholder.

    Returns
    -------
    str
        The substring before the first ``"{"`` with surrounding whitespace
        stripped; an empty string when the template starts with a placeholder.
    """
    return template.split("{", 1)[0].strip()


def _execute_prompt(cfg: dict[str, Any]) -> tuple[str, float, float, str]:
    """Benchmark a single prompt component's formatting step.

    Instantiates the prompt class only (no LLM) inside the load timer and
    times one render inside the execution timer; the history block is
    formatted before the timers so the measured render stays format-only.

    After the placeholder assertions, the render must contain the prefix of
    the config's own template (the text before its first placeholder). This
    proves the output came from *this* config: the selected language variant
    for a default class or the genuine custom text for a custom class. The
    check is skipped when the template starts with a placeholder.

    Parameters
    ----------
    cfg : dict[str, Any]
        A ``PROMPT_CONFIGS`` entry (``component_class`` and ``params`` are
        read; ``params`` may carry the iteration bookkeeping keys).

    Returns
    -------
    tuple[str, float, float, str]
        ``(status, execution_time, load_time, error_message)``.
    """
    params = dict(cfg["params"])
    component_class = cfg["component_class"]
    prompt_params: dict[str, Any] = {}
    for key in ("language", "template"):
        if key in params:
            prompt_params[key] = params[key]
    PromptClass = load_component_class(PROMPT_MAP, component_class)
    history_block = format_history(TRANSFORMATION_HISTORY, 2)

    with Timer() as load_timer:
        prompt = PromptClass(**prompt_params)

    with Timer() as exec_timer:
        rendered = _render(prompt, component_class, history_block)

    _assert_prompt_rendered(rendered, component_class)
    prefix = _template_prefix(params.get("template", ""))
    if prefix:
        assert prefix in rendered, (
            f"{component_class} rendered output does not contain its config "
            "template prefix"
        )

    return "passed", exec_timer.elapsed, load_timer.elapsed, ""


def run_all_prompt_benchmarks(
    logger,
    iterations: int = 1,
    skip_passes: bool = False,
    results_dir: Optional[Path] = None,
) -> None:
    """Run all prompt formatting benchmarks.

    Parameters
    ----------
    logger : BenchmarkLogger
    iterations : int
        Number of iterations per config.
    skip_passes : bool
        If True, skip configs that passed in the last benchmark run.
    results_dir : Path or None
        Base results directory scanned for previous runs (falls back to
        the logger's output directory when None).
    """
    statuses = (
        load_last_run_statuses(results_dir or logger.output_dir)
        if skip_passes
        else None
    )
    for iteration in range(1, iterations + 1):
        configs = []
        for cfg in PROMPT_CONFIGS:
            c = copy.deepcopy(cfg)
            c.setdefault("params", {})["iteration"] = iteration
            c.setdefault("params", {})["total_iterations"] = iterations
            configs.append(c)
        run_configs(
            configs,
            "prompt",
            _execute_prompt,
            logger,
            skip_statuses=statuses,
        )

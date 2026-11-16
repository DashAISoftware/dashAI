"""Component-level benchmarks for the query transformation modules.

Each transformer class is benchmarked twice: a history-aware baseline and a
variant that drops the conversation history, with a different query budget for
the 1-to-n transformers.
"""

from __future__ import annotations

import copy
import functools
import logging
from pathlib import Path
from typing import Any, Optional

from DashAI.back.models.RAG.prompts.transformation.default_query_decomposition_prompt import (  # noqa: E501
    TEMPLATES as DECOMPOSITION_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.prompts.transformation.default_query_expansion_prompt import (  # noqa: E501
    TEMPLATES as EXPANSION_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.prompts.transformation.default_query_rewriting_prompt import (  # noqa: E501
    TEMPLATES as REWRITING_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.transformation.base_query_transformation import (
    QueryTransformationResult,
)
from RAG_benchmark.app.benchmark_data import (
    LLM_MAP,
    PROMPT_MAP,
    TRANSFORMATION_HISTORY,
    TRANSFORMATION_MAP,
    TRANSFORMATION_MESSAGE,
)
from RAG_benchmark.app.benchmark_utils import (
    Timer,
    ensure_component_downloaded,
    load_component_class,
    load_last_run_statuses,
    run_configs,
)
from RAG_benchmark.app.components.llm import _resolve_llm_device

log = logging.getLogger(__name__)

#: Sampling shared by every transformer, whatever its checkpoint. The context
#: window is per checkpoint and lives in ``_TRANSFORMER_LLM_VARIANTS``.
_TRANSFORMER_LLM_PARAMS = {
    "max_tokens": 256,
    "temperature": 0.1,
    "frequency_penalty": 0.0,
    "device": "CPU",
}

#: Checkpoints the matrix benchmarks, as
#: ``(suffix, component, repo, context_window)``.
#:
#: ``qwen1.5b`` holds the rows that were already measured with the small
#: checkpoint; ``qwen7b`` repeats the same techniques on the checkpoint the
#: pipelines use. Keeping both makes the comparison explicit instead of
#: rewriting history: the config name states which model produced the row.
_TRANSFORMER_LLM_VARIANTS: tuple[tuple[str, str, str, int], ...] = (
    ("qwen1.5b", "Qwen25_15BInstruct", "Qwen/Qwen2.5-1.5B-Instruct-GGUF", 2048),
    ("qwen7b", "Qwen25_7BInstruct", "Qwen/Qwen2.5-7B-Instruct-GGUF", 4096),
)

#: Language of the default transformation prompt used by every baseline config.
_TRANSFORMER_PROMPT_LANGUAGE = "en"

#: Techniques, as ``(class, slug, prompt class, templates, baseline params,
#: variant suffix, variant params)``. The baseline is history-aware; the
#: variant drops the history and, for the 1-to-n transformers, changes the
#: query budget.
_TRANSFORMER_TECHNIQUES: tuple[
    tuple[str, str, str, dict[str, str], dict[str, Any], str, dict[str, Any]], ...
] = (
    (
        "LLMQueryRewriter",
        "rewriter",
        "DefaultQueryRewritingPrompt",
        REWRITING_PROMPT_TEMPLATES,
        {"history_window": 2},
        "-no-history",
        {"history_window": 0},
    ),
    (
        "LLMQueryExpander",
        "expander",
        "DefaultQueryExpansionPrompt",
        EXPANSION_PROMPT_TEMPLATES,
        {"history_window": 2, "n_queries": 3},
        "-n5",
        {"history_window": 0, "n_queries": 5},
    ),
    (
        "LLMQueryDecomposer",
        "decomposer",
        "DefaultQueryDecompositionPrompt",
        DECOMPOSITION_PROMPT_TEMPLATES,
        {"history_window": 2, "max_subqueries": 4},
        "-n2",
        {"history_window": 0, "max_subqueries": 2},
    ),
)


def _llm_ref(component: str, context_window: int) -> dict[str, Any]:
    """Build a fresh nested LLM component reference for one checkpoint."""
    params = dict(_TRANSFORMER_LLM_PARAMS)
    params["context_window"] = context_window
    return {"component": component, "params": params}


def _transformation_config(
    component_class: str,
    config_name: str,
    prompt_component: str,
    prompt_templates: dict[str, str],
    llm_component: str,
    llm_repo: str,
    context_window: int,
    history_window: int,
    n_queries: int | None = None,
    max_subqueries: int | None = None,
) -> dict[str, Any]:
    """Build one query-transformation benchmark config.

    Parameters
    ----------
    component_class : str
        The transformer class name registered in ``TRANSFORMATION_MAP``.
    config_name : str
        Unique benchmark config name.
    prompt_component : str
        The default prompt class name registered in ``PROMPT_MAP``.
    prompt_templates : dict[str, str]
        The prompt module's ``TEMPLATES`` mapping (language -> template).
    llm_component : str
        Registered LLM class the transformer calls.
    llm_repo : str
        GGUF repo reported as the config's ``model_name``.
    context_window : int
        Context budget of that checkpoint.
    history_window : int
        Number of conversation turns the transformer receives.
    n_queries : int or None
        Expansion target; omitted for classes that do not accept it.
    max_subqueries : int or None
        Decomposition cap; omitted for classes that do not accept it.

    Returns
    -------
    dict[str, Any]
        A ``TRANSFORMATION_CONFIGS`` entry.
    """
    params: dict[str, Any] = {
        "prompt": {
            "component": prompt_component,
            "params": {
                "language": _TRANSFORMER_PROMPT_LANGUAGE,
                "template": prompt_templates[_TRANSFORMER_PROMPT_LANGUAGE],
            },
        },
        "llm_model": _llm_ref(llm_component, context_window),
        "history_window": history_window,
    }
    if n_queries is not None:
        params["n_queries"] = n_queries
    if max_subqueries is not None:
        params["max_subqueries"] = max_subqueries
    return {
        "component_class": component_class,
        "model_name": llm_repo,
        "config_name": config_name,
        "params": params,
    }


#: Two configs per technique and checkpoint: 3 techniques x 2 profiles x 2
#: checkpoints = 12.
TRANSFORMATION_CONFIGS = [
    _transformation_config(
        component_class,
        f"{slug}-{llm_suffix}{name_suffix}",
        prompt_component,
        prompt_templates,
        llm_component,
        llm_repo,
        context_window,
        **params,
    )
    for (
        component_class,
        slug,
        prompt_component,
        prompt_templates,
        baseline_params,
        variant_name,
        variant_params,
    ) in _TRANSFORMER_TECHNIQUES
    for llm_suffix, llm_component, llm_repo, context_window in _TRANSFORMER_LLM_VARIANTS
    for name_suffix, params in (("", baseline_params), (variant_name, variant_params))
]


def _execute_transformation(
    cfg: dict[str, Any], *, download_missing_models: bool = True
) -> tuple[str, float, float, str]:
    """Benchmark a single query transformer config.

    Returns
    -------
    tuple[str, float, float, str]
        ``(status, execution_time, load_time, error_message)``.
    """
    params = dict(cfg["params"])

    prompt_spec = params["prompt"]
    PromptClass = load_component_class(PROMPT_MAP, prompt_spec["component"])

    llm_spec = params["llm_model"]
    LLMClass = load_component_class(LLM_MAP, llm_spec["component"])

    ensure_component_downloaded(LLMClass, download=download_missing_models)

    TransformerClass = load_component_class(TRANSFORMATION_MAP, cfg["component_class"])

    extra_kwargs: dict[str, Any] = {}
    for key in ("n_queries", "max_subqueries"):
        if key in params:
            extra_kwargs[key] = params[key]

    with Timer() as load_timer:
        prompt = PromptClass(**prompt_spec.get("params", {}))
        llm_model = LLMClass(**llm_spec.get("params", {}))
        transformer = TransformerClass(
            prompt=prompt,
            llm_model=llm_model,
            history_window=params.get("history_window", 2),
            **extra_kwargs,
        )

    with Timer() as exec_timer:
        result = transformer.transform(TRANSFORMATION_MESSAGE, TRANSFORMATION_HISTORY)

    assert isinstance(result, QueryTransformationResult), (
        f"Expected a QueryTransformationResult, got {type(result).__name__}"
    )
    queries = result.queries
    assert isinstance(queries, list), f"Expected a list of queries, got {type(queries)}"
    assert queries, "Expected at least one transformed query"
    assert all(isinstance(query, str) and query.strip() for query in queries), (
        f"Expected non-empty string queries, got {queries}"
    )

    return "passed", exec_timer.elapsed, load_timer.elapsed, ""


def run_all_transformation_benchmarks(
    logger,
    iterations: int = 1,
    device: str = "CPU",
    skip_passes: bool = False,
    results_dir: Optional[Path] = None,
    download_missing_models: bool = True,
) -> None:
    """Run all query transformation benchmarks.

    Parameters
    ----------
    logger : BenchmarkLogger
    iterations : int
        Number of iterations per config.
    device : str
        Device for the nested LLM: ``auto`` resolves to the first llama.cpp
        GPU (falling back to ``CPU``), and ``GPU``/``CUDA`` ask for that GPU
        explicitly.
    skip_passes : bool
        If True, skip configs that passed in the last benchmark run.
    results_dir : Path or None
        Base results directory scanned for previous runs (falls back to
        the logger's output directory when None).
    download_missing_models : bool
        If True, download missing nested-LLM artifacts before loading. If
        False, a missing model fails that execution instead.
    """
    device = _resolve_llm_device(device)
    statuses = (
        load_last_run_statuses(results_dir or logger.output_dir)
        if skip_passes
        else None
    )
    for iteration in range(1, iterations + 1):
        configs = []
        for cfg in TRANSFORMATION_CONFIGS:
            c = copy.deepcopy(cfg)
            c.setdefault("params", {})["iteration"] = iteration
            c.setdefault("params", {})["total_iterations"] = iterations
            c["params"]["llm_model"].setdefault("params", {})["device"] = device
            configs.append(c)
        execute_fn = functools.partial(
            _execute_transformation,
            download_missing_models=download_missing_models,
        )
        run_configs(
            configs,
            "transformation",
            execute_fn,
            logger,
            skip_statuses=statuses,
        )

"""Component-level benchmarks for the registered GGUF text-generation classes.

Every checkpoint class is benchmarked twice: a ``concise`` and a ``creative``
sampling profile over the same weights, so inside a pair the decoding policy is
the only variable.
"""

from __future__ import annotations

import copy
import functools
import logging
from pathlib import Path
from typing import Any, Optional

from RAG_benchmark.app.benchmark_data import LLM_MAP, MULTI_TURN_CONVERSATION
from RAG_benchmark.app.benchmark_utils import (
    Timer,
    ensure_component_downloaded,
    load_component_class,
    load_last_run_statuses,
    run_configs,
)

log = logging.getLogger(__name__)

LLM_SYSTEM_PROMPT = "You are a helpful AI assistant. Answer concisely."

#: The one checkpoint that resolves its GGUF through ``llama_cpp`` directly
#: instead of the DashAI downloadable-component mixin.
PHI4_COMPONENT = "Phi4MiniInstructModel"

#: Run bookkeeping keys, stripped before a checkpoint is constructed.
_BOOKKEEPING_KEYS = ("iteration", "total_iterations")

#: Sampling profile shared by the checkpoint-specific GGUF classes: short,
#: near-greedy answers suited to factual RAG generation.
_GGUF_PARAMS = {
    "max_tokens": 100,
    "temperature": 0.1,
    "frequency_penalty": 0.0,
    "context_window": 4096,
    "device": "CPU",
}

#: Sampling profile that trades determinism for lexical diversity: longer
#: answers, higher temperature and a mild repetition penalty.
_CREATIVE_PARAMS = {
    "max_tokens": 200,
    "temperature": 0.7,
    "frequency_penalty": 0.2,
    "context_window": 4096,
}

#: Sampling profiles paired over every checkpoint class, so each class is
#: benchmarked twice with the same weights and a different decoding policy.
_SAMPLING_PROFILES: dict[str, dict[str, Any]] = {
    "concise": _GGUF_PARAMS,
    "creative": _CREATIVE_PARAMS,
}

#: Registered GGUF checkpoint classes with their HF repo and base config name.
_LLM_CHECKPOINTS: tuple[tuple[str, str, str], ...] = (
    (
        "Llama31_8BInstruct",
        "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
        "llama3.1-8b",
    ),
    (
        "Llama32_1BInstruct",
        "bartowski/Llama-3.2-1B-Instruct-GGUF",
        "llama3.2-1b",
    ),
    (
        "Llama32_3BInstruct",
        "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "llama3.2-3b",
    ),
    (
        "Mistral7BInstructV03",
        "bartowski/Mistral-7B-Instruct-v0.3-GGUF",
        "mistral-7b",
    ),
    (
        "MistralNemoInstruct2407",
        "bartowski/Mistral-Nemo-Instruct-2407-GGUF",
        "mistral-nemo",
    ),
    (
        "Qwen25_05BInstruct",
        "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        "qwen2.5-0.5b",
    ),
    (
        "Qwen25_15BInstruct",
        "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        "qwen2.5-1.5b",
    ),
    (
        "SmolLM2_360MInstruct",
        "HuggingFaceTB/SmolLM2-360M-Instruct-GGUF",
        "smollm2-360m",
    ),
    (
        "SmolLM2_17BInstruct",
        "HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF",
        "smollm2-1.7b",
    ),
    (
        "Phi4MiniInstructModel",
        "unsloth/Phi-4-mini-instruct-GGUF",
        "phi4-mini",
    ),
)

#: Checkpoint-specific params layered over the sampling profile. Phi-4 needs an
#: explicit quantization because its repo ships several GGUF files.
_EXTRA_CHECKPOINT_PARAMS: dict[str, dict[str, Any]] = {
    "Phi4MiniInstructModel": {
        "model_name": "unsloth/Phi-4-mini-instruct-GGUF",
        "quantization": "Phi-4-mini-instruct.Q8_0.gguf",
    },
}

#: Two configs per checkpoint class (``<base>-concise`` / ``<base>-creative``).
LLM_CONFIGS = [
    {
        "component_class": component_class,
        "model_name": model_name,
        "config_name": f"{base_config_name}-{profile_name}",
        "params": {
            **_EXTRA_CHECKPOINT_PARAMS.get(component_class, {}),
            **profile_params,
        },
    }
    for component_class, model_name, base_config_name in _LLM_CHECKPOINTS
    for profile_name, profile_params in _SAMPLING_PROFILES.items()
]


def _ensure_phi4_checkpoint(params: dict, *, download: bool) -> None:
    """Gate Phi-4's GGUF download before the load timer starts.

    ``Phi4MiniInstructModel`` uses ``llama_cpp.Llama.from_pretrained`` and is
    not an ``HFDownloadableMixin``, so the generic component gate cannot see
    it. Resolve its file from the Hugging Face cache here instead: fail under
    ``--no-download`` when missing, and download it before the timer otherwise.

    Parameters
    ----------
    params : dict
        Phi-4 parameters carrying ``model_name`` and ``quantization``.
    download : bool
        Whether a missing file may be downloaded.
    """
    from huggingface_hub import hf_hub_download, try_to_load_from_cache

    repo_id = params.get("model_name")
    filename = params.get("quantization")
    if not repo_id or not filename:
        raise RuntimeError(
            "Phi4MiniInstructModel needs 'model_name' and 'quantization' to "
            "locate its GGUF checkpoint."
        )
    cached = try_to_load_from_cache(repo_id=repo_id, filename=filename)
    if isinstance(cached, str):
        return
    if not download:
        raise RuntimeError(
            f"Phi4MiniInstructModel artifact '{repo_id}/{filename}' is missing "
            "from the Hugging Face cache. Re-run without --no-download to fetch "
            "it, or download it in the DashAI app first."
        )
    print(f"  Downloading Phi4MiniInstructModel ({repo_id}/{filename})...")
    hf_hub_download(repo_id=repo_id, filename=filename)


def _execute_llm(
    cfg: dict, *, download_missing_models: bool = True
) -> tuple[str, float, float, str]:
    """Benchmark a single LLM config, returning (status, exec, load, error)."""
    class_name = cfg["component_class"]
    params = dict(cfg["params"])
    for key in _BOOKKEEPING_KEYS:
        params.pop(key, None)

    LLMClass = load_component_class(LLM_MAP, class_name)

    ensure_component_downloaded(LLMClass, download=download_missing_models)
    if class_name == PHI4_COMPONENT:
        _ensure_phi4_checkpoint(params, download=download_missing_models)

    model = None
    try:
        with Timer() as load_timer:
            model = LLMClass(**params)

        prompt = [
            {
                "role": "system",
                "content": LLM_SYSTEM_PROMPT,
            },
            MULTI_TURN_CONVERSATION[0],
        ]

        with Timer() as exec_timer:
            output = model.generate(prompt)
    finally:
        if model is not None:
            close = getattr(model, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    log.warning("Failed to close %s after the benchmark.", class_name)

    assert isinstance(output, list), f"Expected list, got {type(output)}"
    assert len(output) > 0, "Expected at least one response"
    assert isinstance(output[0], str), f"Expected str, got {type(output[0])}"
    assert output[0].strip(), "Response is empty"

    return "passed", exec_timer.elapsed, load_timer.elapsed, ""


def _resolve_llm_device(device: str) -> str:
    """Resolve the ``device`` CLI value to a value accepted by LLM schemas.

    ``auto`` (the CLI default) resolves to the first llama.cpp GPU device and
    falls back to ``CPU`` when llama.cpp reports none; ``GPU``/``CUDA`` are
    aliases for the same device and fail loudly when there is none, so an
    explicit request never silently runs on the CPU. ``CPU`` is normalized to
    its canonical uppercase form, and an unknown value fails before a single
    model is loaded.

    Parameters
    ----------
    device : str
        Raw ``--device`` value: ``auto``, ``CPU``, ``GPU`` or ``CUDA``.

    Returns
    -------
    str
        ``CPU`` or the llama.cpp GPU label.

    Raises
    ------
    ValueError
        If the value is unknown, or a GPU was requested but llama.cpp has
        none.
    """
    from RAG_benchmark.app.device import resolve_requested_device

    return resolve_requested_device(device)


def run_all_llm_benchmarks(
    logger,
    iterations: int = 1,
    device: str = "CPU",
    skip_passes: bool = False,
    results_dir: Optional[Path] = None,
    download_missing_models: bool = True,
) -> None:
    """Run all LLM benchmarks, optionally skipping previously passed configs.

    Parameters
    ----------
    logger : BenchmarkLogger
    iterations : int
        Number of iterations per config.
    device : str
        Device for local LLM inference; ``CUDA`` is resolved to the first
        available llama.cpp GPU device (falling back to ``CPU``).
    skip_passes : bool
        If True, skip configs that passed in the last benchmark run.
    results_dir : Path or None
        Base results directory scanned for previous runs (falls back to
        the logger's output directory when None).
    download_missing_models : bool
        If True, download missing GGUF artifacts before loading. If False, a
        missing model fails that execution instead (``--no-download``).
    """
    device = _resolve_llm_device(device)
    statuses = (
        load_last_run_statuses(results_dir or logger.output_dir)
        if skip_passes
        else None
    )
    for iteration in range(1, iterations + 1):
        configs = []
        for cfg in LLM_CONFIGS:
            c = copy.deepcopy(cfg)
            c.setdefault("params", {})["iteration"] = iteration
            c.setdefault("params", {})["total_iterations"] = iterations
            c.setdefault("params", {})["device"] = device
            configs.append(c)
        execute_fn = functools.partial(
            _execute_llm, download_missing_models=download_missing_models
        )
        run_configs(configs, "llm", execute_fn, logger, skip_statuses=statuses)

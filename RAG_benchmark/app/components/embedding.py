"""Embedding component benchmarks generated from the registered converters.

The configs are derived from ``TEXT_EMBEDDING_CONVERTERS`` instead of a
hand-maintained list, so a new text embedding converter is benchmarked as soon
as it is registered. Each converter gets a default and an alternate
configuration whose options differ in batching, normalization and the overflow
strategy, so the reported times compare two realistic uses of the same model.

Converters that call a remote embedding service declare
``REQUIRES_API_KEY = True``. Their configs record an empty ``api_key``; the
converter reads the environment credential at encode time, so no secret is
written to a results file or copied into the logged config.
"""

from __future__ import annotations

import copy
import functools
import os
from pathlib import Path
from typing import Any, Optional

import numpy as np

from DashAI.back.converters.hugging_face.text_embedding import (
    TEXT_EMBEDDING_CONVERTERS,
)
from DashAI.back.converters.hugging_face.text_embedding.transformer import (
    DEFAULT_POOLING_STRATEGY,
    MAX,
)
from DashAI.back.converters.hugging_face.text_embedding_roles import PASSAGE
from DashAI.back.core.schema_fields.utils import schema_placeholder_defaults
from RAG_benchmark.app.benchmark_data import load_paper_texts
from RAG_benchmark.app.benchmark_utils import (
    Timer,
    ensure_component_downloaded,
    load_last_run_statuses,
    run_configs,
)
from RAG_benchmark.app.components.retrieval import (
    ITERATION_KEY,
    TOTAL_ITERATIONS_KEY,
    _component_class,
)
from RAG_benchmark.app.device import resolve_requested_device, supports_device_label

#: Device an embedding config falls back to when its converter cannot run on
#: the resolved one. Torch-backed converters declare the torch device enum,
#: which on this machine holds ``"CPU"`` alone because the benchmark's torch
#: build is CPU-only; only the GGUF converter exposes the llama.cpp GPU label.
EMBEDDING_DEVICE = "CPU"

#: Suffix and parameters of the two configurations every converter gets.
DEFAULT_CONFIG_SUFFIX = "default"
ALTERNATE_CONFIG_SUFFIX = "alternate"

DEFAULT_EMBEDDING_PARAMS: dict[str, Any] = {
    "device": EMBEDDING_DEVICE,
    "batch_size": 32,
    "normalize": True,
    "overflow_strategy": "truncate",
}

ALTERNATE_EMBEDDING_PARAMS: dict[str, Any] = {
    "device": EMBEDDING_DEVICE,
    "batch_size": 16,
    "normalize": False,
    "overflow_strategy": "aggregate",
}

#: Pooling strategy of the alternate profile.
ALTERNATE_POOLING_STRATEGY = MAX

#: Parameter key of the pooling strategy.
POOLING_STRATEGY_KEY = "pooling_strategy"

#: Character spans encoded per execution. The first span is long enough to make
#: the aggregate profile split it into several token windows; the second is a
#: disjoint short span, so the batch is not the same text twice.
PASSAGE_SPANS = ((0, 2500), (2500, 2700))

#: Tolerance of the unit-norm assertion on normalized vectors.
NORM_TOLERANCE = 1e-3

#: Parameter a remote converter takes its credential through.
API_KEY_PARAM = "api_key"

#: Environment variable that supplies the OpenAI credential. It is read at
#: execution time, never while the configs are built, so no key reaches a log.
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"


def _embedding_config(
    converter: type, suffix: str, params: dict[str, Any]
) -> dict[str, Any]:
    """Return one embedding benchmark config for *converter*.

    Parameters
    ----------
    converter : type
        A registered text embedding converter class.
    suffix : str
        Configuration name appended to the class name.
    params : dict[str, Any]
        Converter parameters, completed with the pooling strategy when the
        converter exposes one.

    Returns
    -------
    dict[str, Any]
        The benchmark config.
    """
    # The converter schemas fill nothing in, so the config is completed with the
    # placeholders the browser form also seeds (for example the INSTRUCTOR
    # ``instruction``) before the benchmark options are applied.
    config_params = {**schema_placeholder_defaults(converter), **params}
    # A remote converter takes a credential, but the logged config must always
    # carry the empty placeholder: the executor reads the real value from the
    # environment so no secret reaches a results file.
    if API_KEY_PARAM in config_params:
        config_params[API_KEY_PARAM] = ""
    if getattr(converter, "POOLING_STRATEGIES", None):
        config_params[POOLING_STRATEGY_KEY] = (
            DEFAULT_POOLING_STRATEGY
            if suffix == DEFAULT_CONFIG_SUFFIX
            else ALTERNATE_POOLING_STRATEGY
        )
    return {
        "component_class": converter.__name__,
        "model_name": converter.MODEL_NAME,
        "config_name": f"{converter.__name__}-{suffix}",
        "params": config_params,
    }


def _embedding_device(converter: type, device: str) -> str:
    """Return the device label *converter* should be benchmarked on.

    Only converters whose schema accepts the resolved llama.cpp GPU label are
    offloaded -- `E5MistralGGUFEmbedding` declares the llama.cpp device enum,
    while torch-backed converters declare the torch one, which on the
    benchmark's CPU-only torch build contains ``"CPU"`` alone.

    Parameters
    ----------
    converter : type
        A registered text embedding converter class.
    device : str
        Device of the run, already resolved to ``CPU`` or a llama.cpp GPU
        label.

    Returns
    -------
    str
        The label to write into the converter parameters.
    """
    if device != EMBEDDING_DEVICE and supports_device_label(converter, device):
        return device
    return EMBEDDING_DEVICE


def _build_embedding_configs(device: str = EMBEDDING_DEVICE) -> list[dict[str, Any]]:
    """Return two benchmark configs per registered text embedding converter.

    Parameters
    ----------
    device : str
        Device of the run; each converter keeps it only when its schema
        accepts it, and falls back to the CPU otherwise.

    Returns
    -------
    list[dict[str, Any]]
        The benchmark configs.
    """
    configs: list[dict[str, Any]] = []
    for converter in TEXT_EMBEDDING_CONVERTERS:
        converter_device = _embedding_device(converter, device)
        for suffix, params in (
            (DEFAULT_CONFIG_SUFFIX, DEFAULT_EMBEDDING_PARAMS),
            (ALTERNATE_CONFIG_SUFFIX, ALTERNATE_EMBEDDING_PARAMS),
        ):
            configs.append(
                _embedding_config(
                    converter, suffix, {**params, "device": converter_device}
                )
            )
    return configs


#: Every embedding configuration the benchmark executes, with the CPU device.
#: :func:`run_all_embedding_benchmarks` rebuilds the matrix with the device the
#: run resolved to.
EMBEDDING_CONFIGS = _build_embedding_configs()


def _sample_passages() -> list[str]:
    """Return the two disjoint paper spans every embedding config encodes."""
    paper_text = load_paper_texts(max_docs=1)[0]
    assert len(paper_text) >= PASSAGE_SPANS[-1][1], (
        "The benchmark paper is shorter than the embedding sample spans; "
        "add a longer paper or reduce PASSAGE_SPANS."
    )
    return [paper_text[start:end] for start, end in PASSAGE_SPANS]


def _ensure_api_key(component_class: type, params: dict[str, Any]) -> None:
    """Check a remote converter has a credential without copying it into params.

    Parameters
    ----------
    component_class : type
        The converter about to be instantiated.
    params : dict[str, Any]
        Local copy of the config parameters.

    Raises
    ------
    RuntimeError
        If the converter requires an API key and neither the parameters nor the
        environment provide one.
    """
    if not getattr(component_class, "REQUIRES_API_KEY", False):
        return
    if params.get(API_KEY_PARAM) or os.environ.get(OPENAI_API_KEY_ENV, ""):
        return
    raise RuntimeError(
        f"{component_class.__name__} requires an API key but neither the "
        f"component parameters nor {OPENAI_API_KEY_ENV} provide one."
    )


def _execute_embedding(
    cfg: dict,
    *,
    download_missing_models: bool = True,
    passages: Optional[list[str]] = None,
) -> tuple[str, float, float, str]:
    """Benchmark one embedding config, returning ``(status, exec, load, error)``.

    The model is downloaded before the load timer starts, then instantiated and
    loaded inside it, so the reported load time is model loading only. A remote
    converter receives its credential from the environment here, on the local
    params copy, so the logged config keeps its empty placeholder.

    Parameters
    ----------
    cfg : dict
        Benchmark config carrying ``component_class`` and ``params``.
    download_missing_models : bool
        When False, a missing model fails the execution instead of being
        downloaded.

    Returns
    -------
    tuple[str, float, float, str]
        Status, encoding time, load time and error message (empty on success).
    """
    component_class = _component_class(cfg["component_class"])
    params = copy.deepcopy(cfg.get("params") or {})
    params.pop(ITERATION_KEY, None)
    params.pop(TOTAL_ITERATIONS_KEY, None)

    _ensure_api_key(component_class, params)

    passages = _sample_passages() if passages is None else passages

    ensure_component_downloaded(component_class, download=download_missing_models)

    with Timer() as load_timer:
        embedding = component_class(**params)
        embedding.pretrained()

    with Timer() as exec_timer:
        vectors = embedding.encode(passages, role=PASSAGE)

    assert isinstance(vectors, np.ndarray), (
        f"Expected ndarray, got {type(vectors).__name__}"
    )
    assert vectors.ndim == 2, f"Expected 2-D, got {vectors.ndim}D"
    assert vectors.shape[0] == len(passages), (
        f"Expected {len(passages)} rows, got {vectors.shape[0]}"
    )
    assert vectors.shape[1] > 0, f"Expected positive dimension, got {vectors.shape[1]}"
    assert vectors.dtype == np.float32, f"Expected float32 vectors, got {vectors.dtype}"
    assert np.isfinite(vectors).all(), "Embedding contains non-finite values"
    if embedding.normalize:
        norms = np.linalg.norm(vectors, axis=1)
        assert np.allclose(norms, 1.0, atol=NORM_TOLERANCE), (
            f"Expected unit-norm rows, got norms {norms}"
        )

    return "passed", exec_timer.elapsed, load_timer.elapsed, ""


def run_all_embedding_benchmarks(
    logger,
    iterations: int = 1,
    device: str = "CPU",
    skip_passes: bool = False,
    results_dir: Optional[Path] = None,
    download_missing_models: bool = True,
) -> None:
    """Run all embedding benchmarks, optionally skipping previously passed configs.

    Parameters
    ----------
    logger : BenchmarkLogger
    iterations : int
        Number of iterations per config.
    device : str
        Device of the run: ``auto``, ``CPU``, ``GPU`` or ``CUDA``. It is
        resolved to a llama.cpp GPU label and applied to every converter whose
        schema accepts that label (the GGUF converter); torch-backed
        converters stay on the CPU.
    skip_passes : bool
        If True, skip configs that passed in the last benchmark run.
    results_dir : Path or None
        Base results directory scanned for previous runs (falls back to
        the logger's output directory when None).
    download_missing_models : bool
        If True, download missing model artifacts before loading. If False, a
        missing model fails that execution instead (``--no-download``).
    """
    resolved_device = resolve_requested_device(device)
    statuses = (
        load_last_run_statuses(results_dir or logger.output_dir)
        if skip_passes
        else None
    )
    passages = _sample_passages()
    execute_fn = functools.partial(
        _execute_embedding,
        download_missing_models=download_missing_models,
        passages=passages,
    )
    for iteration in range(1, iterations + 1):
        configs = []
        for cfg in _build_embedding_configs(resolved_device):
            prepared = copy.deepcopy(cfg)
            prepared.setdefault("params", {})[ITERATION_KEY] = iteration
            prepared.setdefault("params", {})[TOTAL_ITERATIONS_KEY] = iterations
            configs.append(prepared)
        run_configs(configs, "embedding", execute_fn, logger, skip_statuses=statuses)

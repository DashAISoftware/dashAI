"""Base class for pipeline benchmark execution.

Creates a DashAI app in-process with TestClient, manages test documents,
creates generative sessions via the API, orchestrates multi-turn
conversations, and records detailed timing and results.

Uses real PDF papers from RAG_benchmark/papers/ as document sources.
Documents are created and parsed through the current DashAI Data module
(``POST /api/v1/documents`` + ``POST /api/v1/job`` with a ``DocumentJob``)
and are attached to the RAG session with
``POST /api/v1/rag/sessions/{id}/documents`` after the session is created.
Every session loads all discovered papers as its conversation corpus;
iterations are independent conversations over that complete corpus.
"""

from __future__ import annotations

import copy
import json as _json
import logging
import math
import os
import time as _time
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
)

from fastapi.testclient import TestClient

from DashAI.back.app import create_app
from DashAI.back.core.enums.status import DocumentStatus, RunStatus
from DashAI.back.dependencies.config_builder import build_config_dict
from DashAI.back.dependencies.job_queues.huey_job_queue import HueyJobQueue
from RAG_benchmark.app.benchmark_data import (
    DOCUMENT_LOADER_PARAMS,
    discover_benchmark_paper_files,
)
from RAG_benchmark.app.benchmark_utils import ensure_component_downloaded
from RAG_benchmark.app.config import BenchmarkConfig
from RAG_benchmark.app.device import (
    AUTO_DEVICE,
    DevicePlan,
    apply_device_plan,
    default_device_priority,
    detect_out_of_memory,
    display_path,
    format_bytes_as_gib,
    largest_gpu_assignment,
    plan_device_assignments,
    vram_budget_bytes,
)
from RAG_benchmark.app.models import PipelineRunResult, TurnRecord
from RAG_benchmark.app.pipelines.writer import PipelineResultsWriter

if TYPE_CHECKING:
    # ``conversation`` imports the optional ``openai`` package, so it is only
    # imported at runtime inside :meth:`PipelineBenchmarkRunner.setup`. Keep
    # the symbol available to type checkers without making it a hard import.
    from RAG_benchmark.app.conversation import UserSimulator

log = logging.getLogger(__name__)

#: Registry name of the document loader used to parse benchmark PDFs.
DOCUMENT_DATALOADER = "PypdfDocumentDataLoader"

#: Loader parameters, shared with the component benchmarks so a pipeline and a
#: chunker row are always parsed from the same text shape.
DOCUMENT_DATALOADER_PARAMS: Dict[str, Any] = dict(DOCUMENT_LOADER_PARAMS)

#: How long a freshly enqueued ``DocumentJob`` is polled before giving up.
_DOCUMENT_POLL_ATTEMPTS = 60
_DOCUMENT_POLL_INTERVAL_S = 0.5

#: Parameter a remote component takes its credential through.
API_KEY_PARAM = "api_key"

#: Environment variable that supplies the OpenAI credential.
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"

#: Cross-encoder retriever: its checkpoint is a *parameter*, not a component
#: class, so ``ensure_component_downloaded`` cannot see it.
CROSS_ENCODER_RETRIEVER_COMPONENT = "SentenceTransformerCrossEncoderRetriever"

#: Parameter holding the Hugging Face checkpoint id of the cross-encoder.
MODEL_NAME_PARAM = "model_name"

#: Key under which the recorded config of an iteration stores the device plan
#: and the out-of-memory demotions applied to it, so the device that was
#: actually used stays inspectable in ``configs.json``.
DEVICE_PLAN_CONFIG_KEY = "device_plan"

#: Run id of a retried attempt of an iteration, e.g. ``iter0-retry1``. The
#: first attempt keeps the plain ``iter<iteration>`` id.
RETRY_RUN_ID_TEMPLATE = "iter{iteration}-retry{attempt}"


def _redact_secrets(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deep copy of ``params`` with API keys replaced by empty strings.

    Every value under an ``api_key`` or ``API_key`` key is redacted,
    recursively, including values nested inside lists. The input dict is
    never mutated.

    Parameters
    ----------
    params : dict[str, Any]
        The parameters to redact.

    Returns
    -------
    dict[str, Any]
        A deep copy of ``params`` with API key values set to ``""``.
    """
    redacted = copy.deepcopy(params)

    def _redact(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in ("api_key", "API_key"):
                    obj[key] = ""
                else:
                    _redact(value)
        elif isinstance(obj, list):
            for item in obj:
                _redact(item)

    _redact(redacted)
    return redacted


def _iter_component_refs(node: Any) -> Iterator[Dict[str, Any]]:
    """Yield every nested ``{"component": ...}`` reference in *node*.

    Walks dicts and lists recursively, so a component ref nested inside a
    list inside a parameter dict is found. The input is never mutated.

    Parameters
    ----------
    node : Any
        Parameter tree to scan.

    Yields
    ------
    dict[str, Any]
        Each dict that carries a ``component`` key.
    """
    if isinstance(node, dict):
        if "component" in node:
            yield node
        for value in node.values():
            yield from _iter_component_refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_component_refs(item)


def _iter_tokenizer_names(node: Any) -> Iterator[str]:
    """Yield every non-empty ``tokenizer_name`` found in *node*.

    Parameters
    ----------
    node : Any
        Parameter tree to scan.

    Yields
    ------
    str
        Each tokenizer checkpoint named by a chunker parameter.
    """
    if isinstance(node, dict):
        tokenizer_name = node.get("tokenizer_name")
        if isinstance(tokenizer_name, str) and tokenizer_name:
            yield tokenizer_name
        for value in node.values():
            yield from _iter_tokenizer_names(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_tokenizer_names(item)


def _iter_cross_encoder_models(node: Any) -> Iterator[str]:
    """Yield every cross-encoder checkpoint named in *node*.

    Parameters
    ----------
    node : Any
        Parameter tree to scan.

    Yields
    ------
    str
        Each non-empty ``model_name`` of a cross-encoder retriever reference.
    """
    for ref in _iter_component_refs(node):
        if ref.get("component") != CROSS_ENCODER_RETRIEVER_COMPONENT:
            continue
        model_name = (ref.get("params") or {}).get(MODEL_NAME_PARAM)
        if isinstance(model_name, str) and model_name:
            yield model_name


def ensure_api_key_available(
    name: str, component_class: Any, ref: Dict[str, Any]
) -> None:
    """Ensure a remote component reference carries an API key before any turn.

    Components that call a remote service declare ``REQUIRES_API_KEY = True``.
    The pipeline configs keep the ``api_key`` parameter empty so the secret never
    reaches the session payload; the converter reads ``OPENAI_API_KEY`` at encode
    time. This pre-flight therefore accepts either source and fails before a
    single document is embedded when neither provides a credential, keeping the
    failure out of the per-turn timings.

    Parameters
    ----------
    name : str
        Registry name of the component, used in the error message.
    component_class : Any
        The registered class the reference resolves to.
    ref : dict[str, Any]
        The ``{"component", "params"}`` reference being validated.

    Raises
    ------
    RuntimeError
        If the component requires an API key and the reference declares none.
    """
    if not getattr(component_class, "REQUIRES_API_KEY", False):
        return
    api_key = (ref.get("params") or {}).get(API_KEY_PARAM)
    if api_key or os.environ.get(OPENAI_API_KEY_ENV, ""):
        return
    raise RuntimeError(
        f"{name} requires an API key and neither the component parameters nor "
        f"the {OPENAI_API_KEY_ENV} environment variable provide one. Set "
        f"{OPENAI_API_KEY_ENV} before running the benchmark."
    )


def ensure_tokenizer_available(tokenizer_name: str, *, download: bool) -> None:
    """Ensure a chunker tokenizer is cached before the first turn.

    ``TokenChunkModel`` loads its tokenizer lazily on the first ``chunk_text``
    call. Doing that inside the first turn would count the download as indexing
    time, so the pipeline pre-flight resolves it here instead.

    Parameters
    ----------
    tokenizer_name : str
        Hugging Face tokenizer repo id.
    download : bool
        When False, a missing tokenizer raises instead of downloading.

    Raises
    ------
    RuntimeError
        If the tokenizer is missing and ``download`` is False.
    """
    from transformers import AutoTokenizer

    try:
        AutoTokenizer.from_pretrained(tokenizer_name, local_files_only=True)
        return
    except Exception:
        if not download:
            raise RuntimeError(
                f"Tokenizer '{tokenizer_name}' is missing from the Hugging Face "
                "cache. Re-run without --no-download to fetch it, or download "
                "it before the benchmark."
            ) from None
    print(f"  Downloading tokenizer ({tokenizer_name})...")
    AutoTokenizer.from_pretrained(tokenizer_name)


def ensure_cross_encoder_available(model_name: str, *, download: bool) -> None:
    """Ensure a cross-encoder checkpoint is cached before the first turn.

    ``SentenceTransformerCrossEncoderRetriever`` takes its checkpoint as a
    ``model_name`` parameter instead of being a downloadable DashAI component,
    so ``ensure_component_downloaded`` never sees it and the first turn would
    otherwise pay for the download inside its own timings. The pre-flight
    resolves the checkpoint here instead.

    Parameters
    ----------
    model_name : str
        Hugging Face repo id of the cross-encoder.
    download : bool
        When False, a missing checkpoint raises instead of downloading.

    Raises
    ------
    RuntimeError
        If the checkpoint is missing and ``download`` is False.
    """
    from huggingface_hub import snapshot_download

    try:
        snapshot_download(repo_id=model_name, local_files_only=True)
        return
    except Exception:
        if not download:
            raise RuntimeError(
                f"Cross-encoder artifacts for '{model_name}' are missing from "
                "the Hugging Face cache. Re-run without --no-download to fetch "
                "them, or download them in the DashAI app first."
            ) from None
    print(f"  Downloading cross-encoder ({model_name})...")
    snapshot_download(repo_id=model_name)


def _pipeline_success(
    pipeline_error: Optional[str],
    turn_records: List[TurnRecord],
) -> Tuple[bool, Optional[str]]:
    """Determine the pipeline success flag and an accompanying message.

    Parameters
    ----------
    pipeline_error : str or None
        Error raised at the pipeline iteration level, if any.
    turn_records : list[TurnRecord]
        Turn records collected during the iteration.

    Returns
    -------
    tuple[bool, str or None]
        Success flag and message (``None`` when fully successful).
    """
    if pipeline_error is not None:
        return False, pipeline_error
    if not turn_records:
        return False, "No turns were recorded."
    if all(t.error is not None for t in turn_records):
        return False, "All turns failed."
    failed = 0
    for turn in turn_records:
        if turn.error is not None:
            failed += 1
    if failed:
        return True, f"{failed} of {len(turn_records)} turns failed."
    return True, None


@dataclass(frozen=True)
class ProcessOutputParse:
    """Typed result of parsing a finished RAG process output.

    Attributes
    ----------
    message : str
        The assistant answer, read from the ``str`` row.
    chunks_retrieved : int
        Number of retrieved chunks, read from the ``Dict`` row.
    retrieved_chunks : Any
        The parsed chunk payload (a dict or a list), or ``{}`` when absent.
    queries : list[str]
        The queries the retrieval ran over, read from the ``Queries`` row.
    trace : Any
        The parsed per-query retrieval trace, or ``None`` when absent.
    transformation_time_ms : float
        Query-transformation stage time (0.0 when disabled or unavailable).
    retrieval_time_ms : float
        Retrieval stage time (0.0 in the legacy fallback).
    generation_time_ms : float
        Generation stage time, or the whole-turn wall clock in the legacy
        fallback.
    used_legacy_timings : bool
        True when no valid ``Timings`` row was present and the wall-clock
        fallback was applied.
    """

    message: str = ""
    chunks_retrieved: int = 0
    retrieved_chunks: Any = field(default_factory=dict)
    queries: List[str] = field(default_factory=list)
    trace: Any = None
    transformation_time_ms: float = 0.0
    retrieval_time_ms: float = 0.0
    generation_time_ms: float = 0.0
    used_legacy_timings: bool = False


#: ``data_type`` values the five-row parser understands.
_RECOGNIZED_DATA_TYPES = frozenset({"Queries", "Dict", "Trace", "Timings", "str"})

#: Keys a valid ``Timings`` row must carry, all as finite real numbers.
_TIMING_KEYS = ("transformation_ms", "retrieval_ms", "generation_ms", "total_ms")


def _row_data(row: Any) -> Any:
    """Return the ``data`` field of a serialized ``ProcessData`` row."""
    return row.get("data") if isinstance(row, dict) else None


def _first_typed_row(rows: List[Any], data_type: str) -> Optional[Dict[str, Any]]:
    """Return the first row whose ``data_type`` matches, or ``None``."""
    for row in rows:
        if isinstance(row, dict) and row.get("data_type") == data_type:
            return row
    return None


def _has_typed_rows(rows: List[Any]) -> bool:
    """Return True when any row carries a recognized ``data_type``.

    A payload is either fully typed (at least one recognized row) or a truly
    untyped legacy payload (no recognized row at all). ``None`` and unknown
    ``data_type`` values do not count as typed.
    """
    for row in rows:
        if isinstance(row, dict) and row.get("data_type") in _RECOGNIZED_DATA_TYPES:
            return True
    return False


def _coerce_json(raw: Any) -> Any:
    """Parse ``raw`` as JSON, returning ``None`` when it is not valid JSON.

    A value that is already a dict or list is returned unchanged.
    """
    if isinstance(raw, (dict, list)):
        return raw
    if isinstance(raw, str) and raw:
        try:
            return _json.loads(raw)
        except (ValueError, TypeError):
            return None
    return None


def _is_finite_number(value: Any) -> bool:
    """Return True for a finite real number (bool, NaN and Inf are rejected)."""
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return math.isfinite(value)


def _parse_timings(raw: Any) -> Optional[Tuple[float, float, float]]:
    """Validate and unpack a ``Timings`` row.

    The key contract is strict: a valid row is a dict carrying **all four**
    keys (``transformation_ms``, ``retrieval_ms``, ``generation_ms``,
    ``total_ms``) whose values are finite real numbers. Anything else
    (missing or renamed keys, strings, bools, NaN/Infinity) is invalid and the
    caller must fall back to the legacy whole-turn timing behaviour.

    Returns
    -------
    tuple[float, float, float] or None
        ``(transformation_ms, retrieval_ms, generation_ms)`` when valid,
        otherwise ``None``.
    """
    if not isinstance(raw, dict):
        return None
    for key in _TIMING_KEYS:
        if key not in raw or not _is_finite_number(raw[key]):
            return None
    return (
        float(raw["transformation_ms"]),
        float(raw["retrieval_ms"]),
        float(raw["generation_ms"]),
    )


def _parse_process_output(
    result_data: Dict[str, Any],
    total_turn_ms: float = 0.0,
) -> ProcessOutputParse:
    """Extract the answer, chunks, queries, trace and timings from a result.

    Rows are selected by their ``data_type`` (``Queries``, ``Dict``,
    ``Trace``, ``Timings``, ``str``), never by position, so the parser
    tolerates row reordering. A payload is either **typed** (it carries at
    least one recognized ``data_type`` row) or a **truly untyped legacy**
    payload (it carries no recognized row at all). The legacy positional
    fallback (``output[0]`` is the message, ``output[1]`` the chunks) applies
    *only* to truly untyped payloads; when typed rows exist but the expected
    one is absent, ``message`` / ``chunks_retrieved`` are left empty instead
    of misreading an unrelated row.

    A ``Timings`` row is honoured only when it is a dict carrying all four
    keys (``transformation_ms``, ``retrieval_ms``, ``generation_ms``,
    ``total_ms``) whose values are finite real numbers (bools, NaN,
    ±Infinity and strings are rejected). When no valid ``Timings`` row is
    present the legacy timing behaviour applies: generation time is the
    whole-turn wall clock and retrieval/transformation are ``0.0``.

    Parameters
    ----------
    result_data : dict[str, Any]
        The finished process payload.
    total_turn_ms : float
        Wall-clock duration of the whole turn, used as the generation-time
        fallback when the ``Timings`` row is missing.

    Returns
    -------
    ProcessOutputParse
        The typed, testable parse result.
    """
    if not isinstance(result_data, dict):
        return ProcessOutputParse()

    output_raw = result_data.get("output", [])
    rows: List[Any] = output_raw if isinstance(output_raw, list) else []

    typed_rows_present = _has_typed_rows(rows)

    message = ""
    str_rows: List[Any] = []
    for row in rows:
        if isinstance(row, dict) and row.get("data_type") == "str":
            str_rows.append(row)
    if str_rows:
        for row in reversed(str_rows):
            value = _row_data(row)
            if value is not None and str(value) != "":
                message = str(value)
                break
    elif not typed_rows_present and rows:
        value = _row_data(rows[0])
        message = "" if value is None else str(value)

    chunks_row = _first_typed_row(rows, "Dict")
    if chunks_row is None and not typed_rows_present and len(rows) > 1:
        chunks_row = rows[1]
    chunks_retrieved = 0
    retrieved_chunks: Any = {}
    if chunks_row is not None:
        parsed_chunks = _coerce_json(_row_data(chunks_row))
        if isinstance(parsed_chunks, (dict, list)):
            chunks_retrieved = len(parsed_chunks)
            retrieved_chunks = parsed_chunks

    queries: List[str] = []
    queries_row = _first_typed_row(rows, "Queries")
    if queries_row is not None:
        parsed_queries = _coerce_json(_row_data(queries_row))
        if isinstance(parsed_queries, list):
            queries = [str(query) for query in parsed_queries]

    trace: Any = None
    trace_row = _first_typed_row(rows, "Trace")
    if trace_row is not None:
        parsed_trace = _coerce_json(_row_data(trace_row))
        if isinstance(parsed_trace, (dict, list)):
            trace = parsed_trace

    transformation_time_ms = 0.0
    retrieval_time_ms = 0.0
    generation_time_ms = 0.0
    used_legacy_timings = True
    timings_row = _first_typed_row(rows, "Timings")
    if timings_row is not None:
        parsed_timings = _parse_timings(_coerce_json(_row_data(timings_row)))
        if parsed_timings is not None:
            transformation_time_ms, retrieval_time_ms, generation_time_ms = (
                parsed_timings
            )
            used_legacy_timings = False

    if used_legacy_timings:
        generation_time_ms = float(total_turn_ms)
        log.warning(
            "Process output has no valid 'Timings' row; falling back to the "
            "whole-turn wall clock for generation_time_ms."
        )

    return ProcessOutputParse(
        message=message,
        chunks_retrieved=chunks_retrieved,
        retrieved_chunks=retrieved_chunks,
        queries=queries,
        trace=trace,
        transformation_time_ms=transformation_time_ms,
        retrieval_time_ms=retrieval_time_ms,
        generation_time_ms=generation_time_ms,
        used_legacy_timings=used_legacy_timings,
    )


def _aggregate_stats(
    turn_records: List[TurnRecord],
) -> Tuple[float, float, float, float]:
    """Compute average transformation, retrieval, generation and turn times.

    Transformation, retrieval and generation averages use only successful
    turns; the total-turn average uses every recorded turn.

    Parameters
    ----------
    turn_records : list[TurnRecord]
        Turn records from one pipeline iteration.

    Returns
    -------
    tuple[float, float, float, float]
        Average transformation, retrieval, generation and total turn times
        in ms.
    """
    successful: List[TurnRecord] = []
    for turn in turn_records:
        if turn.error is None:
            successful.append(turn)

    if successful:
        avg_transformation = sum(t.transformation_time_ms for t in successful) / len(
            successful
        )
        avg_retrieval = sum(t.retrieval_time_ms for t in successful) / len(successful)
        avg_generation = sum(t.generation_time_ms for t in successful) / len(successful)
    else:
        avg_transformation = 0.0
        avg_retrieval = 0.0
        avg_generation = 0.0

    if turn_records:
        avg_turn = sum(t.total_turn_time_ms for t in turn_records) / len(turn_records)
    else:
        avg_turn = 0.0

    return avg_transformation, avg_retrieval, avg_generation, avg_turn


def _report_device_plan(pipeline_key: str, plan: DevicePlan) -> None:
    """Print and log a pipeline's device plan once, before its first turn.

    Parameters
    ----------
    pipeline_key : str
        Pipeline registry key, used as the report label.
    plan : DevicePlan
        The plan computed for the pipeline parameters.
    """
    device = plan.gpu_label or "CPU only"
    budget = format_bytes_as_gib(plan.budget_bytes) if plan.budget_bytes else "n/a"
    print(f"  Device plan ({pipeline_key}): {device}, budget {budget}")
    log.info("Device plan for %s: %s, budget %s", pipeline_key, device, budget)
    for note in plan.notes:
        print(f"    {note}")
        log.info("Device plan %s: %s", pipeline_key, note)


def _iteration_run_id(iteration: int, attempt: int) -> str:
    """Return the results id of one attempt of an iteration.

    Parameters
    ----------
    iteration : int
        Zero-based iteration index.
    attempt : int
        Zero-based attempt index within the iteration; a retry after an
        out-of-memory demotion gets a distinct id so no row of the failed
        attempt is overwritten.

    Returns
    -------
    str
        ``iter<iteration>`` for the first attempt, ``iter<i>-retry<n>`` after.
    """
    if attempt == 0:
        return f"iter{iteration}"
    return RETRY_RUN_ID_TEMPLATE.format(iteration=iteration, attempt=attempt)


def _iteration_session_name(
    base_name: str, run_tag: str, iteration: int, attempt: int
) -> str:
    """Return the unique GenerativeSession name of one attempt.

    The session name is UNIQUE in the database, so a retried attempt of the
    same iteration must not reuse the name of the attempt that failed.

    Parameters
    ----------
    base_name : str
        Name the pipeline config declared.
    run_tag : str
        Timestamp tag of the whole run.
    iteration : int
        Zero-based iteration index.
    attempt : int
        Zero-based attempt index within the iteration.

    Returns
    -------
    str
        The session name, e.g. ``"Pub 5a (run 240101120000, iter 0)"``.
    """
    suffix = f"retry {attempt}" if attempt else ""
    parts = ["run " + run_tag, f"iter {iteration}"]
    if suffix:
        parts.append(suffix)
    return f"{base_name} ({', '.join(parts)})"


def _out_of_memory_failure(
    pipeline_error: Optional[str],
    turn_records: List[TurnRecord],
) -> Optional[str]:
    """Return the first out-of-memory error of a failed attempt, if any.

    The failure may have aborted the iteration (session creation, document
    attach) or only some of its turns, because a failed turn is recorded
    instead of raised.

    Parameters
    ----------
    pipeline_error : str or None
        Error raised at the iteration level, if any.
    turn_records : list[TurnRecord]
        Turns recorded by the attempt.

    Returns
    -------
    str or None
        The matching error message, or ``None`` when the attempt did not fail
        on a GPU allocation.
    """
    candidates: List[str] = [pipeline_error] if pipeline_error else []
    candidates.extend(turn.error for turn in turn_records if turn.error)
    for candidate in candidates:
        if detect_out_of_memory(candidate):
            return candidate
    return None


def _device_plan_record(
    plan: DevicePlan, demoted: Sequence[Tuple[str, ...]]
) -> Dict[str, Any]:
    """Summarise a device plan for the recorded configuration.

    Parameters
    ----------
    plan : DevicePlan
        The plan applied to the attempt.
    demoted : sequence[tuple[str, ...]]
        References demoted to the CPU after an earlier out-of-memory failure.

    Returns
    -------
    dict[str, Any]
        JSON-ready summary of the plan, its notes and its demotions.
    """
    return {
        "gpu_label": plan.gpu_label,
        "budget_bytes": plan.budget_bytes,
        "assignments": {
            display_path(path): label for path, label in plan.assignments.items()
        },
        "notes": list(plan.notes),
        "demoted": [display_path(path) for path in demoted],
    }


def _recorded_config(
    params: Dict[str, Any],
    plan: Optional[DevicePlan],
    demoted: Sequence[Tuple[str, ...]],
) -> Dict[str, Any]:
    """Return the redacted config stored for one attempt, with its device plan.

    Parameters
    ----------
    params : dict[str, Any]
        The attempt's session payload.
    plan : DevicePlan or None
        The plan applied to it, or ``None`` when no payload was built.
    demoted : sequence[tuple[str, ...]]
        References demoted to the CPU after an earlier out-of-memory failure.

    Returns
    -------
    dict[str, Any]
        The config to persist; the device plan is only added when it planned
        at least one component.
    """
    config = _redact_secrets(params)
    if plan is not None and plan.assignments:
        config[DEVICE_PLAN_CONFIG_KEY] = _device_plan_record(plan, demoted)
    return config


def _report_demotion(
    path: Tuple[str, ...], iteration: int, attempt: int, error: str
) -> None:
    """Print and log one out-of-memory demotion.

    Parameters
    ----------
    path : tuple[str, ...]
        Parameter path of the component demoted to the CPU.
    iteration : int
        Zero-based iteration index being retried.
    attempt : int
        Zero-based index of the attempt that hit the out-of-memory failure.
    error : str
        The error message that triggered the demotion.
    """
    name = display_path(path)
    message = (
        f"  Out of memory with {name} on the GPU; retrying "
        f"iter{iteration} with it on CPU."
    )
    print(message)
    log.warning(
        "Out of memory with %s on the GPU (attempt %d of iteration %d): %s. "
        "Retrying with it on the CPU.",
        name,
        attempt,
        iteration,
        error,
    )


class PipelineBenchmarkRunner:
    """Runs a full pipeline benchmark with multi-turn conversation."""

    def __init__(
        self, config: BenchmarkConfig, requested_device: str = AUTO_DEVICE
    ) -> None:
        """
        Parameters
        ----------
        config : BenchmarkConfig
            Benchmark configuration.
        requested_device : str
            ``--device`` value of the run: ``auto``, ``CPU``, ``GPU`` or
            ``CUDA``. It is resolved to a label and then used as the budget of
            each pipeline's device plan. The plan only compares each
            component's weights with the free VRAM, because the pipeline
            releases every stage before the next one loads; an allocation that
            still runs out of memory is retried with that stage on the CPU.
        """
        self._config = config
        self._client: Optional[TestClient] = None
        self._document_ids: List[int] = []
        self._data_path: Optional[Path] = None
        self._user_simulator: Optional[UserSimulator] = None
        self._run_tag = _time.strftime("%y%m%d%H%M%S")
        self._requested_device = requested_device
        self._registry: Any = None
        self._gpu_budget_bytes = vram_budget_bytes()
        # Pipelines whose device plan was already printed; the plan is
        # recomputed every iteration but reported once per pipeline.
        self._device_reported: set[str] = set()

    def setup(self) -> None:
        """Create the DashAI app, TestClient, and load PDF papers as Data documents.

        The app runs on a permanent data directory
        (``BenchmarkConfig.data_dir``) instead of a temp folder: the SQLite
        DB and the RAG embeddings persist across runs, so chunk sets,
        embedding models and embedding matrices are recycled instead of
        recomputed. Data documents are keyed by name, so their ids remain
        stable between runs and later runs skip re-parsing.
        """
        self._data_path = self._config.data_dir
        self._data_path.mkdir(parents=True, exist_ok=True)

        app = create_app(local_path=self._data_path, logging_level="ERROR")
        # Models resolve from the shared DashAI component store (~/.DashAI/components
        # by default) instead of the benchmark data dir, so pipeline runs reuse
        # anything the app or the component benchmarks already downloaded.
        app.container["config"]["COMPONENT_PATH"] = build_config_dict(
            local_path=None, logging_level="ERROR"
        )["COMPONENT_PATH"]
        job_queue = app.container["job_queue"]
        if job_queue and isinstance(job_queue, HueyJobQueue):
            job_queue.set_test_mode(True)

        self._client = TestClient(app)
        self._registry = app.container["component_registry"]

        paper_files = discover_benchmark_paper_files(max_docs=None)
        if not paper_files:
            raise FileNotFoundError(
                f"No PDF papers found in {self._config.papers_dir}. "
                "Place PDF files in RAG_benchmark/papers/."
            )

        self._document_ids = self._ensure_documents(paper_files)
        if not self._document_ids:
            raise FileNotFoundError(
                f"No Data documents could be prepared from {self._config.papers_dir}."
            )

        from RAG_benchmark.app.conversation import UserSimulator

        if self._config.deepseek_api_key:
            self._user_simulator = UserSimulator.from_config(self._config)
        else:
            log.warning("No DeepSeek API key. Using fallback questions.")
            self._user_simulator = UserSimulator(
                api_key="", model=self._config.deepseek_model
            )

    def teardown(self) -> None:
        """Release the DB engine; keep the permanent data directory.

        Unlike the previous temp-folder behaviour, the data directory
        (SQLite DB + embeddings) is intentionally NOT deleted so that
        future runs recycle the cached chunk sets and embedding matrices.
        """
        import contextlib
        import gc

        if self._client:
            with contextlib.suppress(Exception):
                self._client.app.container["engine"].dispose()
            self._client = None

        gc.collect()

    # ── Data documents ────────────────────────────────────────────────

    def _list_documents(self) -> List[Dict[str, Any]]:
        """Return every Data document the API lists.

        Returns
        -------
        list[dict[str, Any]]
            Document rows as ``GET /api/v1/documents/`` serves them.

        Raises
        ------
        RuntimeError
            If the listing request does not return HTTP 200.
        """
        response = self._client.get("/api/v1/documents/")
        if response.status_code != 200:
            raise RuntimeError(
                f"Data document listing failed: {response.status_code} - "
                f"{response.text}"
            )
        payload = response.json()
        return payload if isinstance(payload, list) else []

    def _ensure_documents(self, paper_files: List[Path]) -> List[int]:
        """Return the Data document ids for ``paper_files``, parsing new ones.

        Documents already FINISHED under the same file name (including the
        extension) are reused so a later run skips re-parsing. Missing
        documents are created, uploaded through ``DocumentJob`` and polled
        until FINISHED.

        Parameters
        ----------
        paper_files : list[Path]
            PDF files to make available as Data documents.

        Returns
        -------
        list[int]
            Data document ids, in ``paper_files`` order.
        """
        finished_by_name: Dict[str, Dict[str, Any]] = {}
        for document in self._list_documents():
            name = document.get("name")
            if name and document.get("status") == DocumentStatus.FINISHED.value:
                finished_by_name[name] = document

        document_ids: List[int] = []
        for paper_file in paper_files:
            name = paper_file.name
            document = finished_by_name.get(name)
            if document is None:
                document = self._create_and_parse_document(paper_file, name)
                finished_by_name[name] = document
            document_ids.append(int(document["id"]))
        return document_ids

    def _create_and_parse_document(self, paper_file: Path, name: str) -> Dict[str, Any]:
        """Create and parse one PDF into a FINISHED Data document.

        Parameters
        ----------
        paper_file : Path
            The PDF to upload.
        name : str
            Unique Data document name (the PDF file name, extension included).

        Returns
        -------
        dict[str, Any]
            The finished document as ``GET /api/v1/documents/{id}`` serves it.

        Raises
        ------
        RuntimeError
            If creation, enqueueing or parsing fails.
        """
        payload = {
            "name": name,
            "file_name": paper_file.name,
            "dataloader": DOCUMENT_DATALOADER,
            "dataloader_params": dict(DOCUMENT_DATALOADER_PARAMS),
        }
        created = self._client.post("/api/v1/documents/", json=payload)
        if created.status_code == 409:
            # The name is taken. Reuse the row: return it when it is FINISHED,
            # otherwise re-run (or wait for) its parsing job.
            for document in self._list_documents():
                if document.get("name") != name:
                    continue
                document_id = int(document["id"])
                status = document.get("status")
                if status == DocumentStatus.FINISHED.value:
                    return document
                # Any non-FINISHED row is a stale leftover: the benchmark runs
                # the queue in test mode, so DELIVERED/STARTED cannot belong to
                # a live job. Re-enqueue to restart parsing. (In a real async
                # queue this would duplicate a live job, which is acceptable
                # here because DocumentJob is idempotent per document.)
                self._enqueue_document_job(document_id, name, paper_file)
                return self._poll_document(document_id)
            raise RuntimeError(
                f"Document '{name}' already exists but could not be listed."
            )
        if created.status_code != 201:
            raise RuntimeError(
                f"Data document creation failed: {created.status_code} - {created.text}"
            )

        document_id = int(created.json()["id"])
        self._enqueue_document_job(document_id, name, paper_file)
        return self._poll_document(document_id)

    def _enqueue_document_job(
        self, document_id: int, name: str, paper_file: Path
    ) -> None:
        """Upload a PDF and enqueue its ``DocumentJob``.

        Parameters
        ----------
        document_id : int
            The created Data document id.
        name : str
            Data document name, stored for the job list.
        paper_file : Path
            The PDF whose bytes are uploaded.

        Raises
        ------
        RuntimeError
            If the job is not enqueued with HTTP 201.
        """
        response = self._client.post(
            "/api/v1/job/",
            data={
                "job_type": "DocumentJob",
                "kwargs": _json.dumps({"document_id": document_id, "name": name}),
            },
            files={
                "file": (paper_file.name, paper_file.read_bytes(), "application/pdf")
            },
            headers={"filename": paper_file.name},
        )
        if response.status_code != 201:
            raise RuntimeError(
                f"Document job enqueue failed: {response.status_code} - {response.text}"
            )

    def _poll_document(self, document_id: int) -> Dict[str, Any]:
        """Poll a document endpoint until its parsing finishes.

        Parameters
        ----------
        document_id : int
            The Data document to poll.

        Returns
        -------
        dict[str, Any]
            The document payload once it reaches ``FINISHED``.

        Raises
        ------
        RuntimeError
            If the document errors, is not found or does not finish in time.
        """
        for _ in range(_DOCUMENT_POLL_ATTEMPTS):
            response = self._client.get(f"/api/v1/documents/{document_id}")
            if response.status_code == 404:
                raise RuntimeError(f"Document {document_id} not found")
            if response.status_code == 200:
                document = response.json()
                status = document.get("status")
                if status == DocumentStatus.FINISHED.value:
                    return document
                if status == DocumentStatus.ERROR.value:
                    raise RuntimeError(
                        f"Document {document_id} ended with ERROR status"
                    )
            _time.sleep(_DOCUMENT_POLL_INTERVAL_S)
        raise RuntimeError(f"Document {document_id} did not finish")

    def _attach_documents(self, session_id: int, document_ids: List[int]) -> None:
        """Attach Data documents to a RAG session.

        Parameters
        ----------
        session_id : int
            The generative session.
        document_ids : list[int]
            The Data document ids to attach.

        Raises
        ------
        RuntimeError
            If the attach request does not return HTTP 200.
        """
        response = self._client.post(
            f"/api/v1/rag/sessions/{session_id}/documents",
            json={"document_ids": list(document_ids)},
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Document attach failed: {response.status_code} - {response.text}"
            )

    # ── Session / process orchestration ───────────────────────────────

    def _create_session(self, params: Dict[str, Any]) -> int:
        """Create a generative session and return its ID.

        Parameters
        ----------
        params : dict[str, Any]
            Session payload to POST.

        Returns
        -------
        int
            The created session ID.

        Raises
        ------
        RuntimeError
            If session creation does not return HTTP 201.
        """
        response = self._client.post("/api/v1/generative-session/", json=params)
        if response.status_code != 201:
            raise RuntimeError(
                f"Session creation failed: {response.status_code} - {response.text}"
            )
        return response.json()["id"]

    def _create_process(self, session_id: int, user_msg: str) -> int:
        """Create a generative process and enqueue its job.

        Parameters
        ----------
        session_id : int
            ID of the generative session to run.
        user_msg : str
            The user message for this turn.

        Returns
        -------
        int
            The created process ID.

        Raises
        ------
        RuntimeError
            If process or job creation does not return HTTP 201.
        """
        proc_resp = self._client.post(
            "/api/v1/generative-process/",
            data={"session_id": session_id, "text_0": user_msg},
        )
        if proc_resp.status_code != 201:
            raise RuntimeError(f"Process creation failed: {proc_resp.status_code}")
        process_id = proc_resp.json()["id"]

        job_resp = self._client.post(
            "/api/v1/job/",
            data={
                "job_type": "GenerativeJob",
                "kwargs": _json.dumps({"generative_process_id": process_id}),
            },
        )
        if job_resp.status_code != 201:
            raise RuntimeError(f"Job enqueue failed: {job_resp.status_code}")
        return process_id

    def _poll_process(self, process_id: int) -> Dict[str, Any]:
        """Poll the process endpoint until the run finishes.

        Parameters
        ----------
        process_id : int
            ID of the generative process to poll.

        Returns
        -------
        dict[str, Any]
            The process payload once it reaches ``FINISHED``.

        Raises
        ------
        RuntimeError
            If the process errors, is not found, or does not finish in time.
        """
        for _ in range(30):
            get_resp = self._client.get(f"/api/v1/generative-process/{process_id}")
            if get_resp.status_code == 404:
                raise RuntimeError(f"Process {process_id} not found")
            if get_resp.status_code == 200:
                candidate = get_resp.json()
                status = candidate.get("status", RunStatus.NOT_STARTED.value)
                if status == RunStatus.FINISHED.value:
                    return candidate
                if status == RunStatus.ERROR.value:
                    raise RuntimeError(f"Process {process_id} ended with ERROR status")
            else:
                log.warning(
                    "Process %d poll returned unexpected status %d",
                    process_id,
                    get_resp.status_code,
                )
            _time.sleep(0.5)
        raise RuntimeError(f"Process {process_id} did not finish")

    def _execute_turn(
        self,
        session_id: int,
        turn_num: int,
        prev_resp: Optional[str],
    ) -> TurnRecord:
        """Run a single conversation turn and record its outcome.

        The turn timer starts after the user question is generated so that
        question-generation latency is excluded from the recorded timings.

        Parameters
        ----------
        session_id : int
            ID of the generative session.
        turn_num : int
            Zero-based turn index within the session.
        prev_resp : str or None
            The previous assistant response, if any.

        Returns
        -------
        TurnRecord
            The recorded turn, successful or failed.
        """
        user_msg = ""
        turn_start: Optional[float] = None
        try:
            if self._user_simulator:
                user_msg = self._user_simulator.generate_question(prev_resp)
            else:
                user_msg = "Tell me about RAG."

            turn_start = _time.perf_counter()

            process_id = self._create_process(session_id, user_msg)
            result_data = self._poll_process(process_id)

            total_turn_ms = (_time.perf_counter() - turn_start) * 1000

            parsed = _parse_process_output(result_data, total_turn_ms)

            return TurnRecord(
                turn_number=turn_num,
                user_message=user_msg,
                assistant_response=parsed.message,
                retrieval_time_ms=parsed.retrieval_time_ms,
                transformation_time_ms=parsed.transformation_time_ms,
                generation_time_ms=parsed.generation_time_ms,
                total_turn_time_ms=total_turn_ms,
                chunks_retrieved=parsed.chunks_retrieved,
                queries=parsed.queries,
                retrieved_chunks=parsed.retrieved_chunks,
                prompt_length_chars=len(user_msg),
                response_length_chars=len(parsed.message),
            )
        except Exception as e:
            turn_error = str(e)
            total_turn_ms = (
                (_time.perf_counter() - turn_start) * 1000
                if turn_start is not None
                else 0.0
            )
            log.error("Turn %d failed: %s", turn_num, turn_error)
            return TurnRecord(
                turn_number=turn_num,
                user_message=user_msg,
                assistant_response="",
                retrieval_time_ms=0.0,
                transformation_time_ms=0.0,
                generation_time_ms=0.0,
                total_turn_time_ms=total_turn_ms,
                chunks_retrieved=0,
                queries=[],
                retrieved_chunks={},
                prompt_length_chars=0,
                response_length_chars=0,
                error=turn_error,
            )

    def ensure_models_available(
        self, params: Dict[str, Any], *, download: bool = True
    ) -> None:
        """Ensure every downloadable component referenced by *params* is available.

        Called before a pipeline's iterations so downloads are never counted as
        load time. References whose component name is not in the registry are
        skipped (session validation reports those separately). Once every
        registered reference is resolved, any component that declares
        ``REQUIRES_API_KEY`` is checked for a credential, so a missing key fails
        before the first iteration instead of mid-conversation. Chunker
        tokenizers and cross-encoder checkpoints are not components of their
        own, so those Hugging Face repos are gated explicitly as well.

        Parameters
        ----------
        params : dict[str, Any]
            A session/pipeline payload to scan recursively for component refs.
        download : bool
            When True, fetch missing artifacts; when False, a missing
            component raises instead (``--no-download``).

        Raises
        ------
        RuntimeError
            If a remote component's reference declares no API key.
        """
        if not self._client:
            raise RuntimeError(
                "PipelineBenchmarkRunner not set up. Call setup() first."
            )
        registry = self._client.app.container["component_registry"]
        resolved: List[Tuple[str, Any, Dict[str, Any]]] = []
        for ref in _iter_component_refs(params):
            name = ref.get("component")
            if not isinstance(name, str) or not name:
                continue
            if name not in registry:
                continue
            component_class = registry[name]["class"]
            ensure_component_downloaded(component_class, download=download)
            resolved.append((name, component_class, ref))
        for name, component_class, ref in resolved:
            ensure_api_key_available(name, component_class, ref)
        for tokenizer_name in sorted(set(_iter_tokenizer_names(params))):
            ensure_tokenizer_available(tokenizer_name, download=download)
        for model_name in sorted(set(_iter_cross_encoder_models(params))):
            ensure_cross_encoder_available(model_name, download=download)

    def _plan_and_apply_devices(
        self,
        pipeline_key: str,
        params: Dict[str, Any],
        demoted: Sequence[Tuple[str, ...]] = (),
    ) -> DevicePlan:
        """Plan this attempt's GPU offload and write it into *params*.

        The plan is recomputed for every attempt (it is pure and cheap) and
        printed once per pipeline, or again whenever a demotion changed it, so
        the run log states which component runs on which device and why.

        Parameters
        ----------
        pipeline_key : str
            Pipeline registry key, which selects the device priority.
        params : dict[str, Any]
            Session parameters of the attempt, updated in place.
        demoted : sequence[tuple[str, ...]]
            References demoted to the CPU after an out-of-memory failure of a
            previous attempt of the same iteration.

        Returns
        -------
        DevicePlan
            The plan that was applied to *params*.
        """
        plan = plan_device_assignments(
            params,
            default_device_priority(pipeline_key),
            requested=self._requested_device,
            budget_bytes=self._gpu_budget_bytes,
            registry=self._registry,
            demoted=demoted,
        )
        if pipeline_key not in self._device_reported or demoted:
            _report_device_plan(pipeline_key, plan)
            self._device_reported.add(pipeline_key)
        apply_device_plan(params, plan)
        return plan

    def run_pipeline(
        self,
        pipeline_key: str,
        pipeline_name: str,
        config_fn: Callable[[List[int]], Dict[str, Any]],
        iterations: int = 3,
        messages_per_conversation: int = 5,
        pipeline_index: int = 1,
    ) -> List[PipelineRunResult]:
        """Run a pipeline benchmark for the given number of iterations.

        Each iteration creates an independent conversation over the complete
        corpus — the session is created first, then all discovered Data
        documents are attached to it.

        Parameters
        ----------
        pipeline_key : str
            Key identifying the pipeline in the registry (used in logging).
        pipeline_name : str
            Human-readable pipeline name.
        config_fn : Callable[[List[int]], Dict[str, Any]]
            Function mapping the full list of document IDs to a session
            payload dict. The corpus is attached after creation, so the
            returned payload must not carry ``documents``.
        iterations : int
            Number of iterations to run.
        messages_per_conversation : int
            Number of user-assistant turns per session.
        pipeline_index : int
            One-based index of this pipeline in the run, used to name its
            output folder (e.g. ``1 - Publication 1 - Medical Fitness``).

        Returns
        -------
        list[PipelineRunResult]
            One result per iteration, in iteration order.
        """
        if not self._client:
            raise RuntimeError(
                "PipelineBenchmarkRunner not set up. Call setup() first."
            )
        if not self._document_ids:
            raise RuntimeError("No documents loaded. Call setup() first.")

        results: List[PipelineRunResult] = []
        writer = PipelineResultsWriter(
            folder=self._config.pipelines_dir / f"{pipeline_index} - {pipeline_name}",
            pipeline_name=pipeline_name,
        )

        for iteration in range(iterations):
            pipeline_total_start = _time.perf_counter()
            doc_ids = list(self._document_ids)
            log.info(
                "Pipeline %s (iteration %d): using %d documents",
                pipeline_key,
                iteration,
                len(doc_ids),
            )

            attempt = 0
            # References this iteration demoted to the CPU after an
            # out-of-memory failure; each retry adds the largest component
            # still on the GPU, so an iteration is retried at most once per
            # GPU-assigned component.
            demoted: List[Tuple[str, ...]] = []
            while True:
                run_id = _iteration_run_id(iteration, attempt)
                params, plan, pipeline_error = self._prepare_attempt(
                    pipeline_key=pipeline_key,
                    pipeline_name=pipeline_name,
                    config_fn=config_fn,
                    doc_ids=doc_ids,
                    iteration=iteration,
                    attempt=attempt,
                    demoted=demoted,
                )

                # Persist the (possibly partial) config so every attempt leaves
                # a trace on disk even when the config builder itself fails.
                writer.write_config(
                    run_id=run_id,
                    config=_recorded_config(params, plan, demoted),
                )

                turn_records: List[TurnRecord] = []
                if pipeline_error is None:
                    turn_records, pipeline_error = self._run_attempt(
                        pipeline_key=pipeline_key,
                        pipeline_name=pipeline_name,
                        params=params,
                        doc_ids=doc_ids,
                        writer=writer,
                        run_id=run_id,
                        iteration=iteration,
                        messages_per_conversation=messages_per_conversation,
                    )

                if pipeline_error is not None and not turn_records:
                    _write_failed_iteration(
                        writer=writer,
                        run_id=run_id,
                        pipeline_name=pipeline_name,
                        iteration=iteration,
                        error=pipeline_error,
                    )

                failure = _out_of_memory_failure(pipeline_error, turn_records)
                demotion = (
                    largest_gpu_assignment(plan)
                    if failure is not None and plan is not None
                    else None
                )
                if demotion is None:
                    break
                demoted.append(demotion[0])
                _report_demotion(demotion[0], iteration, attempt, failure)
                attempt += 1

            pipeline_total_ms = (_time.perf_counter() - pipeline_total_start) * 1000

            (
                avg_transformation,
                avg_retrieval,
                avg_generation,
                avg_turn,
            ) = _aggregate_stats(turn_records)
            success, error_message = _pipeline_success(pipeline_error, turn_records)

            results.append(
                PipelineRunResult(
                    pipeline_name=pipeline_name,
                    pipeline_config=_recorded_config(params, plan, demoted),
                    document_ids=list(self._document_ids),
                    turns=turn_records,
                    total_time_ms=pipeline_total_ms,
                    avg_transformation_time_ms=avg_transformation,
                    avg_retrieval_time_ms=avg_retrieval,
                    avg_generation_time_ms=avg_generation,
                    avg_turn_time_ms=avg_turn,
                    total_chunks_retrieved=sum(
                        t.chunks_retrieved for t in turn_records
                    ),
                    success=success,
                    error_message=error_message,
                    iteration=iteration,
                )
            )

        return results

    def _prepare_attempt(
        self,
        *,
        pipeline_key: str,
        pipeline_name: str,
        config_fn: Callable[[List[int]], Dict[str, Any]],
        doc_ids: List[int],
        iteration: int,
        attempt: int,
        demoted: Sequence[Tuple[str, ...]],
    ) -> Tuple[Dict[str, Any], Optional[DevicePlan], Optional[str]]:
        """Build one attempt's session payload with its device plan applied.

        Parameters
        ----------
        pipeline_key : str
            Pipeline registry key, which selects the device priority.
        pipeline_name : str
            Human-readable pipeline name, used when the config declares none.
        config_fn : Callable[[List[int]], Dict[str, Any]]
            Function building the session payload for the corpus.
        doc_ids : list[int]
            Data-document ids of the corpus, handed to *config_fn*.
        iteration : int
            Zero-based iteration index.
        attempt : int
            Zero-based attempt index within the iteration.
        demoted : sequence[tuple[str, ...]]
            References demoted to the CPU after an earlier attempt failed on a
            GPU allocation.

        Returns
        -------
        tuple[dict[str, Any], DevicePlan or None, str or None]
            The payload, the plan applied to it (``None`` when no payload could
            be built) and the failure message, if any.
        """
        params: Dict[str, Any] = {}
        pipeline_error: Optional[str] = None
        try:
            params = config_fn(doc_ids)
            params["name"] = _iteration_session_name(
                params.get("name") or pipeline_name,
                self._run_tag,
                iteration,
                attempt,
            )
        except Exception as e:
            pipeline_error = str(e)
            log.error(
                "Pipeline %s iteration %d failed: %s",
                pipeline_key,
                iteration,
                pipeline_error,
            )

        # Guard against a config function that silently returns a non-dict
        # value; the rest of the iteration expects a dict.
        if not isinstance(params, dict):
            params = {}

        # Offload what fits of this pipeline's llama.cpp components before the
        # session is created: the configs declare CPU, so without this the GPU
        # reported by --device would never be used.
        plan: Optional[DevicePlan] = None
        if params:
            plan = self._plan_and_apply_devices(pipeline_key, params, demoted)
        return params, plan, pipeline_error

    def _run_attempt(
        self,
        *,
        pipeline_key: str,
        pipeline_name: str,
        params: Dict[str, Any],
        doc_ids: List[int],
        writer: PipelineResultsWriter,
        run_id: str,
        iteration: int,
        messages_per_conversation: int,
    ) -> Tuple[List[TurnRecord], Optional[str]]:
        """Run every turn of one attempt, recording each as it finishes.

        Parameters
        ----------
        pipeline_key : str
            Pipeline registry key, used in the failure log line.
        pipeline_name : str
            Human-readable pipeline name, stored on every turn row.
        params : dict[str, Any]
            Session payload to create the session with.
        doc_ids : list[int]
            Data-document ids to attach to the session.
        writer : PipelineResultsWriter
            Writer of this pipeline's run folder.
        run_id : str
            Results id of the attempt, used to name its turn rows.
        iteration : int
            Zero-based iteration index.
        messages_per_conversation : int
            Number of user-assistant turns to run.

        Returns
        -------
        tuple[list[TurnRecord], str or None]
            The recorded turns and the failure message when the attempt
            aborted before its turns could run.
        """
        turn_records: List[TurnRecord] = []
        pipeline_error: Optional[str] = None
        try:
            session_id = self._create_session(params)
            self._attach_documents(session_id, doc_ids)

            if self._user_simulator:
                self._user_simulator.reset()

            prev_resp: Optional[str] = None
            for turn_num in range(messages_per_conversation):
                turn = self._execute_turn(session_id, turn_num, prev_resp)
                turn_records.append(turn)
                writer.append_turn(
                    turn_id=f"{run_id}-turn{turn_num}",
                    run_id=run_id,
                    pipeline_name=pipeline_name,
                    iteration=iteration,
                    turn=turn,
                )
                prev_resp = turn.assistant_response
        except Exception as e:
            pipeline_error = str(e)
            log.error(
                "Pipeline %s iteration %d failed: %s",
                pipeline_key,
                iteration,
                pipeline_error,
            )
        return turn_records, pipeline_error


def _write_failed_iteration(
    writer: "PipelineResultsWriter",
    run_id: str,
    pipeline_name: str,
    iteration: int,
    error: str,
) -> None:
    """Persist a failed iteration that produced no conversation turns.

    Records an error marker turn so the iteration is never lost from disk
    when the config builder or session creation fails before any turn ran.
    """
    writer.append_turn(
        turn_id=f"{run_id}-error",
        run_id=run_id,
        pipeline_name=pipeline_name,
        iteration=iteration,
        turn=TurnRecord(
            turn_number=0,
            user_message="",
            assistant_response="",
            retrieval_time_ms=0.0,
            transformation_time_ms=0.0,
            generation_time_ms=0.0,
            total_turn_time_ms=0.0,
            chunks_retrieved=0,
            queries=[],
            retrieved_chunks={},
            prompt_length_chars=0,
            response_length_chars=0,
            error=error,
        ),
    )

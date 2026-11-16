"""Per-pipeline llama.cpp device planning for the RAG benchmark suite.

``--device`` used to be recorded in the run metadata and then ignored: every
pipeline config declared ``"device": "CPU"`` for its GGUF components, so a
single turn of a pipeline with a 7B model took tens of minutes.

The llama.cpp components of a pipeline are **never resident at the same time**.
``RAG_pipeline.generate()`` releases every stage as soon as that stage ends
(``_release`` after the transformation stage, after retrieval and after
generation, plus the same calls in its ``finally`` safety net), and
``LazyLLM.close()`` drops the backend, closes it, runs ``gc.collect()`` and
clears the accelerator cache. The peak VRAM of a turn is therefore the largest
single checkpoint, not the sum: every candidate is evaluated on its own against
the same budget instead of subtracting from a running total.

This module therefore computes an explicit device plan per pipeline: which
llama.cpp components are offloaded to the GPU and which stay on the CPU. The
fit test only compares the checkpoint's weights with the free VRAM: the KV
cache and the compute buffers of a real context window are not predicted here,
because they depend on the exact llama.cpp build and are hard to model. The
plan is deliberately optimistic and relies on a runtime safety net: when a
load or an inference really runs out of memory, the pipeline benchmark demotes
the offending stage to the CPU and retries the iteration (see
:func:`detect_out_of_memory`).

Only llama.cpp components are planned. A component is eligible when its schema
``device`` field offers the GPU label llama.cpp reports; torch-backed
components are never touched, because the benchmark's torch build is CPU-only.
"""

from __future__ import annotations

import functools
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
)

log = logging.getLogger(__name__)

#: Value of ``--device`` that resolves to the first llama.cpp GPU, if any.
AUTO_DEVICE = "auto"

#: Label the DashAI schemas use for the CPU, and canonical CPU assignment.
CPU_DEVICE = "CPU"

#: Aliases an explicitly GPU-requesting user may type.
GPU_ALIASES = frozenset({"GPU", "CUDA"})

BYTES_PER_MEBIBYTE = 1024 * 1024
BYTES_PER_GIBIBYTE = 1024**3

#: VRAM left untouched so the driver, the CUDA context and the desktop
#: compositor survive. It is *not* a KV-cache estimate: the fit test compares
#: weights only, and a real allocation failure is handled at runtime by
#: demoting the stage to the CPU and retrying (see
#: :func:`detect_out_of_memory`).
VRAM_RESERVE_BYTES = 256 * BYTES_PER_MEBIBYTE

#: Optimism of the fit test, as a fraction of the budget. A checkpoint whose
#: GGUF files exceed the budget by less than this is still offloaded, because
#: the summed file size overstates what llama.cpp keeps resident (a sharded
#: q8_0 checkpoint stores a second copy of its tied output embedding) and the
#: approved policy is to try the GPU and demote to the CPU only when an
#: allocation really fails. Measured on the reference RTX 4060, ``Qwen25_7B``
#: q8_0 is 7 724 MiB of files against a 7 700 MiB budget and still loads with
#: 152 MiB of VRAM to spare. It stays small on purpose: a checkpoint that
#: misses the budget by more than this keeps the CPU.
VRAM_FIT_TOLERANCE = 1.02

#: Substrings that identify an out-of-memory failure in a llama.cpp / ggml /
#: CUDA error message. Matching is case-insensitive. ``cudamalloc`` covers the
#: bare ``cudaMalloc failed`` that some builds report without the
#: ``CUDA error:`` prefix.
OUT_OF_MEMORY_MARKERS = (
    "out of memory",
    "failed to allocate",
    "cuda error",
    "ggml_backend_cuda",
    "cublas",
    "cudamalloc",
)

#: Schema parameter holding the device label of a component reference.
DEVICE_PARAM = "device"

#: Parameter segment of a component reference, dropped from the plan notes.
PARAMS_SEGMENT = "params"

#: Wrapper key of a generative-session payload: its stages live one level
#: deeper, under ``parameters``. Both shapes are planned, so a flat parameter
#: tree is understood as well.
SESSION_PARAMETERS_KEY = "parameters"

#: Directory segment a checkpoint class declares its GGUF glob in.
GGUF_PATTERN_ATTR = "GGUF_PATTERN"

#: Attribute a GGUF component class exposes to locate its downloaded file.
LOCAL_GGUF_PATH_ATTR = "_local_gguf_path"

#: Attribute a downloadable component declares its download size in.
DOWNLOAD_SIZE_ATTR = "DOWNLOAD_SIZE_BYTES"

#: Command that reports free VRAM, in MiB, one line per GPU.
NVIDIA_SMI_COMMAND = (
    "nvidia-smi",
    "--query-gpu=memory.free",
    "--format=csv,noheader,nounits",
)

#: How long ``nvidia-smi`` may take before the budget is treated as unknown.
NVIDIA_SMI_TIMEOUT_S = 10.0

#: Device priority of every pipeline whose bottleneck is generation.
GENERATION_FIRST_PRIORITY = ("generation_model", "query_transformation")

#: Device priority of ``pub4a``: the 7B embedding model is its bottleneck.
RETRIEVER_FIRST_PRIORITY = ("retriever_model", "generation_model")

#: Pipeline whose embedding stage, not its generator, dominates a turn.
RETRIEVER_FIRST_PIPELINE = "pub4a"


def format_bytes_as_gib(value_bytes: int) -> str:
    """Format a byte count as GiB with one decimal, for the plan notes.

    Parameters
    ----------
    value_bytes : int
        The byte count to format.

    Returns
    -------
    str
        The count in GiB, e.g. ``"1.9 GiB"``.
    """
    return f"{value_bytes / BYTES_PER_GIBIBYTE:.1f} GiB"


def llama_gpu_label() -> Optional[str]:
    """Return the first GPU label llama.cpp reports, or ``None``.

    The label is the exact string the DashAI GGUF schemas accept in their
    ``device`` field, e.g.
    ``"GPU 0: NVIDIA GeForce RTX 4060 Laptop GPU - Compute Capability 8.9"``.

    Returns
    -------
    str or None
        The GPU label, or ``None`` when llama.cpp was built without GPU
        support or found no device.
    """
    from DashAI.back.models.utils import (
        LLAMA_DEVICE_ENUM,
        is_gpu_available_for_llama_cpp,
    )

    if not is_gpu_available_for_llama_cpp():
        return None
    return next((label for label in LLAMA_DEVICE_ENUM if label != CPU_DEVICE), None)


def llama_gpu_labels() -> Tuple[str, ...]:
    """Return every GPU label llama.cpp reports.

    Returns
    -------
    tuple[str, ...]
        The non-CPU labels of ``LLAMA_DEVICE_ENUM``; empty on a CPU-only
        llama.cpp build.
    """
    from DashAI.back.models.utils import LLAMA_DEVICE_ENUM

    return tuple(label for label in LLAMA_DEVICE_ENUM if label != CPU_DEVICE)


@functools.lru_cache(maxsize=1)
def free_vram_bytes() -> Optional[int]:
    """Return the free VRAM of the first GPU, in bytes, or ``None``.

    The value is read once per process from ``nvidia-smi`` and cached: the
    planner runs for every iteration and the budget must not drift between
    iterations of the same run.

    Returns
    -------
    int or None
        Free VRAM in bytes, or ``None`` when ``nvidia-smi`` is missing,
        fails, or prints something unexpected.
    """
    try:
        completed = subprocess.run(
            NVIDIA_SMI_COMMAND,
            capture_output=True,
            text=True,
            timeout=NVIDIA_SMI_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        log.debug("nvidia-smi could not report free VRAM: %s", exc)
        return None
    if completed.returncode != 0:
        log.debug("nvidia-smi exited with %d", completed.returncode)
        return None
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        return None
    try:
        return int(float(lines[0].split()[0])) * BYTES_PER_MEBIBYTE
    except (ValueError, IndexError):
        log.debug("Unexpected nvidia-smi output: %r", completed.stdout)
        return None


def clear_free_vram_cache() -> None:
    """Forget the cached free-VRAM reading (used by tests)."""
    free_vram_bytes.cache_clear()


def vram_budget_bytes() -> int:
    """Return the VRAM the plan may spend, i.e. free VRAM minus the reserve.

    Returns
    -------
    int
        The budget in bytes, or ``0`` when free VRAM could not be read.
    """
    free = free_vram_bytes()
    if free is None:
        return 0
    return max(free - VRAM_RESERVE_BYTES, 0)


def detect_out_of_memory(error: Optional[str]) -> bool:
    """Return whether *error* looks like a GPU out-of-memory failure.

    The match is case-insensitive and looks for any of
    :data:`OUT_OF_MEMORY_MARKERS`, so it recognises the messages llama.cpp,
    ggml and CUDA actually print (``CUDA error: out of memory``,
    ``ggml_backend_cuda_buffer_type_alloc_buffer: allocating ... failed``,
    ``cudaMalloc failed``) without matching unrelated failures such as an
    exceeded context window.

    Parameters
    ----------
    error : str or None
        The error message recorded for a failed iteration or turn.

    Returns
    -------
    bool
        True when the message is an out-of-memory failure.
    """
    if not isinstance(error, str) or not error:
        return False
    lowered = error.lower()
    return any(marker in lowered for marker in OUT_OF_MEMORY_MARKERS)


def resolve_requested_device(requested: str) -> str:
    """Resolve a ``--device`` value to a label the component schemas accept.

    Parameters
    ----------
    requested : str
        ``auto``, ``CPU``, ``GPU`` or ``CUDA`` (case-insensitive), or a label
        this function already returned, which is passed through so a resolved
        value can be handed back in.

    Returns
    -------
    str
        ``CPU`` or the llama.cpp GPU label.

    Raises
    ------
    ValueError
        If the value is unknown, or if a GPU was requested but llama.cpp
        reports none.
    """
    value = (requested or "").strip()
    current_label = llama_gpu_label()
    if current_label is not None and value == current_label:
        return value
    if value.lower() == AUTO_DEVICE:
        return current_label or CPU_DEVICE
    if value.upper() in GPU_ALIASES:
        label = current_label
        if label is None:
            raise ValueError(
                f"{requested!r} requests a GPU but llama.cpp reports no GPU "
                "device. Use 'CPU' or 'auto' instead."
            )
        return label
    if value.upper() == CPU_DEVICE:
        return CPU_DEVICE
    raise ValueError(
        f"Unknown device {requested!r}. Use 'auto', 'CPU', 'GPU' or 'CUDA'."
    )


def _local_checkpoint_bytes(component_class: Any) -> Optional[int]:
    """Return the on-disk size of a class' GGUF checkpoint, or ``None``.

    Multi-part checkpoints are summed: a 7B model stored as several q8_0
    shards only reports its first shard through ``_local_gguf_path()``, and
    planning from that single shard would understate the footprint by ~5 GiB.

    Parameters
    ----------
    component_class : Any
        The registered component class.

    Returns
    -------
    int or None
        Total checkpoint size in bytes, or ``None`` when the class has no
        local checkpoint or the file cannot be located.
    """
    locate = getattr(component_class, LOCAL_GGUF_PATH_ATTR, None)
    if not callable(locate):
        return None
    try:
        path = Path(locate())
    except Exception as exc:  # missing download, unregistered store, ...
        log.debug("%s has no local checkpoint: %s", component_class, exc)
        return None
    if not path.is_file():
        return None
    pattern = getattr(component_class, GGUF_PATTERN_ATTR, None) or "*.gguf"
    try:
        shards = [item for item in path.parent.glob(pattern) if item.is_file()]
        total = sum(item.stat().st_size for item in shards) if shards else 0
    except (OSError, ValueError):
        total = 0
    return total or path.stat().st_size


def estimate_component_vram_bytes(component_class: Any) -> Optional[int]:
    """Return the VRAM a GGUF checkpoint's weights occupy, in bytes.

    The on-disk size is used when the checkpoint is downloaded (it reflects
    the actual quantization), otherwise the size the class declares. Only the
    weights are estimated: the KV cache and the compute buffers are validated
    at runtime, not predicted here.

    Parameters
    ----------
    component_class : Any
        The registered component class.

    Returns
    -------
    int or None
        The checkpoint size in bytes, or ``None`` when the class declares
        neither a local file nor a download size.
    """
    local_bytes = _local_checkpoint_bytes(component_class)
    if local_bytes is not None:
        return local_bytes
    declared = getattr(component_class, DOWNLOAD_SIZE_ATTR, None)
    if isinstance(declared, int) and declared > 0:
        return declared
    return None


def _index_segment(index: int) -> str:
    """Return the path segment standing for a list index."""
    return f"[{index}]"


def _is_index_segment(segment: str) -> bool:
    """Return whether *segment* stands for a list index."""
    return segment.startswith("[") and segment.endswith("]")


def _iter_refs_with_path(
    node: Any,
    path: Tuple[str, ...] = (),
) -> Iterator[Tuple[Tuple[str, ...], Dict[str, Any]]]:
    """Yield every ``{"component": ...}`` reference together with its path.

    Walks dicts and lists recursively, like
    ``RAG_benchmark.app.pipelines.base._iter_component_refs``, but keeps the
    parameter keys that lead to each reference so the planner can tell which
    top-level stage it belongs to. List items are keyed by their index, e.g.
    ``("[0]",)``. The input is never mutated.

    Parameters
    ----------
    node : Any
        Parameter tree to scan.
    path : tuple[str, ...]
        Keys already walked to reach *node*.

    Yields
    ------
    tuple[tuple[str, ...], dict[str, Any]]
        The path of the reference and the reference itself.
    """
    if isinstance(node, dict):
        if "component" in node:
            yield path, node
        for key, value in node.items():
            yield from _iter_refs_with_path(value, path + (str(key),))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from _iter_refs_with_path(item, path + (_index_segment(index),))


def display_path(path: Tuple[str, ...]) -> str:
    """Render a reference path for the plan notes, e.g. ``llm_model``.

    The ``params`` segments, the list indices and the ``parameters`` wrapper of
    a session payload are dropped: the note names the stage and the component,
    not the structural keys between them.
    """
    parts = [
        segment
        for segment in path
        if segment != PARAMS_SEGMENT and not _is_index_segment(segment)
    ]
    if parts and parts[0] == SESSION_PARAMETERS_KEY:
        parts = parts[1:]
    return ".".join(parts) or "<parameters>"


def _stage_rank(path: Tuple[str, ...], priority: Sequence[str]) -> Optional[int]:
    """Return the priority rank of the reference at *path*, or ``None``.

    Parameters
    ----------
    path : tuple[str, ...]
        Path of the reference, whose first segment is its top-level stage. A
        session payload nests the stages under ``parameters``, which is
        transparent here.
    priority : sequence[str]
        Top-level parameter keys, most important first.

    Returns
    -------
    int or None
        The rank of the owning stage, or ``None`` when the stage is not
        prioritised (its device is left untouched).
    """
    stage = path[1:] if path and path[0] == SESSION_PARAMETERS_KEY else path
    if not stage:
        return None
    for rank, key in enumerate(priority):
        if key == stage[0]:
            return rank
    return None


def _component_class(registry: Any, name: Any) -> Optional[Any]:
    """Resolve a registry name to its component class, or ``None``."""
    if registry is None or not isinstance(name, str) or not name:
        return None
    try:
        if name not in registry:
            return None
        entry = registry[name]
    except (KeyError, TypeError):
        return None
    return entry.get("class") if isinstance(entry, dict) else None


def _top_stage(path: Tuple[str, ...]) -> Optional[str]:
    """Return the parameter key a reference belongs to, ignoring the wrapper."""
    stage = path[1:] if path and path[0] == SESSION_PARAMETERS_KEY else path
    return stage[0] if stage else None


@functools.lru_cache(maxsize=None)
def _device_enum(component_class: Any) -> Tuple[str, ...]:
    """Return the options of a component's schema ``device`` field.

    Parameters
    ----------
    component_class : Any
        The registered component class.

    Returns
    -------
    tuple[str, ...]
        The enum options, or an empty tuple when the component has no
        schema or no ``device`` field.
    """
    schema = getattr(component_class, "SCHEMA", None)
    if schema is None:
        return ()
    try:
        properties = schema.model_json_schema().get("properties", {})
    except Exception as exc:  # a schema that cannot render cannot be planned
        log.debug("%s schema could not be rendered: %s", component_class, exc)
        return ()
    device_field = properties.get(DEVICE_PARAM)
    if not isinstance(device_field, dict):
        return ()
    options = device_field.get("enum")
    if not isinstance(options, list):
        return ()
    return tuple(str(option) for option in options)


def supports_device_label(component_class: Any, label: Optional[str]) -> bool:
    """Return whether the component's schema accepts a device *label*.

    Torch-backed components declare their own device enum (``CPU`` only on
    this machine, because the benchmark's torch build has no CUDA), so they
    never match a llama.cpp GPU label and are left exactly as the pipeline or
    benchmark config declares them.

    Parameters
    ----------
    component_class : Any
        The registered component class.
    label : str or None
        The GPU label to look for; ``None`` falls back to every label
        llama.cpp reports.

    Returns
    -------
    bool
        True when the schema accepts the label.
    """
    labels = {label} if label else set(llama_gpu_labels())
    return bool(set(_device_enum(component_class)) & labels)


def _ref_at(node: Any, path: Tuple[str, ...]) -> Optional[Dict[str, Any]]:
    """Return the component reference found at *path*, or ``None``."""
    current = node
    for segment in path:
        if _is_index_segment(segment):
            index = int(segment[1:-1])
            if not isinstance(current, list) or index >= len(current):
                return None
            current = current[index]
        else:
            if not isinstance(current, dict):
                return None
            current = current.get(segment)
        if current is None:
            return None
    return current if isinstance(current, dict) else None


@dataclass
class DevicePlan:
    """Device assignment computed for one pipeline's parameters.

    Attributes
    ----------
    assignments : dict[tuple[str, ...], str]
        Parameter path of a component reference mapped to its device label.
    notes : list[str]
        Human-readable one-liners, one per planned component, naming the
        checkpoint's weights and the budget they were compared against.
    gpu_label : str or None
        The GPU label the plan could have used, or ``None`` when the run is
        CPU-only.
    budget_bytes : int
        The VRAM budget every candidate was evaluated against, in bytes.
    footprints : dict[tuple[str, ...], int]
        Estimated weight bytes of every candidate whose size is known, used to
        pick the largest GPU assignment when an out-of-memory failure forces a
        demotion.
    """

    assignments: Dict[Tuple[str, ...], str] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    gpu_label: Optional[str] = None
    budget_bytes: int = 0
    footprints: Dict[Tuple[str, ...], int] = field(default_factory=dict)


def largest_gpu_assignment(
    plan: DevicePlan,
) -> Optional[Tuple[Tuple[str, ...], int]]:
    """Return the GPU-assigned component with the largest footprint.

    Parameters
    ----------
    plan : DevicePlan
        The plan of the attempt that just failed.

    Returns
    -------
    tuple[tuple[str, ...], int] or None
        The path and estimated weights of the largest GPU assignment, or
        ``None`` when every planned component already runs on the CPU. Ties
        keep the first assignment in priority order.
    """
    gpu_assignments = [
        (path, plan.footprints.get(path, 0))
        for path, label in plan.assignments.items()
        if label != CPU_DEVICE
    ]
    if not gpu_assignments:
        return None
    return max(gpu_assignments, key=lambda assignment: assignment[1])


def plan_device_assignments(
    parameters: Dict[str, Any],
    priority: Sequence[str],
    *,
    requested: str,
    budget_bytes: int,
    registry: Any,
    demoted: Iterable[Tuple[str, ...]] = (),
) -> DevicePlan:
    """Compute the per-component device assignment of one pipeline.

    Components are considered in *priority* order, but each candidate is
    evaluated independently against the same *budget_bytes*: the llama.cpp
    components of a pipeline are released as their stage ends, so the peak
    VRAM is the largest single checkpoint rather than the sum. A candidate
    takes the GPU when its weights fit the budget; otherwise it stays on the
    CPU and the next candidate is still evaluated, because a later (smaller)
    checkpoint can still be offloaded.

    The fit test only counts the checkpoint's weights and allows a small
    optimism window (:data:`VRAM_FIT_TOLERANCE`) on top of the budget: the KV
    cache and the compute buffers are validated at runtime, and a real
    allocation failure demotes the stage to the CPU (see
    :func:`detect_out_of_memory`).

    Parameters
    ----------
    parameters : dict[str, Any]
        The session parameters of the pipeline. Never mutated.
    priority : sequence[str]
        Top-level parameter keys, most important first. References under
        other keys are not planned and keep the device their config declares.
    requested : str
        The raw ``--device`` value (``auto``, ``CPU``, ``GPU`` or ``CUDA``).
    budget_bytes : int
        VRAM every candidate is evaluated against, in bytes.
    registry : Any
        Component registry used to resolve component names to classes; a
        mapping supporting ``in`` and ``[]`` is enough.
    demoted : iterable[tuple[str, ...]]
        References forced onto the CPU after an out-of-memory failure, even
        when their weights fit the budget. They are still reported, so the
        plan states why they were denied the GPU.

    Returns
    -------
    DevicePlan
        The assignments, their notes and the budget they were compared with.

    Raises
    ------
    ValueError
        If *requested* is not a known device value, or requests a GPU when
        llama.cpp reports none.
    """
    resolved = resolve_requested_device(requested)
    if resolved == CPU_DEVICE:
        return DevicePlan(
            notes=[f"device: CPU (requested {requested!r}; no GPU offload)"],
            budget_bytes=0,
        )

    budget = max(int(budget_bytes), 0)
    budget_text = format_bytes_as_gib(budget)
    plan = DevicePlan(gpu_label=resolved, budget_bytes=budget)
    demoted_paths = set(demoted)

    candidates: List[Tuple[int, Tuple[str, ...], Dict[str, Any]]] = []
    for path, ref in _iter_refs_with_path(parameters):
        rank = _stage_rank(path, priority)
        if rank is not None:
            candidates.append((rank, path, ref))
    # Stable sort: references of the same stage keep their config order.
    candidates.sort(key=lambda candidate: candidate[0])

    for _, path, ref in candidates:
        component_class = _component_class(registry, ref.get("component"))
        if component_class is None or not supports_device_label(
            component_class, resolved
        ):
            continue
        name = display_path(path)
        size = estimate_component_vram_bytes(component_class)
        if size is None:
            plan.assignments[path] = CPU_DEVICE
            plan.notes.append(
                f"{name}: CPU (checkpoint size unknown; cannot compare it "
                f"with the {budget_text} budget)"
            )
            continue
        plan.footprints[path] = size
        size_text = format_bytes_as_gib(size)
        fits = size <= int(budget * VRAM_FIT_TOLERANCE)
        if path in demoted_paths:
            plan.assignments[path] = CPU_DEVICE
            plan.notes.append(
                f"{name}: CPU (demoted after an out-of-memory failure; "
                f"{size_text} weights fit the {budget_text} budget)"
            )
        elif fits and size <= budget:
            plan.assignments[path] = resolved
            plan.notes.append(
                f"{name}: GPU ({size_text} weights fit the {budget_text} budget)"
            )
        elif fits:
            plan.assignments[path] = resolved
            plan.notes.append(
                f"{name}: GPU ({size_text} weights fit the {budget_text} budget "
                "within the offload tolerance)"
            )
        else:
            plan.assignments[path] = CPU_DEVICE
            plan.notes.append(
                f"{name}: CPU ({size_text} weights exceed the {budget_text} budget)"
            )

    if not plan.notes:
        plan.notes.append(
            f"device: {resolved} (no prioritised llama.cpp component to offload)"
        )
    return plan


def apply_device_plan(parameters: Dict[str, Any], plan: DevicePlan) -> None:
    """Write a plan's device labels into the pipeline parameters, in place.

    Only the references the plan names are touched, and only their ``device``
    parameter: every other value keeps the one the pipeline config declared.

    Parameters
    ----------
    parameters : dict[str, Any]
        The session parameters to update.
    plan : DevicePlan
        The plan produced by :func:`plan_device_assignments`.
    """
    for path, label in plan.assignments.items():
        ref = _ref_at(parameters, path)
        if ref is None:
            log.warning("Device plan lost its reference at %s", ".".join(path))
            continue
        params = ref.get(PARAMS_SEGMENT)
        if not isinstance(params, dict):
            params = {}
            ref[PARAMS_SEGMENT] = params
        params[DEVICE_PARAM] = label


def default_device_priority(pipeline_key: str) -> Tuple[str, ...]:
    """Return the device priority of a pipeline.

    ``pub4a`` lists its embedding model first: indexing the corpus through a
    7B GGUF embedding model is what makes its turns take ~29 minutes on the
    CPU, while its generation stage costs ~1 minute. Every other pipeline
    generates far more tokens than it transforms, so its generator comes
    first.

    Candidates are evaluated independently against the budget, so the order no
    longer changes the outcome: every candidate that fits gets the GPU either
    way. The order still fixes the order of the plan's notes and which
    assignment is reported first when an out-of-memory failure has to demote
    components of the same size.

    Parameters
    ----------
    pipeline_key : str
        Registry key of the pipeline, e.g. ``pub4a``.

    Returns
    -------
    tuple[str, ...]
        Top-level parameter keys, most important first.
    """
    if pipeline_key == RETRIEVER_FIRST_PIPELINE:
        return RETRIEVER_FIRST_PRIORITY
    return GENERATION_FIRST_PRIORITY

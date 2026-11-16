"""Offline tests for the per-pipeline llama.cpp device planner.

Nothing here loads a model, touches the GPU or queries the real registry:
``free_vram_bytes`` and ``llama_gpu_label`` are monkeypatched, and the
component classes are minimal stand-ins that expose the same surface the
planner reads (a schema ``device`` enum and a checkpoint size).

The pipeline tests use a fake HTTP client instead of the DashAI app, so the
out-of-memory demotion path is exercised without running a single iteration
against a model.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pytest

from DashAI.back.core.enums.status import RunStatus
from RAG_benchmark.app import device as device_mod
from RAG_benchmark.app.config import BenchmarkConfig
from RAG_benchmark.app.pipelines.base import PipelineBenchmarkRunner

#: Label the fake llama.cpp build reports, in the format the DashAI schemas use.
FAKE_GPU = "GPU 0: Fake RTX 4060 - Compute Capability 8.9"

GIB = 1024**3
MIB = 1024**2

#: Checkpoint sizes of the real components, rounded like the planner reads them.
E5_MISTRAL_GGUF_GIB = 4.78
LLAMA_3B_GIB = 1.88
LLAMA_1B_GIB = 0.75
QWEN_7B_GIB = 7.02

#: Peak model of the publication 5 pipelines and the one of ``pub4a``, as
#: measured on this machine, in GiB.
QWEN_7B_MEASURED_GIB = 7.02
E5_MISTRAL_MEASURED_GIB = 4.78

#: VRAM the planner may spend in the pinned scenarios: 7.8 GiB free minus the
#: 256 MiB reserve, rounded to the 7.2 GiB every existing scenario assumed.
BUDGET_GIB = 7.2

#: The two large checkpoints the planner has to refuse when they cannot fit.
OVERSIZED_GIB = 7.9
LARGE_FIT_GIB = 7.0
LARGER_FIT_GIB = 7.2


class _FakeSchema:
    """Minimal stand-in for a DashAI ``BaseSchema`` subclass."""

    def __init__(self, device_enum: Sequence[str]) -> None:
        self._device_enum = tuple(device_enum)

    def model_json_schema(self) -> Dict[str, Any]:
        """Return only the ``device`` property the planner inspects."""
        return {"properties": {"device": {"enum": list(self._device_enum)}}}


def _component(
    device_enum: Sequence[str],
    size_gib: Optional[float] = None,
) -> type:
    """Build a fake component class with a device enum and a declared size."""
    download_size = None if size_gib is None else int(size_gib * GIB)
    return type(
        "FakeComponent",
        (),
        {"SCHEMA": _FakeSchema(device_enum), "DOWNLOAD_SIZE_BYTES": download_size},
    )


def _registry(**components: type) -> Dict[str, Dict[str, Any]]:
    """Build a registry mapping every component name to its class."""
    return {name: {"class": component} for name, component in components.items()}


def _ref(component: str, **params: Any) -> Dict[str, Any]:
    """Build a ``{component, params}`` reference."""
    return {"component": component, "params": dict(params)}


def _parameter_tree(
    *,
    embedding: str,
    generator: str,
    llm: Optional[str] = None,
) -> Dict[str, Any]:
    """Build parameters shaped like ``pub4a`` (``llm`` set: like ``pub5*``)."""
    parameters: Dict[str, Any] = {
        "chunking_model": _ref("TokenChunkModel", chunk_size=300, chunk_overlap=60),
        "retriever_model": _ref(
            "DenseEmbeddingRetriever",
            embedding_model=_ref(embedding, device="CPU", batch_size=32),
            similarity_metric="cosine",
            top_k=20,
        ),
        "generation_model": _ref(
            generator, max_tokens=1024, context_window=8192, device="CPU"
        ),
        "prompt": _ref("DefaultRAGGenerationPrompt", language="en"),
    }
    if llm is not None:
        parameters["query_transformation"] = _ref(
            "LLMQueryRewriter",
            prompt=_ref("DefaultQueryRewritingPrompt", language="en"),
            llm_model=_ref(llm, max_tokens=256, context_window=4096, device="CPU"),
            history_window=2,
        )
    return parameters


@pytest.fixture(autouse=True)
def _fake_gpu(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pretend llama.cpp reports one GPU, without loading anything."""
    monkeypatch.setattr(device_mod, "llama_gpu_label", lambda: FAKE_GPU)


@pytest.fixture(autouse=True)
def _fake_free_vram(monkeypatch: pytest.MonkeyPatch) -> None:
    """Report a fixed free VRAM so no test shells out to ``nvidia-smi``."""
    monkeypatch.setattr(
        device_mod,
        "free_vram_bytes",
        lambda: int(BUDGET_GIB * GIB) + device_mod.VRAM_RESERVE_BYTES,
    )


# ---------------------------------------------------------------------------
# resolve_requested_device
# ---------------------------------------------------------------------------


def test_resolve_auto_uses_the_llama_cpp_gpu() -> None:
    """``auto`` resolves to the GPU label llama.cpp reports."""
    assert device_mod.resolve_requested_device("auto") == FAKE_GPU


def test_resolve_auto_falls_back_to_cpu_without_a_gpu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``auto`` is the silent CPU fallback: it never fails."""
    monkeypatch.setattr(device_mod, "llama_gpu_label", lambda: None)

    assert device_mod.resolve_requested_device("auto") == device_mod.CPU_DEVICE


def test_resolve_cpu_is_canonicalised() -> None:
    """``CPU`` keeps its canonical uppercase form."""
    assert device_mod.resolve_requested_device("CPU") == device_mod.CPU_DEVICE
    assert device_mod.resolve_requested_device("cpu") == device_mod.CPU_DEVICE


def test_resolve_explicit_gpu_aliases_return_the_label() -> None:
    """``GPU`` and ``CUDA`` ask for the device explicitly."""
    assert device_mod.resolve_requested_device("GPU") == FAKE_GPU
    assert device_mod.resolve_requested_device("cuda") == FAKE_GPU


def test_resolve_accepts_its_own_resolved_label() -> None:
    """A resolved label can be passed back in, as the CLI does.

    The CLI resolves ``auto`` once and hands the label to the runner, which
    plans with it; rejecting it crashed every GPU run before this test existed.
    """
    resolved = device_mod.resolve_requested_device("auto")

    assert device_mod.resolve_requested_device(resolved) == resolved
    assert device_mod.resolve_requested_device(device_mod.CPU_DEVICE) == (
        device_mod.CPU_DEVICE
    )


def test_resolve_explicit_gpu_without_a_gpu_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit GPU request must not silently degrade to the CPU."""
    monkeypatch.setattr(device_mod, "llama_gpu_label", lambda: None)

    with pytest.raises(ValueError, match="no GPU"):
        device_mod.resolve_requested_device("GPU")


def test_resolve_unknown_device_raises() -> None:
    """An unknown value names the accepted ones."""
    with pytest.raises(ValueError, match="Unknown device .*TPU"):
        device_mod.resolve_requested_device("TPU")


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------


def test_reserve_is_driver_headroom_only() -> None:
    """The reserve is the 256 MiB driver headroom, not a KV-cache estimate."""
    assert device_mod.VRAM_RESERVE_BYTES == 256 * MIB


def test_budget_is_free_vram_minus_the_reserve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The budget every candidate is compared against is free - reserve."""
    free_bytes = 7956 * MIB
    monkeypatch.setattr(device_mod, "free_vram_bytes", lambda: free_bytes)

    assert device_mod.vram_budget_bytes() == free_bytes - 256 * MIB


def test_budget_is_zero_when_free_vram_is_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unreadable ``nvidia-smi`` leaves nothing to spend, not a negative."""
    monkeypatch.setattr(device_mod, "free_vram_bytes", lambda: None)

    assert device_mod.vram_budget_bytes() == 0


# ---------------------------------------------------------------------------
# detect_out_of_memory
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "CUDA error: out of memory",
        "ggml_backend_cuda_buffer_type_alloc_buffer: allocating 2048.00 MiB on "
        "device 0: cudaMalloc failed: out of memory",
        "cudaMalloc failed",
        "llama_model_load: failed to allocate KV cache",
        "CUBLAS_STATUS_ALLOC_FAILED when calling cublasCreate",
    ],
)
def test_detect_out_of_memory_matches_ggml_and_cuda_failures(message: str) -> None:
    """Every real allocation failure message is recognised."""
    assert device_mod.detect_out_of_memory(message) is True


def test_detect_out_of_memory_ignores_a_context_window_error() -> None:
    """A prompt that outgrew the context window is not an allocation failure."""
    error = "Requested tokens (15430) exceed context window of 8192"

    assert device_mod.detect_out_of_memory(error) is False


def test_detect_out_of_memory_ignores_missing_errors() -> None:
    """A successful turn carries no error and is not a failure."""
    assert device_mod.detect_out_of_memory(None) is False
    assert device_mod.detect_out_of_memory("") is False


# ---------------------------------------------------------------------------
# plan_device_assignments
# ---------------------------------------------------------------------------


def test_pub4a_plan_offloads_both_large_components() -> None:
    """The retriever closes its embedding, so both checkpoints get the GPU."""
    parameters = _parameter_tree(
        embedding="E5MistralGGUFEmbedding", generator="Llama32_3BInstruct"
    )
    registry = _registry(
        E5MistralGGUFEmbedding=_component((FAKE_GPU, "CPU"), E5_MISTRAL_GGUF_GIB),
        Llama32_3BInstruct=_component((FAKE_GPU, "CPU"), LLAMA_3B_GIB),
    )

    plan = device_mod.plan_device_assignments(
        parameters,
        device_mod.default_device_priority("pub4a"),
        requested="auto",
        budget_bytes=int(BUDGET_GIB * GIB),
        registry=registry,
    )

    assert plan.assignments == {
        ("retriever_model", "params", "embedding_model"): FAKE_GPU,
        ("generation_model",): FAKE_GPU,
    }
    assert plan.footprints[("generation_model",)] == int(LLAMA_3B_GIB * GIB)
    embedding_note = next(
        n for n in plan.notes if n.startswith("retriever_model.embedding_model:")
    )
    assert embedding_note == (
        f"retriever_model.embedding_model: GPU ({E5_MISTRAL_MEASURED_GIB:.1f} GiB "
        f"weights fit the {BUDGET_GIB:.1f} GiB budget)"
    )
    assert plan.budget_bytes == int(BUDGET_GIB * GIB)


def test_a_small_retriever_embedding_also_shares_the_gpu() -> None:
    """A small embedding is offloaded as well; nothing is pinned to the CPU."""
    parameters = _parameter_tree(
        embedding="E5MistralGGUFEmbedding", generator="Llama32_3BInstruct"
    )
    registry = _registry(
        E5MistralGGUFEmbedding=_component((FAKE_GPU, "CPU"), 0.5),
        Llama32_3BInstruct=_component((FAKE_GPU, "CPU"), LLAMA_3B_GIB),
    )

    plan = device_mod.plan_device_assignments(
        parameters,
        device_mod.default_device_priority("pub4a"),
        requested="auto",
        budget_bytes=int(BUDGET_GIB * GIB),
        registry=registry,
    )

    assert plan.assignments[("retriever_model", "params", "embedding_model")] == (
        FAKE_GPU
    )
    assert plan.assignments[("generation_model",)] == FAKE_GPU


def test_pub5_plan_offloads_the_generator_and_the_transformer() -> None:
    """Qwen 7B fits the budget on its own, so the transformer also gets the GPU."""
    parameters = _parameter_tree(
        embedding="AllMiniLML6V2Embedding",
        generator="Llama32_3BInstruct",
        llm="Qwen25_7BInstruct",
    )
    registry = _registry(
        AllMiniLML6V2Embedding=_component((device_mod.CPU_DEVICE,)),
        Llama32_3BInstruct=_component((FAKE_GPU, "CPU"), LLAMA_3B_GIB),
        Qwen25_7BInstruct=_component((FAKE_GPU, "CPU"), QWEN_7B_GIB),
    )

    plan = device_mod.plan_device_assignments(
        parameters,
        device_mod.default_device_priority("pub5a"),
        requested="auto",
        budget_bytes=int(BUDGET_GIB * GIB),
        registry=registry,
    )

    assert plan.assignments[("generation_model",)] == FAKE_GPU
    assert plan.assignments[("query_transformation", "params", "llm_model")] == FAKE_GPU
    transformation_note = next(
        n for n in plan.notes if n.startswith("query_transformation.llm_model:")
    )
    assert transformation_note == (
        f"query_transformation.llm_model: GPU ({QWEN_7B_MEASURED_GIB:.1f} GiB "
        f"weights fit the {BUDGET_GIB:.1f} GiB budget)"
    )


def test_candidates_are_evaluated_independently_of_each_other() -> None:
    """Two checkpoints that each fit the budget both get the GPU."""
    parameters = {
        "large_model": _ref("LargeModel", device="CPU"),
        "larger_model": _ref("LargerModel", device="CPU"),
    }
    registry = _registry(
        LargeModel=_component((FAKE_GPU, "CPU"), LARGE_FIT_GIB),
        LargerModel=_component((FAKE_GPU, "CPU"), LARGER_FIT_GIB),
    )

    plan = device_mod.plan_device_assignments(
        parameters,
        ("large_model", "larger_model"),
        requested="auto",
        budget_bytes=int(BUDGET_GIB * GIB) + 100 * MIB,
        registry=registry,
    )

    assert plan.assignments == {
        ("large_model",): FAKE_GPU,
        ("larger_model",): FAKE_GPU,
    }


def test_a_checkpoint_larger_than_the_budget_stays_on_the_cpu() -> None:
    """A model that exceeds the budget is denied the GPU and the note says so."""
    parameters = {"generation_model": _ref("OversizedModel", device="CPU")}
    registry = _registry(OversizedModel=_component((FAKE_GPU, "CPU"), OVERSIZED_GIB))

    plan = device_mod.plan_device_assignments(
        parameters,
        ("generation_model",),
        requested="auto",
        budget_bytes=int(BUDGET_GIB * GIB),
        registry=registry,
    )

    assert plan.assignments[("generation_model",)] == device_mod.CPU_DEVICE
    assert plan.notes == [
        f"generation_model: CPU ({OVERSIZED_GIB:.1f} GiB weights exceed the "
        f"{BUDGET_GIB:.1f} GiB budget)"
    ]


def test_a_marginally_over_budget_checkpoint_is_still_offloaded() -> None:
    """Qwen 7B's files are 24 MiB over the budget of the reference machine.

    It loads with 152 MiB of VRAM to spare (measured), so the planner is
    optimistic within :data:`device_mod.VRAM_FIT_TOLERANCE` instead of pushing
    a 25 tok/s GPU stage onto a 4 tok/s CPU one.
    """
    qwen_files = 8098525408  # three q8_0 shards, as ``DOWNLOAD_SIZE_BYTES``
    # The reference machine's real budget: 7956 MiB free - 256 MiB reserve.
    budget = 7700 * MIB
    assert qwen_files > budget, "the fixture no longer models the marginal case"
    parameters = {"generation_model": _ref("Qwen25_7BInstruct", device="CPU")}
    component = type(
        "Qwen25_7BInstruct",
        (),
        {
            "SCHEMA": _FakeSchema((FAKE_GPU, "CPU")),
            "DOWNLOAD_SIZE_BYTES": qwen_files,
        },
    )

    plan = device_mod.plan_device_assignments(
        parameters,
        ("generation_model",),
        requested="auto",
        budget_bytes=budget,
        registry=_registry(Qwen25_7BInstruct=component),
    )

    assert plan.assignments[("generation_model",)] == FAKE_GPU
    assert plan.notes == [
        f"generation_model: GPU ({device_mod.format_bytes_as_gib(qwen_files)} weights "
        f"fit the {device_mod.format_bytes_as_gib(budget)} budget within the "
        "offload tolerance)"
    ]


def test_an_excess_far_beyond_the_tolerance_keeps_the_cpu() -> None:
    """The optimism window is bounded: a much larger file keeps the CPU."""
    parameters = {"generation_model": _ref("OversizedModel", device="CPU")}
    registry = _registry(OversizedModel=_component((FAKE_GPU, "CPU"), OVERSIZED_GIB))

    plan = device_mod.plan_device_assignments(
        parameters,
        ("generation_model",),
        requested="auto",
        budget_bytes=int(BUDGET_GIB * GIB),
        registry=registry,
    )

    assert plan.assignments[("generation_model",)] == device_mod.CPU_DEVICE


def test_fitting_component_does_not_end_the_priority_list() -> None:
    """One candidate too large for the budget does not stop the others."""
    parameters = {
        "big_model": _ref("Qwen25_7BInstruct", device="CPU"),
        "small_model": _ref("Llama32_1BInstruct", device="CPU"),
    }
    registry = _registry(
        Qwen25_7BInstruct=_component((FAKE_GPU, "CPU"), QWEN_7B_GIB),
        Llama32_1BInstruct=_component((FAKE_GPU, "CPU"), LLAMA_1B_GIB),
    )

    plan = device_mod.plan_device_assignments(
        parameters,
        ("big_model", "small_model"),
        requested="auto",
        budget_bytes=3 * GIB,
        registry=registry,
    )

    assert plan.assignments[("big_model",)] == device_mod.CPU_DEVICE
    assert plan.assignments[("small_model",)] == FAKE_GPU


def test_components_outside_the_priority_are_never_planned() -> None:
    """A llama.cpp component under a non-prioritised stage keeps its device."""
    parameters = {
        "retriever_model": _ref(
            "DenseEmbeddingRetriever",
            embedding_model=_ref("E5MistralGGUFEmbedding", device="CPU"),
        ),
        "generation_model": _ref("Llama32_3BInstruct", device="CPU"),
    }
    registry = _registry(
        E5MistralGGUFEmbedding=_component((FAKE_GPU, "CPU"), E5_MISTRAL_GGUF_GIB),
        Llama32_3BInstruct=_component((FAKE_GPU, "CPU"), LLAMA_3B_GIB),
    )

    plan = device_mod.plan_device_assignments(
        parameters,
        device_mod.default_device_priority("pub1"),
        requested="auto",
        budget_bytes=int(BUDGET_GIB * GIB),
        registry=registry,
    )

    assert set(plan.assignments) == {("generation_model",)}


def test_torch_components_are_never_assigned() -> None:
    """A schema whose device enum has no GPU label is left untouched."""
    parameters = {
        "generation_model": _ref("Llama32_3BInstruct", device=FAKE_GPU),
        "retriever_model": _ref(
            "DenseEmbeddingRetriever",
            embedding_model=_ref("AllMiniLML6V2Embedding", device="CPU"),
        ),
    }
    registry = _registry(
        Llama32_3BInstruct=_component((FAKE_GPU, "CPU"), LLAMA_3B_GIB),
        AllMiniLML6V2Embedding=_component((device_mod.CPU_DEVICE,)),
    )

    plan = device_mod.plan_device_assignments(
        parameters,
        ("retriever_model", "generation_model"),
        requested="auto",
        budget_bytes=int(BUDGET_GIB * GIB),
        registry=registry,
    )

    assert set(plan.assignments) == {("generation_model",)}
    assert plan.assignments[("generation_model",)] == FAKE_GPU
    assert not any("AllMiniLML6V2Embedding" in note for note in plan.notes)


def test_unknown_checkpoint_size_keeps_the_cpu_and_explains_it() -> None:
    """A component whose size cannot be read is not offloaded blindly."""
    parameters = {"generation_model": _ref("MysteryGgufModel", device="CPU")}
    registry = _registry(MysteryGgufModel=_component((FAKE_GPU, "CPU")))

    plan = device_mod.plan_device_assignments(
        parameters,
        ("generation_model",),
        requested="auto",
        budget_bytes=int(BUDGET_GIB * GIB),
        registry=registry,
    )

    assert plan.assignments[("generation_model",)] == device_mod.CPU_DEVICE
    assert plan.notes == [
        f"generation_model: CPU (checkpoint size unknown; cannot compare it "
        f"with the {BUDGET_GIB:.1f} GiB budget)"
    ]


def test_explicitly_demoted_components_stay_on_the_cpu() -> None:
    """A demoted reference keeps the CPU even though its weights fit."""
    parameters = {"generation_model": _ref("Llama32_3BInstruct", device="CPU")}
    registry = _registry(
        Llama32_3BInstruct=_component((FAKE_GPU, "CPU"), LLAMA_3B_GIB),
    )

    plan = device_mod.plan_device_assignments(
        parameters,
        ("generation_model",),
        requested="auto",
        budget_bytes=int(BUDGET_GIB * GIB),
        registry=registry,
        demoted=[("generation_model",)],
    )

    assert plan.assignments[("generation_model",)] == device_mod.CPU_DEVICE
    assert plan.notes == [
        f"generation_model: CPU (demoted after an out-of-memory failure; "
        f"{LLAMA_3B_GIB:.1f} GiB weights fit the {BUDGET_GIB:.1f} GiB budget)"
    ]


def test_largest_gpu_assignment_picks_the_biggest_footprint() -> None:
    """The demotion candidate is the largest component still on the GPU."""
    parameters = _parameter_tree(
        embedding="AllMiniLML6V2Embedding",
        generator="Llama32_3BInstruct",
        llm="Qwen25_7BInstruct",
    )
    registry = _registry(
        AllMiniLML6V2Embedding=_component((device_mod.CPU_DEVICE,)),
        Llama32_3BInstruct=_component((FAKE_GPU, "CPU"), LLAMA_3B_GIB),
        Qwen25_7BInstruct=_component((FAKE_GPU, "CPU"), QWEN_7B_GIB),
    )
    plan = device_mod.plan_device_assignments(
        parameters,
        device_mod.default_device_priority("pub5a"),
        requested="auto",
        budget_bytes=int(BUDGET_GIB * GIB),
        registry=registry,
    )

    largest = device_mod.largest_gpu_assignment(plan)

    assert largest == (
        ("query_transformation", "params", "llm_model"),
        int(QWEN_7B_GIB * GIB),
    )


def test_largest_gpu_assignment_is_none_without_gpu_components() -> None:
    """Nothing is left to demote once every component runs on the CPU."""
    plan = device_mod.DevicePlan(
        assignments={("generation_model",): device_mod.CPU_DEVICE},
        notes=["generation_model: CPU (7.9 GiB weights exceed the budget)"],
        gpu_label=FAKE_GPU,
        budget_bytes=GIB,
    )

    assert device_mod.largest_gpu_assignment(plan) is None


def test_plan_never_mutates_the_parameters() -> None:
    """Planning is pure: the tree is only changed by ``apply_device_plan``."""
    parameters = _parameter_tree(
        embedding="E5MistralGGUFEmbedding", generator="Llama32_3BInstruct"
    )
    snapshot = {
        "chunking_model": dict(parameters["chunking_model"]["params"]),
        "generation_model": dict(parameters["generation_model"]["params"]),
    }
    registry = _registry(
        E5MistralGGUFEmbedding=_component((FAKE_GPU, "CPU"), E5_MISTRAL_GGUF_GIB),
        Llama32_3BInstruct=_component((FAKE_GPU, "CPU"), LLAMA_3B_GIB),
    )

    device_mod.plan_device_assignments(
        parameters,
        device_mod.default_device_priority("pub4a"),
        requested="auto",
        budget_bytes=int(BUDGET_GIB * GIB),
        registry=registry,
    )

    assert parameters["chunking_model"]["params"] == snapshot["chunking_model"]
    assert parameters["generation_model"]["params"] == snapshot["generation_model"]


def test_local_checkpoint_size_sums_multi_part_checkpoints(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A sharded checkpoint is measured whole, not by its first shard."""
    for shard in ("model-00001-of-00002.gguf", "model-00002-of-00002.gguf"):
        (tmp_path / shard).write_bytes(b"0" * 1024)
    component = type(
        "ShardedGguf",
        (),
        {
            "SCHEMA": _FakeSchema((FAKE_GPU, "CPU")),
            "GGUF_PATTERN": "model-*.gguf",
            "DOWNLOAD_SIZE_BYTES": 4096,
            "_local_gguf_path": classmethod(
                lambda cls: tmp_path / "model-00001-of-00002.gguf"
            ),
        },
    )

    assert device_mod.estimate_component_vram_bytes(component) == 2048


# ---------------------------------------------------------------------------
# apply_device_plan
# ---------------------------------------------------------------------------


def test_plan_reads_the_stages_of_a_nested_session_payload() -> None:
    """A real session payload keeps its stages under ``parameters``."""
    parameters = {
        "model_name": "RAGPipeline",
        "task_name": "RAGTask",
        "name": "Pub 5a",
        "description": None,
        "parameters": {
            "generation_model": _ref(
                "Llama32_3BInstruct",
                max_tokens=1024,
                context_window=8192,
                device="CPU",
            ),
            "query_transformation": _ref(
                "LLMQueryRewriter",
                llm_model=_ref(
                    "Qwen25_7BInstruct",
                    max_tokens=256,
                    context_window=4096,
                    device="CPU",
                ),
                history_window=2,
            ),
        },
    }
    registry = _registry(
        Llama32_3BInstruct=_component((FAKE_GPU, "CPU"), LLAMA_3B_GIB),
        Qwen25_7BInstruct=_component((FAKE_GPU, "CPU"), QWEN_7B_GIB),
    )

    plan = device_mod.plan_device_assignments(
        parameters,
        device_mod.default_device_priority("pub5a"),
        requested="auto",
        budget_bytes=int(BUDGET_GIB * GIB),
        registry=registry,
    )

    assert plan.assignments == {
        ("parameters", "generation_model"): FAKE_GPU,
        ("parameters", "query_transformation", "params", "llm_model"): FAKE_GPU,
    }
    assert plan.notes == [
        f"generation_model: GPU ({LLAMA_3B_GIB:.1f} GiB weights fit the "
        f"{BUDGET_GIB:.1f} GiB budget)",
        f"query_transformation.llm_model: GPU ({QWEN_7B_GIB:.1f} GiB weights fit "
        f"the {BUDGET_GIB:.1f} GiB budget)",
    ]


def test_apply_device_plan_only_writes_the_planned_refs() -> None:
    """Only planned references change, and only their ``device`` parameter."""
    parameters = _parameter_tree(
        embedding="E5MistralGGUFEmbedding",
        generator="Llama32_3BInstruct",
        llm="Qwen25_7BInstruct",
    )
    before = _copy(parameters)
    registry = _registry(
        E5MistralGGUFEmbedding=_component((FAKE_GPU, "CPU"), E5_MISTRAL_GGUF_GIB),
        Llama32_3BInstruct=_component((FAKE_GPU, "CPU"), LLAMA_3B_GIB),
        Qwen25_7BInstruct=_component((FAKE_GPU, "CPU"), QWEN_7B_GIB),
    )
    plan = device_mod.plan_device_assignments(
        parameters,
        device_mod.default_device_priority("pub5b"),
        requested="auto",
        budget_bytes=int(BUDGET_GIB * GIB),
        registry=registry,
    )

    device_mod.apply_device_plan(parameters, plan)

    assert parameters["generation_model"]["params"]["device"] == FAKE_GPU
    assert (
        parameters["query_transformation"]["params"]["llm_model"]["params"]["device"]
        == FAKE_GPU
    )
    assert parameters["chunking_model"] == before["chunking_model"]
    assert parameters["prompt"] == before["prompt"]
    assert parameters["retriever_model"] == before["retriever_model"]


def test_apply_device_plan_creates_missing_params() -> None:
    """A reference without ``params`` still receives its device."""
    parameters: Dict[str, Any] = {
        "generation_model": {"component": "Llama32_3BInstruct"}
    }
    plan = device_mod.DevicePlan(
        assignments={("generation_model",): FAKE_GPU},
        notes=["generation_model: GPU (1.9 GiB weights fit the budget)"],
        gpu_label=FAKE_GPU,
        budget_bytes=GIB,
    )

    device_mod.apply_device_plan(parameters, plan)

    assert parameters["generation_model"] == {
        "component": "Llama32_3BInstruct",
        "params": {"device": FAKE_GPU},
    }


def test_default_device_priority_of_pub4a_starts_with_the_retriever() -> None:
    """``pub4a`` indexes through a 7B embedding model, so it goes first."""
    assert device_mod.default_device_priority("pub4a") == (
        "retriever_model",
        "generation_model",
    )


def test_default_device_priority_of_other_pipelines_starts_with_the_generator() -> None:
    """Generation dominates every other pipeline."""
    for key in ("pub1", "pub2", "pub3", "pub4b", "pub5a", "pub5b", "pub5c"):
        assert device_mod.default_device_priority(key) == (
            "generation_model",
            "query_transformation",
        )


# ---------------------------------------------------------------------------
# Out-of-memory demotion of a pipeline iteration
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Minimal stand-in for a TestClient response."""

    def __init__(self, status_code: int, json_data: Any = None, text: str = "") -> None:
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self) -> Any:
        """Return the decoded payload."""
        return self._json


class _FakeRagClient:
    """Fake API client that fails the first N sessions with an OOM error.

    A session creation is where a pipeline instantiates its stages, so an
    allocation failure there models a checkpoint that does not fit the GPU.
    Every other route succeeds and a turn returns one plain answer.
    """

    def __init__(self, out_of_memory_attempts: int) -> None:
        self._remaining_failures = out_of_memory_attempts
        self.session_names: List[str] = []
        self.sessions_created = 0

    def post(self, url: str, **kwargs: Any) -> _FakeResponse:
        """Answer a POST, failing a session creation while scripted to."""
        if url == "/api/v1/generative-session/":
            self.session_names.append(kwargs["json"]["name"])
            if self._remaining_failures > 0:
                self._remaining_failures -= 1
                raise RuntimeError(
                    "CUDA error: out of memory (failed to allocate 2.00 GiB)"
                )
            self.sessions_created += 1
            return _FakeResponse(201, {"id": self.sessions_created})
        if url.startswith("/api/v1/rag/sessions/"):
            return _FakeResponse(200, [])
        return _FakeResponse(201, {"id": 1})

    def get(self, url: str) -> _FakeResponse:
        """Return a finished process carrying a single answer row."""
        return _FakeResponse(
            200,
            {
                "status": RunStatus.FINISHED.value,
                "output": [{"data_type": "str", "data": "answer"}],
            },
        )


def _pub5_registry() -> Dict[str, Dict[str, Any]]:
    """Registry of a publication 5 pipeline: Llama 3B plus Qwen 7B."""
    return _registry(
        AllMiniLML6V2Embedding=_component((device_mod.CPU_DEVICE,)),
        Llama32_3BInstruct=_component((FAKE_GPU, "CPU"), LLAMA_3B_GIB),
        Qwen25_7BInstruct=_component((FAKE_GPU, "CPU"), QWEN_7B_GIB),
    )


def _pub5_parameters() -> Dict[str, Any]:
    """Parameters of a publication 5 pipeline: two GPU-assignable components.

    The shape matches the real session payload: its stages live under
    ``parameters``.
    """
    return {
        "name": "Pub 5a",
        "model_name": "RAGPipeline",
        "task_name": "RAGTask",
        "description": None,
        "parameters": {
            "chunking_model": _ref("TokenChunkModel", chunk_size=300, chunk_overlap=60),
            "retriever_model": _ref(
                "DenseEmbeddingRetriever",
                embedding_model=_ref("AllMiniLML6V2Embedding", device="CPU"),
                similarity_metric="cosine",
                top_k=10,
            ),
            "generation_model": _ref(
                "Llama32_3BInstruct",
                max_tokens=1024,
                context_window=8192,
                device="CPU",
            ),
            "prompt": _ref("DefaultRAGGenerationPrompt", language="en"),
            "query_transformation": _ref(
                "LLMQueryRewriter",
                llm_model=_ref(
                    "Qwen25_7BInstruct",
                    max_tokens=256,
                    context_window=4096,
                    device="CPU",
                ),
                history_window=2,
            ),
        },
    }


def _runner(
    tmp_path: Path,
    client: _FakeRagClient,
    registry: Dict[str, Dict[str, Any]],
    *,
    budget_gib: float = BUDGET_GIB,
) -> PipelineBenchmarkRunner:
    """Build a runner wired to the fake client, registry and budget."""
    runner = PipelineBenchmarkRunner(BenchmarkConfig(results_dir=tmp_path))
    runner._client = client  # type: ignore[assignment]
    runner._registry = registry
    runner._gpu_budget_bytes = int(budget_gib * GIB)
    runner._document_ids = [1]
    runner._user_simulator = None
    return runner


def _read_configs(tmp_path: Path, folder: str) -> Dict[str, Any]:
    """Return the ``configs.json`` of one pipeline run folder."""
    path = tmp_path / "pipelines" / folder / "configs.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_out_of_memory_demotes_the_largest_component_and_retries(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """One allocation failure demotes Qwen 7B and the retried iteration passes."""
    client = _FakeRagClient(out_of_memory_attempts=1)
    runner = _runner(tmp_path, client, _pub5_registry())

    results = runner.run_pipeline(
        pipeline_key="pub5a",
        pipeline_name="Publication 5a",
        config_fn=lambda doc_ids: _pub5_parameters(),
        iterations=1,
        messages_per_conversation=1,
        pipeline_index=1,
    )

    assert results[0].success is True
    assert len(results[0].turns) == 1
    printed = capsys.readouterr().out
    assert (
        "  Out of memory with query_transformation.llm_model on the GPU; "
        "retrying iter0 with it on CPU." in printed
    )

    configs = _read_configs(tmp_path, "1 - Publication 5a")
    assert set(configs) == {"iter0", "iter0-retry1"}
    assert configs["iter0"]["device_plan"]["demoted"] == []
    assert configs["iter0-retry1"]["device_plan"]["demoted"] == [
        "query_transformation.llm_model"
    ]
    assert configs["iter0-retry1"]["device_plan"]["assignments"] == {
        "generation_model": FAKE_GPU,
        "query_transformation.llm_model": device_mod.CPU_DEVICE,
    }
    assert results[0].pipeline_config["device_plan"]["demoted"] == [
        "query_transformation.llm_model"
    ]


def test_a_second_out_of_memory_demotes_the_remaining_component(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The next failure demotes the generator too, and the retry passes."""
    client = _FakeRagClient(out_of_memory_attempts=2)
    runner = _runner(tmp_path, client, _pub5_registry())

    results = runner.run_pipeline(
        pipeline_key="pub5a",
        pipeline_name="Publication 5a",
        config_fn=lambda doc_ids: _pub5_parameters(),
        iterations=1,
        messages_per_conversation=1,
        pipeline_index=1,
    )

    assert results[0].success is True
    printed = capsys.readouterr().out
    assert "Out of memory with query_transformation.llm_model" in printed
    assert "Out of memory with generation_model" in printed

    configs = _read_configs(tmp_path, "1 - Publication 5a")
    assert set(configs) == {"iter0", "iter0-retry1", "iter0-retry2"}
    assert configs["iter0-retry2"]["device_plan"]["demoted"] == [
        "query_transformation.llm_model",
        "generation_model",
    ]
    assert set(configs["iter0-retry2"]["device_plan"]["assignments"].values()) == {
        device_mod.CPU_DEVICE
    }


def test_a_pipeline_without_gpu_components_is_never_retried(tmp_path: Path) -> None:
    """Nothing is left to demote, so the failure is reported instead of retried."""
    client = _FakeRagClient(out_of_memory_attempts=1)
    runner = _runner(tmp_path, client, _pub5_registry(), budget_gib=1.0)

    results = runner.run_pipeline(
        pipeline_key="pub5a",
        pipeline_name="Publication 5a",
        config_fn=lambda doc_ids: _pub5_parameters(),
        iterations=1,
        messages_per_conversation=1,
        pipeline_index=1,
    )

    assert len(client.session_names) == 1
    assert results[0].success is False
    assert device_mod.detect_out_of_memory(results[0].error_message) is True

    configs = _read_configs(tmp_path, "1 - Publication 5a")
    assert set(configs) == {"iter0"}
    assert set(configs["iter0"]["device_plan"]["assignments"].values()) == {
        device_mod.CPU_DEVICE
    }


def test_retried_attempt_uses_a_distinct_session_name(tmp_path: Path) -> None:
    """The UNIQUE session name of the failed attempt is not reused."""
    client = _FakeRagClient(out_of_memory_attempts=1)
    runner = _runner(tmp_path, client, _pub5_registry())

    runner.run_pipeline(
        pipeline_key="pub5a",
        pipeline_name="Publication 5a",
        config_fn=lambda doc_ids: _pub5_parameters(),
        iterations=1,
        messages_per_conversation=1,
        pipeline_index=1,
    )

    assert len(client.session_names) == 2
    assert client.session_names[0] != client.session_names[1]
    assert "retry 1" in client.session_names[1]


# ---------------------------------------------------------------------------
# Device resolution of the component benchmarks
# ---------------------------------------------------------------------------


def test_llm_device_resolution_accepts_auto() -> None:
    """``components --device auto`` offloads to the GPU like the pipelines do."""
    from RAG_benchmark.app.components.llm import _resolve_llm_device

    assert _resolve_llm_device("auto") == FAKE_GPU
    assert _resolve_llm_device("CPU") == device_mod.CPU_DEVICE


def test_component_llm_benchmarks_forward_the_resolved_device(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every LLM benchmark config receives the resolved label, not ``auto``."""
    from RAG_benchmark.app.components import llm as llm_mod

    captured: Dict[str, Any] = {}

    def fake_run_configs(configs, category, execute_fn, logger, skip_statuses=None):
        captured["devices"] = {config["params"]["device"] for config in configs}
        captured["category"] = category

    monkeypatch.setattr(llm_mod, "run_configs", fake_run_configs)

    llm_mod.run_all_llm_benchmarks(None, iterations=1, device="auto")

    assert captured["devices"] == {FAKE_GPU}
    assert captured["category"] == "llm"


def test_embedding_configs_keep_torch_converters_on_the_cpu() -> None:
    """Only the GGUF converter accepts the llama.cpp GPU label."""
    from RAG_benchmark.app.components import embedding as embedding_mod

    gguf = type(
        "E5MistralGGUFEmbedding",
        (),
        {"SCHEMA": _FakeSchema((FAKE_GPU, "CPU"))},
    )
    torch_backed = type(
        "AllMiniLML6V2Embedding",
        (),
        {"SCHEMA": _FakeSchema((device_mod.CPU_DEVICE,))},
    )

    assert embedding_mod._embedding_device(gguf, FAKE_GPU) == FAKE_GPU
    assert embedding_mod._embedding_device(torch_backed, FAKE_GPU) == (
        embedding_mod.EMBEDDING_DEVICE
    )
    assert embedding_mod._embedding_device(gguf, device_mod.CPU_DEVICE) == (
        embedding_mod.EMBEDDING_DEVICE
    )


def _fake_embedding_converter(
    name: str, device_enum: Sequence[str], model_name: str
) -> type:
    """Build a converter class with the surface the config builder reads."""
    return type(
        name,
        (),
        {
            "SCHEMA": _FakeSchema(device_enum),
            "MODEL_NAME": model_name,
            "get_schema": classmethod(lambda cls: {"properties": {}}),
        },
    )


def test_embedding_benchmarks_apply_the_resolved_device(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The embedding runner rebuilds its matrix with the resolved device."""
    from RAG_benchmark.app.components import embedding as embedding_mod

    gguf = _fake_embedding_converter(
        "E5MistralGGUFEmbedding", (FAKE_GPU, "CPU"), "gguf/e5"
    )
    torch_backed = _fake_embedding_converter(
        "AllMiniLML6V2Embedding", (device_mod.CPU_DEVICE,), "mini/lm"
    )
    monkeypatch.setattr(
        embedding_mod, "TEXT_EMBEDDING_CONVERTERS", (gguf, torch_backed)
    )
    monkeypatch.setattr(embedding_mod, "_sample_passages", lambda: ["a", "b"])
    captured: Dict[str, Any] = {}

    def fake_run_configs(configs, category, execute_fn, logger, skip_statuses=None):
        captured["devices"] = {
            config["component_class"]: config["params"]["device"] for config in configs
        }
        captured["category"] = category

    monkeypatch.setattr(embedding_mod, "run_configs", fake_run_configs)
    logger = type("FakeLogger", (), {"output_dir": Path(".")})()

    embedding_mod.run_all_embedding_benchmarks(
        logger, iterations=1, device="auto", download_missing_models=False
    )

    assert captured["devices"] == {
        "E5MistralGGUFEmbedding": FAKE_GPU,
        "AllMiniLML6V2Embedding": device_mod.CPU_DEVICE,
    }
    assert captured["category"] == "embedding"


def _copy(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-copy a parameter tree."""
    return copy.deepcopy(parameters)

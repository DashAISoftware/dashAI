"""Unit tests for the generative workflow components.

A workflow says how a generative session runs. Like a task, it is defined by
the components it relates to, not by a configuration: ``InferenceWorkflow``
relates the generative tasks it runs directly, ``RAGWorkflow`` the text to text
task plus the chunkers, retrievers, prompts and query transformations it uses.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

import pytest

from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.initial_components import get_initial_components
from DashAI.back.models.base_generative_model import BaseGenerativeModel
from DashAI.back.models.RAG import RAG_constants
from DashAI.back.models.RAG.RAG_constants import RAG_WORKFLOW_NAME
from DashAI.back.models.RAG.RAG_pipeline import (
    ChunkReference,
    PipelineStageTimings,
    RAGGenerationOutput,
)
from DashAI.back.tasks.text_to_text_generation_task import TextToTextGenerationTask
from DashAI.back.workflows import (
    INFERENCE_WORKFLOW_NAME,
    BaseGenerativeWorkflow,
    InferenceWorkflow,
    RAGWorkflow,
)


class FakeTextModelSchema(BaseSchema):
    """Empty parameter schema for the fake text model."""


class FakeTextModel(BaseGenerativeModel):
    """Smallest generative model compatible with the text to text task."""

    COMPATIBLE_COMPONENTS = ["TextToTextGenerationTask"]
    SCHEMA = FakeTextModelSchema

    def __init__(self, **kwargs):
        """Accept and ignore any parameters."""

    def generate(self, input: List[Dict[str, str]]) -> List[str]:
        """Return a fixed answer.

        Parameters
        ----------
        input : List[Dict[str, str]]
            Chat messages.

        Returns
        -------
        List[str]
            A single fixed answer.
        """
        return ["answer"]


def _make_timings() -> PipelineStageTimings:
    """Build stage timings with predictable values.

    Returns
    -------
    PipelineStageTimings
        Timings for the four RAG stages.
    """
    return PipelineStageTimings(
        transformation_ms=1.25,
        retrieval_ms=2.5,
        generation_ms=3.75,
        total_ms=7.5,
    )


def _rag_output(**overrides: Any) -> RAGGenerationOutput:
    """Build a RAG pipeline output with sensible defaults.

    Parameters
    ----------
    **overrides : Any
        Fields replacing the defaults.

    Returns
    -------
    RAGGenerationOutput
        The pipeline output.
    """
    fields = {
        "message": "m",
        "chunks": {},
        "queries": ["q"],
        "trace": [],
        "timings": _make_timings(),
    }
    fields.update(overrides)
    return RAGGenerationOutput(**fields)


@pytest.fixture(name="registry")
def fixture_registry() -> ComponentRegistry:
    """Registry holding the text to text task, one model and both workflows.

    Returns
    -------
    ComponentRegistry
        A small registry built from real workflow classes.
    """
    return ComponentRegistry(
        initial_components=[
            TextToTextGenerationTask,
            FakeTextModel,
            InferenceWorkflow,
            RAGWorkflow,
        ]
    )


def test_workflow_names_match_their_constants():
    """The constants other layers compare against are the class names."""
    assert RAGWorkflow.__name__ == RAG_WORKFLOW_NAME == "RAGWorkflow"
    assert InferenceWorkflow.__name__ == INFERENCE_WORKFLOW_NAME == "InferenceWorkflow"


def test_both_workflows_derive_from_the_base():
    """Every workflow shares the base contract."""
    assert issubclass(RAGWorkflow, BaseGenerativeWorkflow)
    assert issubclass(InferenceWorkflow, BaseGenerativeWorkflow)


def test_workflows_declare_only_their_compatible_components():
    """A workflow has no task, job, model parameter or schema of its own."""
    for workflow in (InferenceWorkflow, RAGWorkflow):
        for attribute in ("TASK", "JOB", "MODEL_PARAMETER", "SCHEMA"):
            assert not hasattr(workflow, attribute), (workflow, attribute)


def test_inference_workflow_runs_the_generative_tasks():
    """Inference relates every built in generative task."""
    assert InferenceWorkflow.COMPATIBLE_COMPONENTS == [
        "TextToTextGenerationTask",
        "TextToImageGenerationTask",
        "ControlNetTask",
    ]


def test_rag_workflow_runs_the_text_to_text_task():
    """RAG runs text to text and relates no other task."""
    tasks = [
        name for name in RAGWorkflow.COMPATIBLE_COMPONENTS if name.endswith("Task")
    ]

    assert tasks == ["TextToTextGenerationTask"]


def test_rag_workflow_relates_its_building_blocks():
    """The chunkers, retrievers, prompts and transformations RAG can use."""
    related = set(RAGWorkflow.COMPATIBLE_COMPONENTS)

    assert {"CharacterChunkModel", "TokenChunkModel"} <= related
    assert {"BM25Retriever", "DenseEmbeddingRetriever"} <= related
    assert {"DefaultRAGGenerationPrompt", "CustomRAGGenerationPrompt"} <= related
    assert {"LLMQueryRewriter", "LLMQueryDecomposer"} <= related


def test_every_compatible_component_is_built_in():
    """A workflow names components the app registers, never stale names."""
    names = {component.__name__ for component in get_initial_components()}

    for workflow in (InferenceWorkflow, RAGWorkflow):
        assert set(workflow.COMPATIBLE_COMPONENTS) <= names, workflow


def test_registry_files_workflows_as_plain_components(registry):
    """Workflows have their own type and are not configurable objects."""
    names = {
        component["name"]
        for component in registry.get_components_by_types(select="GenerativeWorkflow")
    }

    assert names == {"InferenceWorkflow", "RAGWorkflow"}
    assert registry["RAGWorkflow"]["type"] == "GenerativeWorkflow"
    assert registry["RAGWorkflow"]["configurable_object"] is False
    assert registry["RAGWorkflow"]["schema"] is None
    assert registry["RAGWorkflow"]["metadata"] is None


def test_task_and_workflow_are_related_both_ways(registry):
    """The registry relates a workflow and its task in both directions."""
    task_related = {
        component["name"]: component["type"]
        for component in registry.get_related_components("TextToTextGenerationTask")
    }
    workflow_related = {
        component["name"]
        for component in registry.get_related_components("RAGWorkflow")
    }

    assert task_related == {
        "FakeTextModel": "GenerativeModel",
        "InferenceWorkflow": "GenerativeWorkflow",
        "RAGWorkflow": "GenerativeWorkflow",
    }
    assert workflow_related == {"TextToTextGenerationTask"}


def test_both_workflows_are_built_in():
    """The app registers both workflows at startup."""
    names = {component.__name__ for component in get_initial_components()}

    assert {"InferenceWorkflow", "RAGWorkflow"} <= names


def test_rag_output_constants_match_the_wire_format():
    """The output row data types have a single source of truth."""
    assert RAG_constants.RAG_OUTPUT_QUERIES_TYPE == "Queries"
    assert RAG_constants.RAG_OUTPUT_CHUNKS_TYPE == "Dict"
    assert RAG_constants.RAG_OUTPUT_TRACE_TYPE == "Trace"
    assert RAG_constants.RAG_OUTPUT_TIMINGS_TYPE == "Timings"
    assert RAG_constants.RAG_OUTPUT_MESSAGE_TYPE == "str"


class TestRAGWorkflowProcessOutput:
    """process_output emits the five typed output rows in pipeline order."""

    def test_five_typed_rows_in_pipeline_order(self):
        """Rows are Queries, Dict, Trace, Timings, then str."""
        chunks = {
            "1_0": ChunkReference(
                document_id=1,
                document_name="doc.txt",
                document_position=0,
                text="chunk text",
            )
        }
        trace = [
            {
                "query": "q one",
                "retriever": {"name": "BM25Retriever", "chunks": ["1_0"]},
            }
        ]
        timings = _make_timings()
        output = _rag_output(
            message="the answer",
            chunks=chunks,
            queries=["q one", "q two"],
            trace=trace,
            timings=timings,
        )

        result = RAGWorkflow().process_output(output)

        assert [data_type for _data, data_type in result] == [
            "Queries",
            "Dict",
            "Trace",
            "Timings",
            "str",
        ]
        assert result[0] == (
            json.dumps(["q one", "q two"], ensure_ascii=False),
            "Queries",
        )
        parsed = json.loads(result[1][0])
        assert parsed["1_0"]["document_id"] == 1
        assert parsed["1_0"]["document_name"] == "doc.txt"
        assert parsed["1_0"]["text"] == "chunk text"
        assert json.loads(result[2][0]) == trace
        parsed_timings = json.loads(result[3][0])
        assert list(parsed_timings) == [
            "transformation_ms",
            "retrieval_ms",
            "generation_ms",
            "total_ms",
        ]
        assert parsed_timings == timings.to_dict()
        assert result[4] == ("the answer", "str")

    def test_empty_chunks(self):
        """Empty chunks and trace still give the five rows."""
        timings = _make_timings()
        output = _rag_output(
            message="no context answer",
            queries=["no context"],
            timings=timings,
        )

        result = RAGWorkflow().process_output(output)

        assert len(result) == 5
        assert result[0] == (
            json.dumps(["no context"], ensure_ascii=False),
            "Queries",
        )
        assert result[1][1] == "Dict"
        assert json.loads(result[1][0]) == {}
        assert result[2] == ("[]", "Trace")
        assert result[3][1] == "Timings"
        assert json.loads(result[3][0]) == timings.to_dict()
        assert result[4] == ("no context answer", "str")

    def test_multiple_chunks(self):
        """Every chunk is serialized in the Dict row."""
        chunks = {
            "1_0": ChunkReference(1, "a.txt", 0, "text A"),
            "2_1": ChunkReference(2, "b.txt", 1, "text B"),
            "3_2": ChunkReference(3, "c.txt", 2, "text C"),
        }

        result = RAGWorkflow().process_output(_rag_output(chunks=chunks))

        parsed = json.loads(result[1][0])
        assert len(parsed) == 3
        assert parsed["1_0"]["text"] == "text A"
        assert parsed["2_1"]["text"] == "text B"
        assert parsed["3_2"]["text"] == "text C"

    def test_message_is_string_cast(self):
        """A non string message is cast to str."""
        result = RAGWorkflow().process_output(_rag_output(message=42))

        assert result[4] == ("42", "str")

    def test_queries_serialized_without_ascii_escaping(self):
        """The Queries row keeps non ASCII characters and the list shape."""
        queries = ["consultá", "quería"]

        result = RAGWorkflow().process_output(_rag_output(queries=queries))

        assert result[0][0] == json.dumps(queries, ensure_ascii=False)
        assert json.loads(result[0][0]) == queries

    def test_trace_row_round_trips_through_json(self):
        """The Trace row decodes back to the original nested nodes."""
        trace = [
            {
                "query": "q1",
                "retriever": {
                    "name": "ParallelRetriever",
                    "chunks": ["1_0", "2_1"],
                    "children": [
                        {"name": "BM25Retriever", "chunks": ["1_0"]},
                        {"name": "TFIDFRetriever", "chunks": ["2_1"]},
                    ],
                },
            }
        ]

        result = RAGWorkflow().process_output(_rag_output(queries=["q1"], trace=trace))

        assert json.loads(result[2][0]) == trace

    def test_timings_row_has_the_exact_four_float_keys(self):
        """The Timings row holds exactly the four timing fields as floats."""
        result = RAGWorkflow().process_output(_rag_output())

        parsed = json.loads(result[3][0])
        assert list(parsed.keys()) == [
            "transformation_ms",
            "retrieval_ms",
            "generation_ms",
            "total_ms",
        ]
        assert all(isinstance(value, float) for value in parsed.values())

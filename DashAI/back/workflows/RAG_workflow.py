import json
from typing import Any, Dict, List, Tuple

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.RAG_constants import (
    RAG_OUTPUT_CHUNKS_TYPE,
    RAG_OUTPUT_MESSAGE_TYPE,
    RAG_OUTPUT_QUERIES_TYPE,
    RAG_OUTPUT_TIMINGS_TYPE,
    RAG_OUTPUT_TRACE_TYPE,
    RAG_PARAM_GENERATION_MODEL,
)
from DashAI.back.models.RAG.RAG_pipeline import RAGGenerationOutput, RAGPipelineSchema
from DashAI.back.workflows.base_generative_workflow import BaseGenerativeWorkflow


class RAGWorkflow(BaseGenerativeWorkflow):
    """Retrieval-Augmented Generation over the session's documents.

    Built on the text to text task: the session model is the generation LLM
    named by ``generation_model``, the RAG schema validates the session
    parameters and ``RAGJob`` runs each turn, retrieving chunks before the
    LLM answers.
    """

    TASK = "TextToTextGenerationTask"
    MODEL_PARAMETER = RAG_PARAM_GENERATION_MODEL
    SCHEMA = RAGPipelineSchema
    JOB = "RAGJob"

    metadata: Dict[str, Any] = {
        "outputs": {
            RAG_OUTPUT_QUERIES_TYPE: {"min": 1, "max": 1},
            RAG_OUTPUT_CHUNKS_TYPE: {"min": 1, "max": 1},
            RAG_OUTPUT_TRACE_TYPE: {"min": 1, "max": 1},
            RAG_OUTPUT_TIMINGS_TYPE: {"min": 1, "max": 1},
            RAG_OUTPUT_MESSAGE_TYPE: {"min": 1, "max": 1},
        },
    }

    DISPLAY_NAME: MultilingualString = MultilingualString(
        en="Retrieval-Augmented Generation",
        es="Generación Aumentada por Recuperación (RAG)",
        pt="Geração Aumentada por Recuperação (RAG)",
        de="Retrieval-Augmented Generation (RAG)",
        zh="检索增强生成（RAG）",
    )
    DESCRIPTION: MultilingualString = MultilingualString(
        en=(
            "This workflow generates a text response with an LLM model based on"
            " documents provided."
        ),
        es=(
            "Este flujo de trabajo genera una respuesta de texto con un modelo"
            " LLM basado en los documentos proporcionados."
        ),
        pt=(
            "Este fluxo de trabalho gera uma resposta de texto com um modelo"
            " LLM com base nos documentos fornecidos."
        ),
        de=(
            "Dieser Workflow generiert eine Textantwort mit einem LLM-Modell"
            " anhand der bereitgestellten Dokumente."
        ),
        zh="此工作流基于提供的文档，使用 LLM 模型生成文本响应。",
    )

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Return the task the workflow builds on and its output rows.

        Returns
        -------
        Dict[str, Any]
            ``{"task": ..., "outputs": ...}`` where ``outputs`` maps each output
            row type to its cardinality.
        """
        metadata = super().get_metadata()
        metadata["outputs"] = dict(cls.metadata["outputs"])
        return metadata

    def process_output(
        self,
        output: RAGGenerationOutput,
        **kwargs: Any,
    ) -> List[Tuple[str, str]]:
        """Turn a pipeline output into the five typed output rows.

        Rows follow the pipeline order: ``Queries`` (the JSON query list),
        ``Dict`` (the JSON chunk map), ``Trace`` (the JSON per query retrieval
        trace), ``Timings`` (the JSON per stage timings) and ``str`` (the
        answer message).

        Parameters
        ----------
        output : RAGGenerationOutput
            The typed output of ``RAGPipeline.generate()``.
        **kwargs : Any
            Unused; accepted so callers can pass the generic job arguments.

        Returns
        -------
        List[Tuple[str, str]]
            ``(data, type)`` rows ordered Queries, Dict, Trace, Timings, str.
        """
        queries_json = json.dumps(list(output.queries), ensure_ascii=False)
        chunks_json = json.dumps(
            {key: ref.to_dict() for key, ref in output.chunks.items()},
            ensure_ascii=False,
        )
        trace_json = json.dumps(list(output.trace), ensure_ascii=False)
        timings_json = json.dumps(output.timings.to_dict(), ensure_ascii=False)
        return [
            (queries_json, RAG_OUTPUT_QUERIES_TYPE),
            (chunks_json, RAG_OUTPUT_CHUNKS_TYPE),
            (trace_json, RAG_OUTPUT_TRACE_TYPE),
            (timings_json, RAG_OUTPUT_TIMINGS_TYPE),
            (str(output.message), RAG_OUTPUT_MESSAGE_TYPE),
        ]

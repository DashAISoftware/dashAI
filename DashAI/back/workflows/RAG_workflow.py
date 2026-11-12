import json
from typing import TYPE_CHECKING, Any, List, Tuple

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.RAG_constants import (
    RAG_OUTPUT_CHUNKS_TYPE,
    RAG_OUTPUT_MESSAGE_TYPE,
    RAG_OUTPUT_QUERIES_TYPE,
    RAG_OUTPUT_TIMINGS_TYPE,
    RAG_OUTPUT_TRACE_TYPE,
)
from DashAI.back.workflows.base_generative_workflow import BaseGenerativeWorkflow

if TYPE_CHECKING:
    from DashAI.back.models.RAG.RAG_pipeline import RAGGenerationOutput


class RAGWorkflow(BaseGenerativeWorkflow):
    """Retrieval-Augmented Generation over the session's documents.

    Runs the text to text task: the session model is a text to text LLM and
    each turn retrieves chunks of the session's documents before the LLM
    answers. The chunkers, retrievers, generation prompts and query
    transformations a RAG session can use are the ones related here, so a
    workflow over other content (images, say) relates its own.
    """

    COMPATIBLE_COMPONENTS: List[str] = [
        "TextToTextGenerationTask",
        "CharacterChunkModel",
        "RecursiveCharacterChunkModel",
        "TokenChunkModel",
        "BM25Retriever",
        "TFIDFRetriever",
        "DenseEmbeddingRetriever",
        "SentenceTransformerCrossEncoderRetriever",
        "MMRRerankerRetriever",
        "SequentialRetriever",
        "ParallelRetriever",
        "LLMEvaluatedDepthRetriever",
        "LLMEvaluatedEnsembleRetriever",
        "LLMFilterRetriever",
        "DefaultRAGGenerationPrompt",
        "CustomRAGGenerationPrompt",
        "DefaultQARAGGenerationPrompt",
        "LLMQueryRewriter",
        "LLMQueryExpander",
        "LLMQueryDecomposer",
    ]

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

    def process_output(
        self,
        output: "RAGGenerationOutput",
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

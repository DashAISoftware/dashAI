import json
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from DashAI.back.core.schema_fields import (
    BaseSchema,
    component_field,
    int_field,
    list_field,
    none_type,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.RAG_constants import (
    RAG_OUTPUT_CHUNKS_TYPE,
    RAG_OUTPUT_MESSAGE_TYPE,
    RAG_OUTPUT_QUERIES_TYPE,
    RAG_OUTPUT_TIMINGS_TYPE,
    RAG_OUTPUT_TRACE_TYPE,
    RAG_PARAM_GENERATION_MODEL,
)
from DashAI.back.workflows.base_generative_workflow import BaseGenerativeWorkflow

if TYPE_CHECKING:
    from DashAI.back.models.RAG.RAG_pipeline import RAGGenerationOutput


class RAGWorkflowSchema(BaseSchema):
    """Schema of the parameters of a RAG session.

    Defines the six configurable fields: documents, prompt,
    chunking_model, retriever_model, generation_model, and the optional
    query_transformation stage. Each model field accepts a
    ``{"component": str, "params": dict}`` structure resolved by the
    ComponentRegistry.
    """

    documents: schema_field(
        list_field(int_field(gt=0)),
        placeholder=None,
        description=MultilingualString(
            en="List of document IDs to use in the RAG pipeline.",
            es="Lista de IDs de documentos a usar en el pipeline RAG.",
            pt="Lista de IDs de documentos a usar no pipeline RAG.",
            de="Liste der Dokument-IDs, die im RAG-Pipeline verwendet werden sollen.",
            zh="要在 RAG 流水线中使用的文档 ID 列表。",
        ),
    )  # type: ignore

    prompt: schema_field(
        component_field(parent="BasePrompt"),
        placeholder={"component": "DefaultRAGGenerationPrompt", "params": {}},
        description=MultilingualString(
            en="Prompt template used in the RAG pipeline.",
            es="Plantilla de prompt usada en el pipeline RAG.",
            pt="Modelo de prompt usado no pipeline RAG.",
            de="Prompt-Vorlage, die im RAG-Pipeline verwendet wird.",
            zh="用于 RAG 流水线的提示词模板。",
        ),
    )  # type: ignore

    chunking_model: schema_field(
        component_field(parent="BaseChunkingModel"),
        description=MultilingualString(
            en="Chunking model used to split documents into smaller pieces.",
            es="Modelo de fragmentación para dividir documentos en piezas.",
            pt=(
                "Modelo de fragmentação usado para dividir documentos em"
                " fragmentos menores."
            ),
            de="Chunking-Modell zum Aufteilen von Dokumenten in kleinere Stücke.",
            zh="用于将文档拆分为更小块的切分模型。",
        ),
        placeholder={"component": "CharacterChunkModel", "params": {}},
    )  # type: ignore

    retriever_model: schema_field(
        component_field(parent="BaseRetriever"),
        placeholder={"component": "BM25Retriever", "params": {}},
        description=MultilingualString(
            en="Retriever component used in the RAG pipeline.",
            es="Componente recuperador usado en el pipeline RAG.",
            pt="Componente recuperador usado no pipeline RAG.",
            de="Retriever-Komponente, die im RAG-Pipeline verwendet wird.",
            zh="用于 RAG 流水线的检索器组件。",
        ),
    )  # type: ignore

    generation_model: schema_field(
        component_field(parent="TextToTextGenerationTaskModel"),
        placeholder={"component": "", "params": {}},
        description=MultilingualString(
            en="Text generation model used in the RAG pipeline.",
            es="Modelo de generación de texto usado en el pipeline RAG.",
            pt="Modelo de geração de texto usado no pipeline RAG.",
            de="Textgenerierungsmodell, das im RAG-Pipeline verwendet wird.",
            zh="用于 RAG 流水线的文本生成模型。",
        ),
    )  # type: ignore

    query_transformation: schema_field(
        none_type(component_field(parent="BaseQueryTransformation")),
        placeholder=None,
        description=MultilingualString(
            en="Optional query transformation stage that turns the user message"
            " into one or more search queries before retrieval.",
            es="Etapa opcional de transformación de consulta que convierte el"
            " mensaje del usuario en una o varias consultas de búsqueda antes"
            " de la recuperación.",
            pt="Etapa opcional de transformação de consulta que converte a"
            " mensagem do usuário em uma ou mais consultas de busca antes da"
            " recuperação.",
            de="Optionale Abfrage-Transformationsstufe, die die Benutzernachricht"
            " vor dem Abruf in eine oder mehrere Suchanfragen umwandelt.",
            zh="可选的查询转换阶段，在检索前将用户消息转换为一个或多个搜索查询。",
        ),
    ) = None  # type: ignore


class RAGWorkflow(BaseGenerativeWorkflow):
    """Retrieval-Augmented Generation over the session's documents.

    Built on the text to text task: the session model is the generation LLM
    named by ``generation_model``, the RAG schema validates the session
    parameters and ``RAGJob`` runs each turn, retrieving chunks before the
    LLM answers.
    """

    TASK = "TextToTextGenerationTask"
    MODEL_PARAMETER = RAG_PARAM_GENERATION_MODEL
    SCHEMA = RAGWorkflowSchema
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

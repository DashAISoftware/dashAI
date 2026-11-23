"""LLM-backed query decomposition (1-to-n, count decided by the model)."""

from __future__ import annotations

import logging
from typing import Any, ClassVar, Dict, List

from DashAI.back.core.schema_fields import (
    component_field,
    int_field,
    none_type,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.prompts.transformation.transformation_prompt import (
    QueryDecompositionPrompt,
)
from DashAI.back.models.RAG.RAG_constants import (
    MAX_SUBQUERIES_KEY,
    RAG_PROGRESS_JUSTIFICATION_KEY,
    RAG_PROGRESS_MESSAGE_KEY,
)
from DashAI.back.models.RAG.transformation.llm_query_transformation import (
    LLMQueryTransformation,
    MultiQueryTransformationSchema,
)

logger = logging.getLogger(__name__)

#: Upper bound on the sub-queries that the schema placeholder and the pydantic
#: default suggest for a new session. A stored configuration without the key
#: is not capped: the transformer treats an absent cap as no limit.
DEFAULT_MAX_SUBQUERIES = 3


class LLMQueryDecomposerSchema(MultiQueryTransformationSchema):
    """Schema for :class:`LLMQueryDecomposer`.

    Attributes:
        prompt: The transformation prompt, defaulting to the decomposition
            prompt.
        max_subqueries: Optional upper bound on the number of sub-queries.
            A new session suggests :data:`DEFAULT_MAX_SUBQUERIES`; ``None``
            removes the cap.
    """

    prompt: schema_field(
        component_field(parent="QueryTransformationPrompt"),
        placeholder={"component": "DefaultQueryDecompositionPrompt", "params": {}},
        description=MultilingualString(
            en="The prompt used to instruct the transformation model.",
            es="El prompt usado para instruir al modelo de transformación.",
            pt="O prompt usado para instruir o modelo de transformação.",
            de="Der Prompt, der das Transformationsmodell anweist.",
            zh="用于指示转换模型的提示词。",
        ),
    )
    max_subqueries: schema_field(
        none_type(int_field(ge=1)),
        DEFAULT_MAX_SUBQUERIES,
        description=MultilingualString(
            en="Optional upper bound on the number of sub-queries. Defaults to"
            " three; set it to null for no limit.",
            es="Límite superior opcional del número de subconsultas. Por defecto"
            " son tres; establécelo en null para no poner límite.",
            pt="Limite superior opcional do número de subconsultas. Por padrão"
            " são três; defina-o como null para não limitar.",
            de="Optionale Obergrenze für die Anzahl der Teilfragen. Standardmäßig"
            " drei; auf null setzen für kein Limit.",
            zh="子查询数量的可选上限。默认为三个；设为 null 表示不限制。",
        ),
        alias=MultilingualString(
            en="Max sub-queries",
            es="Subconsultas máximas",
            pt="Subconsultas máximas",
            de="Maximale Teilfragen",
            zh="最大子查询数",
        ),
    ) = DEFAULT_MAX_SUBQUERIES


class LLMQueryDecomposer(LLMQueryTransformation):
    """Decomposes a complex question into independently retrievable sub-queries.

    The model decides how many sub-queries are needed. ``max_subqueries`` caps
    the result, defaulting to :data:`DEFAULT_MAX_SUBQUERIES`; set it to ``None``
    to keep every sub-query the model produced.
    """

    SCHEMA = LLMQueryDecomposerSchema
    DISPLAY_NAME: str = MultilingualString(
        en="LLM Query Decomposer",
        es="Descomponedor de Consulta con LLM",
        pt="Decompositor de Consulta com LLM",
        de="LLM-Abfrage-Zerleger",
        zh="LLM 查询分解器",
    )
    DESCRIPTION: str = MultilingualString(
        en="Decomposes a complex question into independently retrievable sub-queries.",
        es="Descompone una pregunta compleja en subconsultas recuperables de"
        " forma independiente.",
        pt="Decompõe uma pergunta complexa em subconsultas recuperáveis de"
        " forma independente.",
        de="Zerlegt eine komplexe Frage in unabhängig abrufbare Teilfragen.",
        zh="将复杂问题分解为可独立检索的子查询。",
    )

    EXPECTED_FUNCTION = "decompose_query"
    ARGUMENT_KEY = "queries"
    TRANSFORMATION_PROMPT_BASE: ClassVar[type] = QueryDecompositionPrompt
    TOLERATE_BARE_LISTS: bool = True

    FUNCTION_DESCRIPTION: str = (
        "Decomposes a complex question into independently retrievable sub-queries."
    )
    FUNCTION_PARAMETERS: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "queries": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The list of independently retrievable sub-queries.",
                "minItems": 1,
            },
            RAG_PROGRESS_MESSAGE_KEY: {
                "type": "string",
                "description": (
                    "Optional one short user-facing sentence in the prompt "
                    "language describing what you did."
                ),
            },
            RAG_PROGRESS_JUSTIFICATION_KEY: {
                "type": "string",
                "description": (
                    "Optional one short sentence in the prompt language "
                    "explaining why you did it."
                ),
            },
        },
        "required": ["queries"],
    }

    metadata = {
        "technique": "decomposition",
        "prompt_parent": "QueryDecompositionPrompt",
    }

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the decomposition transformer.

        Parameters
        ----------
        max_subqueries : int | None, optional
            Optional upper bound on the number of sub-queries. When it is
            omitted or ``None`` the result is unrestricted.

        Other Parameters
        ----------------
        prompt, llm_model, history_window
            Forwarded to :class:`LLMQueryTransformation`.
        """
        self.max_subqueries = kwargs.pop(MAX_SUBQUERIES_KEY, None)
        super().__init__(**kwargs)

    def _render_prompt(self, message: str, history_block: str) -> str:
        """Render the decomposition prompt with the message, history and cap."""
        return self.prompt.format(
            input=message,
            history=history_block,
            n_max=self.max_subqueries,
        )

    def _parse_arguments(self, arguments: Dict[str, Any]) -> List[str]:
        """Parse the list of sub-queries from the model arguments.

        Parameters
        ----------
        arguments : Dict[str, Any]
            The arguments mapping emitted by the model.

        Returns
        -------
        List[str]
            The raw sub-query entries as strings.

        Raises
        ------
        RAGTransformationOutputError
            If the model arguments do not contain a non-empty ``queries`` list.
        """
        return [str(entry) for entry in self._require_list(arguments)]

    def _finalize_queries(self, queries: List[str]) -> List[str]:
        """Truncate to ``max_subqueries`` when the cap is set.

        Parameters
        ----------
        queries : List[str]
            Cleaned, deduplicated sub-queries.

        Returns
        -------
        List[str]
            The final sub-queries.
        """
        if self.max_subqueries is not None and len(queries) > self.max_subqueries:
            logger.info(
                "Query decomposition produced %d sub-queries; truncating to "
                "max_subqueries=%d.",
                len(queries),
                self.max_subqueries,
            )
            return queries[: self.max_subqueries]
        return queries

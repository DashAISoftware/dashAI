"""LLM-evaluated ensemble retriever.

Takes two or more child retrievers. The language model is shown a catalog of the
children (index, class name and configured ``top_k``), chooses which children to
consult each round, and supplies an explicit per-child ``top_k`` for every call.
Sufficiency is judged over the accumulated pool.

The schema placeholders come from :mod:`DashAI.back.models.RAG.RAG_defaults`:
``children`` seeds the default semantic and keyword retrievers and
``llm_model`` seeds the default RAG function-calling LLM. Both are ordinary,
fully modifiable values.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Tuple

from DashAI.back.core.schema_fields import (
    component_field,
    int_field,
    list_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.exceptions.retriever import (
    RAGRetrieverEvaluationError,
)
from DashAI.back.models.RAG.RAG_constants import (
    RAG_PROGRESS_JUSTIFICATION_KEY,
    RAG_PROGRESS_MESSAGE_KEY,
)
from DashAI.back.models.RAG.RAG_defaults import (
    DEFAULT_FUNCTION_CALL_MAX_TRIALS,
    DEFAULT_MAX_CHUNKS,
    DEFAULT_MAX_ITERS,
    MAX_FUNCTION_CALL_TRIALS,
    default_function_calling_llm,
    default_keyword_retriever,
    default_retrieval_sufficiency_prompt,
    default_semantic_retriever,
)
from DashAI.back.models.RAG.retrievers.composite.llm_evaluated_retriever import (
    LLMEvaluatedRetriever,
)
from DashAI.back.models.RAG.retrievers.composite.llm_retriever_support import (
    LLM_RETRIEVER_CATEGORY,
)
from DashAI.back.models.RAG.retrievers.composite.retrieval_context import (
    RetrievalContext,
)
from DashAI.back.models.RAG.retrievers.composite.retrieval_pool import RetrievalPool
from DashAI.back.models.RAG.retrievers.retrieval_contracts import (
    CALL_RETRIEVERS_KEY,
    DISCARD_KEY,
    DROPPED_OPERATIONS_KEY,
    REQUEST_CHUNKS_KEY,
    SUFFICIENT_KEY,
)
from DashAI.back.models.RAG.retrievers.retrieval_expansion import (
    RetrievalExpansionSchema,
)

#: Prefix of the planning verdict's narrative keys in the trace round entry.
_PLANNING_NARRATIVE_PREFIX = "planning_"


class LLMEvaluatedEnsembleRetrieverSchema(RetrievalExpansionSchema):
    """Schema for :class:`LLMEvaluatedEnsembleRetriever`.

    Attributes:
        children: At least two child retrievers, from which the LLM chooses.
            Defaults to the default semantic and keyword retrievers; the value
            is fully modifiable.
        max_chunks: Maximum number of chunks the pool may hold.
        max_iters: Maximum number of retrieval rounds.
        prompt: The retrieval-sufficiency prompt component.
        llm_model: The text-to-text model that chooses children and judges.
            Defaults to the default RAG function-calling LLM; the value is
            fully modifiable.
        function_call_max_trials: Maximum number of evaluation attempts, the
            first call included. Both routes are retried on an unusable verdict.
    """

    children: schema_field(
        list_field(component_field(parent="BaseRetriever"), min_items=2),
        placeholder=[default_semantic_retriever(), default_keyword_retriever()],
        description=MultilingualString(
            en="Child retrievers the LLM may consult. A catalog of their"
            " indices, names and top_k values is rendered into the prompt."
            " Defaults to the default semantic and keyword retrievers; you can"
            " change them.",
            es="Recuperadores hijos que el LLM puede consultar. Se renderiza un"
            " catálogo de sus índices, nombres y valores top_k en el prompt."
            " Por defecto usa los recuperadores semántico y de palabras clave"
            " predeterminados; puedes cambiarlos.",
            pt="Recuperadores filhos que o LLM pode consultar. Um catálogo de"
            " seus índices, nomes e valores top_k é renderizado no prompt."
            " Por padrão usa os recuperadores semântico e de palavras-chave"
            " padrão; você pode alterá-los.",
            de="Kind-Retriever, die das LLM konsultieren darf. Ein Katalog ihrer"
            " Indizes, Namen und top_k-Werte wird in den Prompt gerendert."
            " Standardmäßig werden der semantische Standard-Retriever und der"
            " Standard-Stichwort-Retriever verwendet; sie sind änderbar.",
            zh=(
                "LLM 可咨询的子检索器。其索引、名称和 top_k 值的目录会渲染到提示词中。"
                "默认为默认语义检索器和关键词检索器，可随时修改。"
            ),
        ),
    )  # type: ignore

    max_chunks: schema_field(
        int_field(gt=0),
        placeholder=DEFAULT_MAX_CHUNKS,
        description=MultilingualString(
            en="Maximum number of chunks the accumulated pool may hold.",
            es="Número máximo de fragmentos que puede contener el conjunto acumulado.",
            pt="Número máximo de trechos que o conjunto acumulado pode conter.",
            de="Maximale Anzahl von Fragmenten im gesammelten Pool.",
            zh="累积池可容纳的最大片段数量。",
        ),
    )  # type: ignore

    max_iters: schema_field(
        int_field(gt=0),
        placeholder=DEFAULT_MAX_ITERS,
        description=MultilingualString(
            en="Maximum number of retrieval rounds. One planning call plus at"
            " most this many minus one judgement calls.",
            es="Número máximo de rondas de recuperación. Una llamada de"
            " planificación más como máximo este número menos una llamadas de"
            " evaluación.",
            pt="Número máximo de rodadas de recuperação. Uma chamada de"
            " planejamento mais no máximo esse número menos uma chamadas de"
            " avaliação.",
            de="Maximale Anzahl von Abrufrunden. Ein Planungsaufruf plus"
            " höchstens diese Zahl minus eins Bewertungsaufrufe.",
            zh="最大检索轮数。一次规划调用加上最多该数量减一次评估调用。",
        ),
    )  # type: ignore

    function_call_max_trials: schema_field(
        int_field(ge=1, le=MAX_FUNCTION_CALL_TRIALS, strict=True),
        placeholder=DEFAULT_FUNCTION_CALL_MAX_TRIALS,
        description=MultilingualString(
            en="Maximum number of function-calling evaluation attempts,"
            " including the first. When the verdict is unusable or has no valid"
            " operation left, the evaluation is retried until this limit is"
            " reached.",
            es="Número máximo de intentos de evaluación mediante llamada a"
            " funciones, incluido el primero. Cuando el veredicto es inutilizable"
            " o no queda ninguna operación válida, la evaluación se reintenta"
            " hasta alcanzar este límite.",
            pt="Número máximo de tentativas de avaliação por chamada de função,"
            " incluindo a primeira. Quando o veredicto é inutilizável ou não resta"
            " nenhuma operação válida, a avaliação é repetida até atingir esse"
            " limite.",
            de="Maximale Anzahl von Bewertungsversuchen über Funktionsaufrufe,"
            " einschließlich des ersten. Wenn das Urteil unbrauchbar ist oder keine"
            " gültige Operation übrig bleibt, wird die Bewertung bis zu diesem"
            " Limit wiederholt.",
            zh="通过函数调用进行评估的最大尝试次数，包括首次尝试。当判定不可用或没有剩余"
            "有效操作时，会重试评估直到达到此限制。",
        ),
        alias=MultilingualString(
            en="Function call max trials",
            es="Máximo de intentos de llamada a funciones",
            pt="Máximo de tentativas de chamada de função",
            de="Max. Funktionsaufrufversuche",
            zh="函数调用最大尝试次数",
        ),
    ) = DEFAULT_FUNCTION_CALL_MAX_TRIALS  # type: ignore

    prompt: schema_field(
        component_field(parent="RetrievalSufficiencyPrompt"),
        placeholder=default_retrieval_sufficiency_prompt(),
        description=MultilingualString(
            en="The prompt used to choose children and judge sufficiency.",
            es="El prompt usado para elegir hijos y juzgar la suficiencia.",
            pt="O prompt usado para escolher filhos e julgar a suficiência.",
            de="Der Prompt zur Auswahl der Kinder und Beurteilung der Suffizienz.",
            zh="用于选择子检索器并判断充分性的提示词。",
        ),
    )  # type: ignore

    llm_model: schema_field(
        component_field(parent="TextToTextGenerationTaskModel"),
        placeholder=default_function_calling_llm(),
        description=MultilingualString(
            en="The language model that chooses children and judges"
            " sufficiency. Defaults to the default RAG function-calling LLM;"
            " you can change it.",
            es="El modelo de lenguaje que elige hijos y juzga la suficiencia."
            " Por defecto usa el LLM de llamada a funciones RAG predeterminado;"
            " puedes cambiarlo.",
            pt="O modelo de linguagem que escolhe filhos e julga a suficiência."
            " Por padrão usa o LLM de chamada de funções RAG padrão; você pode"
            " alterá-lo.",
            de="Das Sprachmodell, das Kinder auswählt und die Suffizienz"
            " beurteilt. Standardmäßig wird das RAG-Standard-LLM für"
            " Funktionsaufrufe verwendet; es ist änderbar.",
            zh=(
                "选择子检索器并判断充分性的语言模型。默认为默认 RAG 函数调用 LLM，"
                "可随时修改。"
            ),
        ),
    )  # type: ignore


class LLMEvaluatedEnsembleRetriever(LLMEvaluatedRetriever):
    """Consults LLM-chosen children across rounds to build a sufficient pool.

    A planning evaluation over an empty pool selects the first round's children.
    Each round consults the chosen children at the explicit per-child ``top_k``
    supplied by the model, merges the results and — except for the final round —
    judges the pool. An insufficient verdict selects the next round's children.
    """

    SCHEMA = LLMEvaluatedEnsembleRetrieverSchema
    CATEGORY: MultilingualString = LLM_RETRIEVER_CATEGORY
    DISPLAY_NAME: str = MultilingualString(
        en="LLM-Evaluated Ensemble Retriever",
        es="Recuperador Conjunto Evaluado por LLM",
        pt="Retriever em Conjunto Avaliado por LLM",
        de="LLM-bewerteter Ensemble-Retriever",
        zh="LLM 评估集成检索器",
    )
    DESCRIPTION: str = MultilingualString(
        en="Consults two or more child retrievers chosen by an LLM, using the"
        " explicit per-child top_k supplied for each call until the pool"
        " suffices.",
        es="Consulta dos o más recuperadores hijos elegidos por un LLM, usando"
        " el top_k explícito por hijo indicado en cada llamada hasta que el"
        " conjunto sea suficiente.",
        pt="Consulta dois ou mais recuperadores filhos escolhidos por um LLM,"
        " usando o top_k explícito por filho indicado em cada chamada até que o"
        " conjunto seja suficiente.",
        de="Konsultiert zwei oder mehr vom LLM gewählte Kind-Retriever mit dem"
        " für jeden Aufruf angegebenen top_k pro Kind, bis der Pool ausreicht.",
        zh=(
            "咨询由 LLM 选择的两个或更多子检索器，并使用每次调用指定的"
            "每个子检索器的 top_k，直到池足够。"
        ),
    )

    EXPECTED_FUNCTION: ClassVar[str] = "evaluate_retrieval_sufficiency"
    FUNCTION_DESCRIPTION: ClassVar[str] = (
        "Decide whether the retrieved chunks are sufficient to answer the user "
        "message. Calling retrievers is not mandatory every round: when the "
        "pool suffices, set sufficient to true and omit all actions; when it "
        "does not, request chunks, call retrievers, or both. "
        "request_specific_chunks adds specific chunks to the pool even if no "
        "retriever returned them, discard_specific_chunks removes them, the two "
        "are mutually exclusive for the same chunk, and every chunk not "
        "mentioned is preserved. call_retrievers maps 1-based retriever indices "
        "(1 to the number of retrievers) to the number of chunks to retrieve "
        "next. Respect the maximum pool size and the remaining free slots. The "
        "per-retriever top_k is a size hint; the retriever enforces the hard pool "
        "cap. Every retriever index and chunk position must be valid, never "
        "request and discard the same chunk, leave free capacity when calling "
        "retrievers, and do not leave the pool empty without a retriever call or "
        "chunk request. Chunks not mentioned stay in the pool exactly as they "
        "are, except when the maximum capacity forces out older non-requested "
        "chunks; requested chunks take priority. Invalid decisions are rejected "
        "and must be retried."
    )
    FUNCTION_PARAMETERS: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            SUFFICIENT_KEY: {
                "type": "boolean",
                "description": (
                    "Whether the retrieved chunks suffice to answer the user "
                    "message. When true, omit all actions."
                ),
            },
            CALL_RETRIEVERS_KEY: {
                "type": "object",
                "additionalProperties": {"type": "integer", "minimum": 1},
                "description": (
                    "Optional when insufficient: maps 1-based retriever indices "
                    "(1 to the number of retrievers) to the number of chunks to "
                    "retrieve from them next. Not required every round."
                ),
            },
            REQUEST_CHUNKS_KEY: {
                "type": "object",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 0},
                },
                "description": (
                    "Maps document ids to chunk positions to add to the pool "
                    "even if no retriever returned them. Mutually exclusive with "
                    f"'{DISCARD_KEY}' for the same chunk."
                ),
            },
            DISCARD_KEY: {
                "type": "object",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 0},
                },
                "description": (
                    "Maps document ids to chunk positions to remove from the "
                    "pool even if a retriever returned them. Mutually exclusive "
                    f"with '{REQUEST_CHUNKS_KEY}' for the same chunk."
                ),
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
        "required": [SUFFICIENT_KEY],
    }

    def retrieve(self, query: str, **kwargs: Any) -> Tuple[List[Chunk], Dict[str, Any]]:
        """Retrieve by consulting LLM-chosen children across rounds.

        Parameters
        ----------
        query : str
            The search query string.
        **kwargs
            Unused; children choices and sizes come from the LLM verdicts.

        Returns
        -------
        Tuple[List[Chunk], Dict[str, Any]]
            The final pool (at most ``max_chunks`` chunks) and this retriever's
            trace node, whose ``children`` holds every consulted child node and
            whose ``rounds`` holds one summary per retrieval round.

        Raises
        ------
        RAGRetrieverEvaluationError
            If a verdict stays unusable after retries, or planning keeps
            returning no valid retriever call. Any invalid retriever index, chunk
            reference, contradictory action, capacity violation or
            empty-refill-less decision rejects the whole verdict and is retried.
        """
        context = RetrievalContext.from_retriever(self)
        pool = RetrievalPool(self.max_chunks, context)
        child_nodes: List[Dict[str, Any]] = []
        rounds: List[Dict[str, Any]] = []

        planning, prepared = self._evaluate_with_pool(
            query,
            pool,
            context,
            round_number=1,
            max_rounds=self.max_iters,
            require_retriever_call=True,
        )
        if prepared is None:
            raise RAGRetrieverEvaluationError(
                "The planning evaluation did not produce an applied pool."
            )
        pool = prepared
        planning_drops = list(planning.dropped_operations)
        # The evaluator already guarantees a valid planning retriever call.
        calls = planning.call_retrievers
        self._report_verdict_progress(planning)

        for round_index in range(self.max_iters):
            call_entries: List[Dict[str, Any]] = []
            remaining = self.max_chunks - pool.size()
            if calls and remaining > 0:
                call_entries, nodes = self._consult(query, calls, pool, remaining)
                child_nodes.extend(nodes)
            entry = self._build_entry(round_index, call_entries)
            if round_index == 0:
                self._record_round_narrative(
                    entry, planning, key_prefix=_PLANNING_NARRATIVE_PREFIX
                )
                entry[f"{_PLANNING_NARRATIVE_PREFIX}{DROPPED_OPERATIONS_KEY}"] = (
                    planning_drops
                )
            rounds.append(entry)

            if round_index == self.max_iters - 1:
                break

            verdict, prepared = self._evaluate_with_pool(
                query,
                pool,
                context,
                round_number=round_index + 2,
                max_rounds=self.max_iters,
            )
            calls = verdict.call_retrievers
            self._record_verdict(entry, verdict)
            if verdict.sufficient:
                self._emit_verdict(entry, verdict)
                break
            if prepared is None:
                raise RAGRetrieverEvaluationError(
                    "An insufficient verdict did not produce an applied pool."
                )
            pool = prepared
            self._emit_verdict(entry, verdict)

        pool_chunks = self._apply_retrieval_expansion(pool.materialize())
        return pool_chunks, self._build_trace(pool_chunks, child_nodes, rounds)

    def _build_entry(
        self,
        round_index: int,
        call_entries: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build the trace entry for one ensemble round.

        Parameters
        ----------
        round_index : int
            Zero-based round index.
        call_entries : List[Dict[str, Any]]
            Per-child consultation summaries for this round.

        Returns
        -------
        Dict[str, Any]
            A JSON-serializable round summary with the action maps initialized.
        """
        return {
            "round": round_index + 1,
            "calls": call_entries,
            "verdict": None,
            CALL_RETRIEVERS_KEY: {},
            REQUEST_CHUNKS_KEY: {},
            DISCARD_KEY: {},
        }

    def _consult(
        self,
        query: str,
        calls: Dict[int, int],
        pool: RetrievalPool,
        remaining: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Consult the requested children and merge their chunks into the pool.

        Parameters
        ----------
        query : str
            The search query string.
        calls : Dict[int, int]
            Validated 1-based retriever index to requested top-k mapping.
        pool : RetrievalPool
            The pool the retrieved chunks are merged into.
        remaining : int
            Free slots before the pool reaches ``max_chunks``. Each child's
            request is capped by it and the budget is reduced by the number of
            chunks the pool actually gained (duplicates add nothing).

        Returns
        -------
        Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]
            The per-child call summaries and the child trace nodes.
        """
        call_entries: List[Dict[str, Any]] = []
        nodes: List[Dict[str, Any]] = []
        budget = remaining
        discarded = pool.discarded_count()
        for index, requested_top_k in calls.items():
            if budget <= 0:
                break
            child = self._children[index - 1]
            request_limit = self.max_chunks + discarded
            requested = min(requested_top_k, request_limit)
            before = pool.size()
            chunks, node = self._delegate(child, query, requested)
            pool.add(chunks)
            added = pool.size() - before
            nodes.append(node)
            budget = max(budget - added, 0)
            call_entries.append(
                {
                    "name": type(child).__name__,
                    "requested_top_k": requested,
                    "returned": len(chunks),
                }
            )
        return call_entries, nodes

    def score_chunks(self, chunk_ids: List[int], query: str) -> List[Tuple[int, float]]:
        """Aggregate chunk scores across all children by averaging.

        Each child scores the chunks independently; all scores for the same
        chunk are averaged. Results are sorted by distance (ascending). Chunks
        no child scored are omitted.

        Parameters
        ----------
        chunk_ids : List[int]
            List of chunk IDs to score.
        query : str
            The search query string.

        Returns
        -------
        List[Tuple[int, float]]
            A list of ``(chunk_id, average_distance)`` tuples sorted by distance.
        """
        if not chunk_ids or not self._children:
            return []

        accumulator: Dict[int, List[float]] = {cid: [] for cid in chunk_ids}
        for child in self._children:
            for cid, distance in child.score_chunks(chunk_ids, query):
                accumulator[cid].append(distance)

        merged: List[Tuple[int, float]] = []
        for cid, distances in accumulator.items():
            if not distances:
                continue
            merged.append((cid, sum(distances) / len(distances)))
        merged.sort(key=lambda pair: pair[1])
        return merged

from typing import List

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from DashAI.back.core.schema_fields import (
    BaseSchema,
    component_field,
    float_field,
    int_field,
    list_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.retrievers.composite.composite_retriever import (
    CompositeRetriever,
)


class MMRRerankerRetrieverSchema(BaseSchema):
    mmr_lambda: schema_field(
        float_field(ge=0.0, le=1.0),
        placeholder=0.5,
        description=MultilingualString(
            en="Trade-off between relevance (1.0) and diversity (0.0).",
            es="Compromiso entre relevancia (1.0) y diversidad (0.0).",
        ),
    )  # type: ignore

    retrieval_factor: schema_field(
        int_field(gt=1),
        placeholder=3,
        description=MultilingualString(
            en="Multiplier for initial retrieval size.",
            es="Multiplicador para el tamaño de recuperación inicial.",
        ),
    )  # type: ignore

    top_k: schema_field(
        int_field(gt=0),
        placeholder=5,
        description=MultilingualString(
            en="Final number of chunks to select.",
            es="Número final de fragmentos a seleccionar.",
        ),
    )  # type: ignore

    children: schema_field(
        list_field(component_field(parent="RetrieverModel"), min_items=1, max_items=1),
        placeholder=[],
        description=MultilingualString(
            en="The child retriever whose results will be re-ranked.",
            es="El recuperador hijo cuyos resultados serán reordenados.",
        ),
    )  # type: ignore


class MMRRerankerRetriever(CompositeRetriever):
    FLAGS: list[str] = ["FAMILY:mmr", "composite", "reranker"]
    SCHEMA = MMRRerankerRetrieverSchema
    DISPLAY_NAME: str = MultilingualString(
        en="MMR Reranker",
        es="Reordenador MMR",
    )
    DESCRIPTION: str = MultilingualString(
        en="Re-ranks retrieval results using Maximum Marginal Relevance for diversity.",
        es="Reordena resultados de recuperación usando Maximum Marginal Relevance "
        "para diversidad.",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mmr_lambda = self.params.pop("mmr_lambda")
        self.retrieval_factor = self.params.pop("retrieval_factor")
        self._top_k = self.params.pop("top_k")

    @property
    def retrieval_top_k(self) -> int:
        return self._top_k

    def retrieve(self, query, **kwargs) -> List[Chunk]:
        child = self._children[0]
        expanded_k = self._top_k * self.retrieval_factor
        candidates = child.retrieve(query, top_k=expanded_k)
        if len(candidates) <= self._top_k:
            return candidates

        chunk_ids = [c.id for c in candidates]
        scored = child.score_chunks(chunk_ids, query)
        id_to_dist = dict(scored)

        ordered = [c for c in candidates if c.id in id_to_dist]
        if len(ordered) <= self._top_k:
            return ordered[: self._top_k]

        relevance = np.array([1.0 - id_to_dist[c.id] for c in ordered])
        ordered_ids = [c.id for c in ordered]
        try:
            vectors = child.get_chunk_vectors(ordered_ids)
        except ValueError:
            return ordered[: self._top_k]

        pairwise = cosine_similarity(vectors)
        selected = self._mmr_select(relevance, pairwise)
        return [ordered[i] for i in selected]

    def _mmr_select(
        self,
        relevance: np.ndarray,
        pairwise: np.ndarray,
    ) -> List[int]:
        n = len(relevance)
        best = int(np.argmax(relevance))
        selected = [best]
        remaining = [i for i in range(n) if i != best]

        while len(selected) < self._top_k and remaining:
            scores = np.empty(len(remaining))
            for j, cand in enumerate(remaining):
                max_pair = max(pairwise[cand][s] for s in selected)
                scores[j] = (
                    self.mmr_lambda * relevance[cand]
                    - (1.0 - self.mmr_lambda) * max_pair
                )
            best_idx = int(np.argmax(scores))
            selected.append(remaining[best_idx])
            remaining.pop(best_idx)

        return selected

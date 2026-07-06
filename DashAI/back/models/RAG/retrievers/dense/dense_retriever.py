import os
from typing import Dict, List, Tuple

import numpy as np
from sklearn.metrics.pairwise import pairwise_distances

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.embeddings import DenseEmbedding
from DashAI.back.models.RAG.retrievers.unit_retriever import UnitRetriever

# NOTE: The entire chunk index (similarity_matrix) is loaded into memory,
# which is fine for typical use with tens to low hundreds of documents but
# may be a bottleneck for very large collections.


class DenseRetrieverSchema(BaseSchema):
    similarity_metric: schema_field(
        enum_field(enum=["cityblock", "cosine", "euclidean", "l1", "l2", "manhattan"]),
        placeholder="cosine",
        description=MultilingualString(
            en="Distance metric for comparing dense vectors.",
            es="Métrica de distancia para comparar vectores densos.",
        ),
    )  # type: ignore

    top_k: schema_field(
        int_field(gt=0),
        placeholder=5,
        description=MultilingualString(
            en="Number of chunks to select.",
            es="Número de fragmentos a seleccionar.",
        ),
    )  # type: ignore


class DenseRetriever(UnitRetriever):
    FLAGS: list[str] = ["abstract"]
    DISPLAY_NAME: str = MultilingualString(
        en="Embedding Retriever",
        es="Recuperador por Embeddings",
    )
    DESCRIPTION: str = MultilingualString(
        en="Embedding retriever using vector embeddings for similarity search.",
        es="Recuperador por embeddings que usa representaciones vectoriales para búsqueda por similitud.",
    )

    SCHEMA = DenseRetrieverSchema

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.similarity_metric = self.params.pop("similarity_metric")
        self._top_k = self.params.pop("top_k")

    def _init_embedding(self, embedding_model):
        if not isinstance(embedding_model, DenseEmbedding):
            raise TypeError(
                f"Expected DenseEmbedding instance, "
                f"got {type(embedding_model).__name__}"
            )
        self.embedding_model = embedding_model
        encoding_class_name = embedding_model.__class__.__name__
        encoding_params = dict(sorted(embedding_model.params.items()))

        self.params["encoding_model"] = {
            "class_name": encoding_class_name,
            "parameters": encoding_params,
        }

        self.compute_missing_embeddings()
        self.init_similarity_matrix()

    def compute_missing_embeddings(self):
        for doc_id, doc_chunks in self.chunks.items():
            matrix_dir = self._persistence.matrix_dirs.get(doc_id)
            if matrix_dir is None:
                continue
            matrix_path = os.path.join(matrix_dir, "embeddings.npy")
            if os.path.exists(matrix_path):
                continue
            chunk_texts = [chunk.text for chunk in doc_chunks.values()]
            embeddings = self.embedding_model.batch_encode(chunk_texts)
            os.makedirs(matrix_dir, exist_ok=True)
            np.save(matrix_path, embeddings)

    def init_similarity_matrix(self):
        self.similarity_matrix = None
        self.matrix_row_to_chunk_id = {}
        self.chunk_id_to_doc_id = {}

        all_embeddings = []
        row_index = 0
        for doc_id, chunks in self.chunks.items():
            matrix_dir = self._persistence.matrix_dirs.get(doc_id)
            if matrix_dir is None:
                continue
            matrix_path = os.path.join(matrix_dir, "embeddings.npy")
            if not os.path.exists(matrix_path):
                continue
            for chunk_id in chunks:
                self.matrix_row_to_chunk_id[row_index] = chunk_id
                self.chunk_id_to_doc_id[chunk_id] = doc_id
                row_index += 1
            all_embeddings.append(np.load(matrix_path))

        if all_embeddings:
            self.similarity_matrix = np.vstack(all_embeddings)

    @property
    def retrieval_top_k(self) -> int:
        return self._top_k

    def retrieve(self, query: str, top_k: int | None = None) -> List[Chunk]:
        self._check_infra()
        if self.similarity_matrix is None:
            raise ValueError("Similarity matrix not initialized.")
        k = top_k if top_k is not None else self._top_k
        query_embedding = self.embedding_model.encode(query)
        # NOTE: pairwise_distances computes O(n×dim) per query with no
        # FAISS/HNSW indexing. Low priority since current use cases have
        # small document sets.
        distances = pairwise_distances(
            query_embedding.reshape(1, -1),
            self.similarity_matrix,
            metric=self.similarity_metric,
        )[0]
        top_indices = np.argsort(distances)[:k]
        results = []
        for idx in top_indices:
            chunk_id = self.matrix_row_to_chunk_id[idx]
            doc_id = self.chunk_id_to_doc_id[chunk_id]
            results.append(self.chunks[doc_id][chunk_id])
        return results

    def score_chunks(self, chunk_ids: List[int], query: str) -> List[Tuple[int, float]]:
        self._check_infra()
        if self.similarity_matrix is None:
            raise ValueError("Similarity matrix not initialized.")
        query_embedding = self.embedding_model.encode(query)
        chunk_id_to_row = {
            self.matrix_row_to_chunk_id[r]: r for r in self.matrix_row_to_chunk_id
        }
        valid_ids = [cid for cid in chunk_ids if cid in chunk_id_to_row]
        if not valid_ids:
            return []
        rows = [chunk_id_to_row[cid] for cid in valid_ids]
        distances = pairwise_distances(
            query_embedding.reshape(1, -1),
            self.similarity_matrix[rows],
            metric=self.similarity_metric,
        )[0]
        scored = list(zip(valid_ids, distances.tolist()))
        scored.sort(key=lambda x: x[1])
        return scored

    def get_chunk_vectors(self, chunk_ids: List[int]) -> np.ndarray:
        if self.similarity_matrix is None:
            raise ValueError("Similarity matrix not initialized.")
        chunk_id_to_row: Dict[int, int] = {
            self.matrix_row_to_chunk_id[r]: r for r in self.matrix_row_to_chunk_id
        }
        rows = []
        for cid in chunk_ids:
            row = chunk_id_to_row.get(cid)
            if row is not None:
                rows.append(row)
        if not rows:
            raise ValueError(
                f"None of the provided chunk_ids {chunk_ids} were found "
                "in the similarity matrix."
            )
        return self.similarity_matrix[rows]

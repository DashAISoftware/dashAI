import os
from typing import List, Tuple

import numpy as np
from sklearn.metrics.pairwise import pairwise_distances

from DashAI.back.core.schema_fields import (
    BaseSchema,
    component_field,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.embeddings import DenseEmbedding
from DashAI.back.models.RAG.retrievers.persistence import DensePersistence
from DashAI.back.models.RAG.retrievers.unit_retriever import UnitRetriever

# NOTE: The entire chunk index (similarity_matrix) is loaded into memory,
# which is fine for typical use with tens to low hundreds of documents but
# may be a bottleneck for very large collections.


class DenseRetrieverSchema(BaseSchema):
    encoding_model: schema_field(
        component_field(parent="DenseEmbedding"),
        placeholder={"component": "FastTextEmbedding", "params": {}},
        description=MultilingualString(
            en="Model to convert text into dense vector representations.",
            es="Modelo para convertir texto en representaciones vectoriales densas.",
        ),
    )  # type: ignore

    similarity_metric: schema_field(
        enum_field(
            enum=[
                "cityblock",
                "cosine",
                "euclidean",
                "l1",
                "l2",
                "manhattan",
                "nan_euclidean",
                "braycurtis",
                "canberra",
                "chebyshev",
                "correlation",
                "dice",
                "hamming",
                "jaccard",
                "mahalanobis",
                "minkowski",
                "rogerstanimoto",
                "russellrao",
                "seuclidean",
                "sokalmichener",
                "sokalsneath",
                "sqeuclidean",
                "yule",
            ]
        ),
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
    DISPLAY_NAME: str = MultilingualString(
        en="Dense Retriever",
        es="Recuperador Denso",
    )
    DESCRIPTION: str = MultilingualString(
        en="Dense retriever using vector embeddings for similarity search.",
        es="Recuperador denso que usa embeddings vectoriales para búsqueda por similitud.",
    )

    SCHEMA = DenseRetrieverSchema

    def __init__(self, **kwargs):
        persistence_raw = kwargs["persistence"]
        if not isinstance(persistence_raw, DensePersistence):
            raise TypeError(
                f"Expected DensePersistence, got {type(persistence_raw).__name__}"
            )

        self.embedding_class_name = kwargs["encoding_model"]["properties"]["params"][
            "comp"
        ]["component"]
        self.embedding_params = kwargs["encoding_model"]["properties"]["params"][
            "comp"
        ]["params"]
        kwargs["encoding_model"] = kwargs["encoding_model"]["properties"]["params"][
            "comp"
        ]

        super().__init__(**kwargs)

        self.embedding_model = self.params.pop("encoding_model")
        if not isinstance(self.embedding_model, DenseEmbedding):
            raise TypeError(
                f"Expected DenseEmbedding instance, got {type(self.embedding_model).__name__}"
            )
        self.params["encoding_model"] = {
            "class_name": self.embedding_class_name,
            "parameters": self.embedding_params,
        }

        self.similarity_metric = self.params.pop("similarity_metric")
        self._top_k = self.params.pop("top_k")

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

import logging
import os
import pickle
from typing import Dict, List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import pairwise_distances

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    component_field,
    enum_field,
    float_field,
    int_field,
    list_field,
    none_type,
    schema_field,
    string_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.base_model import BaseModel
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.retrievers.persistence import SparsePersistence
from DashAI.back.models.RAG.retrievers.sparse.sparse_retriever import SparseRetriever

log = logging.getLogger(__name__)


class BM25VectorizerSchema(BaseSchema):
    strip_accents: schema_field(
        none_type(enum_field(enum=["ascii", "unicode"])),
        placeholder=None,
        description=MultilingualString(
            en="Remove accents during preprocessing.",
            es="Eliminar acentos durante el preprocesamiento.",
        ),
    )  # type: ignore

    lowercase: schema_field(
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en="Convert all characters to lowercase.",
            es="Convertir todos los caracteres a minúsculas.",
        ),
    )  # type: ignore

    stop_words: schema_field(
        none_type(list_field(string_field(), min_items=1)),
        placeholder=None,
        description=MultilingualString(
            en="List of stop words.",
            es="Lista de palabras vacías.",
        ),
    )  # type: ignore

    max_df: schema_field(
        float_field(ge=0.0, le=1.0),
        placeholder=1.0,
        description=MultilingualString(
            en="Ignore terms with document frequency above this threshold.",
            es="Ignorar términos con frecuencia de documento superior a este umbral.",
        ),
    )  # type: ignore

    min_df: schema_field(
        float_field(ge=0.0, le=1.0),
        placeholder=0.0,
        description=MultilingualString(
            en="Ignore terms with document frequency below this threshold.",
            es="Ignorar términos con frecuencia de documento inferior a este umbral.",
        ),
    )  # type: ignore

    max_features: schema_field(
        none_type(int_field(ge=1)),
        placeholder=None,
        description=MultilingualString(
            en="Maximum number of features.",
            es="Número máximo de características.",
        ),
    )  # type: ignore


class BM25RetrieverSchema(BaseSchema):
    BM25Vectorizer: schema_field(
        component_field(parent="BM25VectorizerModel"),
        placeholder={"component": "BM25VectorizerModel", "params": {}},
        description=MultilingualString(
            en="BM25 Vectorizer parameters.",
            es="Parámetros del vectorizador BM25.",
        ),
    )  # type: ignore

    k1: schema_field(
        float_field(ge=0.0),
        placeholder=1.5,
        description=MultilingualString(
            en="BM25 k1 parameter: term frequency saturation.",
            es="Parámetro k1 de BM25: saturación de frecuencia de término.",
        ),
    )  # type: ignore

    b: schema_field(
        float_field(ge=0.0, le=1.0),
        placeholder=0.75,
        description=MultilingualString(
            en="BM25 b parameter: length normalization.",
            es="Parámetro b de BM25: normalización de longitud.",
        ),
    )  # type: ignore

    delta: schema_field(
        float_field(ge=0.0),
        placeholder=0.0,
        description=MultilingualString(
            en="BM25 delta parameter for IDF smoothing.",
            es="Parámetro delta de BM25 para suavizado de IDF.",
        ),
    )  # type: ignore

    similarity_function: schema_field(
        enum_field(
            [
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
            en="Similarity function for comparing BM25-weighted vectors.",
            es="Función de similitud para comparar vectores ponderados BM25.",
        ),
    )  # type: ignore

    top_k: schema_field(
        int_field(ge=1),
        placeholder=5,
        description=MultilingualString(
            en="Number of chunks to select.",
            es="Número de fragmentos a seleccionar.",
        ),
    )  # type: ignore

    similarity_threshold: schema_field(
        none_type(float_field()),
        placeholder=None,
        description=MultilingualString(
            en="Distance threshold. None disables filtering.",
            es="Umbral de distancia. None deshabilita el filtrado.",
        ),
    )  # type: ignore


class BM25VectorizerModel(BaseModel):
    SCHEMA = BM25VectorizerSchema

    def __init__(self, **kwargs) -> None:
        self.vectorizer = TfidfVectorizer(
            **kwargs,
            norm=None,
            use_idf=False,
            smooth_idf=False,
            sublinear_tf=False,
        )

    def save(self, filename: str = "") -> None:
        pass

    def load(self, filename: str = "") -> None:
        pass

    def train(self, **kwargs):
        return


class BM25Retriever(SparseRetriever):
    DISPLAY_NAME: str = MultilingualString(
        en="BM25 Retriever",
        es="Recuperador BM25",
    )
    DESCRIPTION: str = MultilingualString(
        en="Sparse retriever using BM25 (Okapi) ranking for document retrieval.",
        es="Recuperador disperso que usa ranking BM25 (Okapi) para recuperar documentos.",
    )

    SCHEMA = BM25RetrieverSchema

    def __init__(self, **kwargs):
        persistence_raw = kwargs["persistence"]
        if not isinstance(persistence_raw, SparsePersistence):
            raise TypeError(
                f"Expected SparsePersistence, got {type(persistence_raw).__name__}"
            )
        kwargs["BM25Vectorizer"] = kwargs["BM25Vectorizer"]["properties"]["params"][
            "comp"
        ]
        super().__init__(**kwargs)

        self.k1 = self.params.pop("k1")
        self.b = self.params.pop("b")
        self.delta = self.params.pop("delta")
        self.similarity_function_name = self.params.pop("similarity_function")
        self._top_k = self.params.pop("top_k")
        self.similarity_threshold = self.params.pop("similarity_threshold")

        vectorizer_model = self.params.pop("BM25Vectorizer")
        if not isinstance(vectorizer_model, BM25VectorizerModel):
            raise TypeError(
                f"Expected BM25VectorizerModel, got {type(vectorizer_model).__name__}"
            )
        self._vectorizer = vectorizer_model.vectorizer

        loaded = self.load()
        if loaded:
            log.info(
                "BM25Retriever loaded from disk at %s.", self._persistence.model_dir
            )
        else:
            log.info("Fitting new BM25 model...")
            self._fit()

    def load(self) -> bool:
        if self._persistence.model_dir is None:
            return False
        model_dir = self._persistence.model_dir
        try:
            with open(os.path.join(model_dir, "bm25_vectorizer.pkl"), "rb") as f:
                self._vectorizer = pickle.load(f)
            with open(os.path.join(model_dir, "bm25_tf_matrix.pkl"), "rb") as f:
                self._tf_matrix = pickle.load(f)
            with open(os.path.join(model_dir, "bm25_matrix.pkl"), "rb") as f:
                self._bm25_matrix = pickle.load(f)
            with open(os.path.join(model_dir, "bm25_row_to_chunk.pkl"), "rb") as f:
                self.matrix_row_to_chunk_map = pickle.load(f)
            return True
        except Exception as e:
            log.info("Error loading BM25 state: %s", e)
            return False

    def save(self) -> None:
        model_dir = self._persistence.model_dir
        if model_dir is None:
            raise ValueError(
                "Cannot save BM25Retriever: persistence.model_dir is None."
            )
        os.makedirs(model_dir, exist_ok=True)
        to_save = {
            "bm25_vectorizer.pkl": self._vectorizer,
            "bm25_tf_matrix.pkl": self._tf_matrix,
            "bm25_matrix.pkl": self._bm25_matrix,
            "bm25_row_to_chunk.pkl": self.matrix_row_to_chunk_map,
        }
        for fname, obj in to_save.items():
            with open(os.path.join(model_dir, fname), "wb") as f:
                pickle.dump(obj, f)

    def _fit(self):
        chunk_texts = []
        current_idx = 0
        self.matrix_row_to_chunk_map: Dict[int, Chunk] = {}

        for doc_chunks in self.chunks.values():
            for chunk in doc_chunks.values():
                chunk_texts.append(chunk.text)
                self.matrix_row_to_chunk_map[current_idx] = chunk
                current_idx += 1

        self._vectorizer.fit(chunk_texts)
        self._tf_matrix = self._vectorizer.transform(chunk_texts)

        tf = self._tf_matrix.copy()
        n_docs = tf.shape[0]
        doc_lengths = np.array(tf.sum(axis=1)).flatten()
        avgdl = np.mean(doc_lengths)

        df = np.array((tf > 0).sum(axis=0)).flatten()
        idf = np.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
        idf += self.delta
        idf[idf < 0] = 0

        from scipy.sparse import lil_matrix

        bm25 = lil_matrix(tf.shape)
        for i in range(tf.shape[0]):
            row = tf[i]
            length_norm = 1 - self.b + self.b * (doc_lengths[i] / avgdl)
            for j in range(row.indptr[0], row.indptr[1]):
                col = row.indices[j]
                tf_val = row.data[j]
                numerator = tf_val * (self.k1 + 1)
                denominator = tf_val + self.k1 * length_norm
                bm25[i, col] = idf[col] * numerator / denominator

        self._bm25_matrix = bm25.tocsr()

    @property
    def retrieval_top_k(self) -> int:
        return self._top_k

    def retrieve(self, query: str, top_k: int | None = None) -> List[Chunk]:
        k = top_k if top_k is not None else self._top_k
        query_vec = self._vectorizer.transform([query])
        similarities = pairwise_distances(
            query_vec,
            self._bm25_matrix,
            metric=self.similarity_function_name,
        ).flatten()

        if self.similarity_threshold is not None:
            mask = similarities <= self.similarity_threshold
            filtered = np.where(mask)[0]
            top_indices = filtered[np.argsort(similarities[filtered])[:k]]
        else:
            top_indices = np.argsort(similarities)[:k]

        return [self.matrix_row_to_chunk_map[idx] for idx in top_indices]

    def score_chunks(self, chunk_ids: List[int], query: str) -> List[Tuple[int, float]]:
        query_vec = self._vectorizer.transform([query])
        chunk_id_to_row = {c.id: r for r, c in self.matrix_row_to_chunk_map.items()}

        rows, valid_ids = [], []
        for cid in chunk_ids:
            row = chunk_id_to_row.get(cid)
            if row is not None:
                rows.append(row)
                valid_ids.append(cid)

        if not rows:
            return []

        chunk_vectors = self._bm25_matrix[rows]
        distances = pairwise_distances(
            query_vec,
            chunk_vectors,
            metric=self.similarity_function_name,
        ).flatten()
        scored = list(zip(valid_ids, distances.tolist()))
        scored.sort(key=lambda x: x[1])
        return scored

import logging
import os
import pickle
from typing import Dict, List, Tuple

import numpy as np
from scipy.sparse import lil_matrix
from sklearn.feature_extraction.text import CountVectorizer
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
from DashAI.back.models.RAG.retrievers.sparse.sparse_retriever import SparseRetriever

log = logging.getLogger(__name__)


class BM25VectorizerSchema(BaseSchema):
    """Schema for the BM25 vectorizer parameters.

    Attributes:
        strip_accents: Whether to remove accents during preprocessing.
        lowercase: Whether to convert all characters to lowercase.
        stop_words: List of stop words (or ``None``).
        max_df: Document frequency upper threshold.
        min_df: Document frequency lower threshold.
        max_features: Maximum number of features (or ``None``).
    """

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


class BM25VectorizerModel(BaseModel):
    """Model component that encapsulates a :class:`CountVectorizer` for BM25.

    The vectorizer provides term-frequency counts; the BM25 weighting
    is applied by the parent :class:`BM25Retriever`.
    """

    DISPLAY_NAME: str = MultilingualString(
        en="BM25 Vectorizer",
        es="Vectorizador BM25",
    )
    DESCRIPTION: str = MultilingualString(
        en="Vectorizer for BM25Retriever using CountVectorizer with"
        " BM25-specific parameters.",
        es="Vectorizador para BM25Retriever usando CountVectorizer con"
        " parámetros específicos de BM25.",
    )

    SCHEMA = BM25VectorizerSchema

    def __init__(self, **kwargs):
        """Initialize and build the underlying ``CountVectorizer``.

        Args:
            **kwargs: Parameters matching :class:`BM25VectorizerSchema`.
        """
        validated = self.SCHEMA.model_validate(kwargs)
        self.params = dict(validated)
        self.vectorizer = CountVectorizer(
            strip_accents=self.params.pop("strip_accents"),
            lowercase=self.params.pop("lowercase"),
            stop_words=self.params.pop("stop_words"),
            max_df=self.params.pop("max_df"),
            min_df=self.params.pop("min_df"),
            max_features=self.params.pop("max_features"),
        )

    def load(self):
        """No-op load (state managed by the parent retriever)."""

    def save(self):
        """No-op save (state managed by the parent retriever)."""

    def train(self):
        """No-op train (fitting is done by the parent retriever)."""


class BM25RetrieverSchema(BaseSchema):
    """Schema for :class:`BM25Retriever`.

    Attributes:
        BM25Vectorizer: Parameters for the CountVectorizer component.
        k1: BM25 term frequency saturation parameter.
        b: BM25 length normalisation parameter.
        delta: BM25 IDF smoothing parameter.
        similarity_function: Distance metric for vector comparison.
        top_k: Number of chunks to select.
    """

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
        enum_field(["cityblock", "cosine", "euclidean", "l1", "l2", "manhattan"]),
        placeholder="cosine",
        description=MultilingualString(
            en="Distance metric for comparing BM25-weighted vectors.",
            es="Métrica de distancia para comparar vectores ponderados BM25.",
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


class BM25Retriever(SparseRetriever):
    """Sparse retriever using BM25 (Okapi) ranking for document retrieval.

    Computes BM25-weighted term-frequency vectors and retrieves via
    pairwise distance.
    """

    FLAGS: list[str] = ["keyword", "sparse"]
    DISPLAY_NAME: str = MultilingualString(
        en="BM25 Retriever",
        es="Recuperador BM25",
    )
    DESCRIPTION: str = MultilingualString(
        en="Sparse retriever using BM25 (Okapi) ranking for document retrieval.",
        es="Recuperador disperso que usa ranking BM25 (Okapi) para"
        " recuperar documentos.",
    )

    SCHEMA = BM25RetrieverSchema

    def __init__(self, **kwargs):
        """Initialize the BM25 retriever.

        Args:
            **kwargs: Must contain ``BM25Vectorizer``, ``k1``, ``b``,
                ``delta``, ``similarity_function``, and ``top_k``.
        """
        super().__init__(**kwargs)

        self.k1 = self.params.pop("k1")
        self.b = self.params.pop("b")
        self.delta = self.params.pop("delta")
        self.similarity_function_name = self.params.pop("similarity_function")
        self._top_k = self.params.pop("top_k")

        vectorizer_model = self.params.pop("BM25Vectorizer")
        self._vectorizer = vectorizer_model.vectorizer

    def init_model(self) -> None:
        """Restore saved state or fit BM25 from scratch."""
        if not self.load():
            self._fit()

    def load(self) -> bool:
        """Load a previously saved BM25 state from disk.

        Returns:
            ``True`` if state was loaded successfully, ``False`` if
            no saved state exists or loading failed.
        """
        if self._persistence.model_dir is None:
            return False
        model_dir = self._persistence.model_dir
        try:
            with open(os.path.join(model_dir, "bm25_vectorizer.pkl"), "rb") as f:
                vectorizer = pickle.load(f)
            with open(os.path.join(model_dir, "bm25_tf_matrix.pkl"), "rb") as f:
                tf_matrix = pickle.load(f)
            with open(os.path.join(model_dir, "bm25_matrix.pkl"), "rb") as f:
                bm25_matrix = pickle.load(f)
            with open(os.path.join(model_dir, "bm25_row_to_chunk.pkl"), "rb") as f:
                matrix_row_to_chunk_map = pickle.load(f)
            self._vectorizer = vectorizer
            self._tf_matrix = tf_matrix
            self._bm25_matrix = bm25_matrix
            self.matrix_row_to_chunk_map = matrix_row_to_chunk_map
            return True
        except Exception as e:
            log.error("Error loading BM25 state: %s", e)
            return False

    def save(self) -> None:
        """Persist the vectorizer, matrices, and chunk map to disk.

        Raises:
            ValueError: If ``persistence.model_dir`` is ``None``.
        """
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
        """Fit the CountVectorizer and compute the BM25-weighted matrix."""
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
        """Return the configured top-k value.

        Returns:
            Number of chunks to retrieve.
        """
        return self._top_k

    def retrieve(self, query: str, top_k: int | None = None) -> List[Chunk]:
        """Retrieve the top-k chunks by BM25-weighted similarity.

        Args:
            query: The search query string.
            top_k: Override for the default ``top_k``. Uses the
                configured value if ``None``.

        Returns:
            A list of :class:`Chunk` instances ordered by distance.
        """
        self._check_infra()
        k = top_k if top_k is not None else self._top_k
        query_vec = self._vectorizer.transform([query])
        distances = pairwise_distances(
            query_vec,
            self._bm25_matrix,
            metric=self.similarity_function_name,
        ).flatten()
        top_indices = np.argsort(distances)[:k]
        return [self.matrix_row_to_chunk_map[idx] for idx in top_indices]

    def score_chunks(self, chunk_ids: List[int], query: str) -> List[Tuple[int, float]]:
        """Score a set of chunk IDs against the query.

        Args:
            chunk_ids: List of chunk IDs to score.
            query: The search query string.

        Returns:
            A list of ``(chunk_id, distance)`` tuples sorted by distance.
        """
        self._check_infra()
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
        scored = list(zip(valid_ids, distances.tolist(), strict=True))
        scored.sort(key=lambda x: x[1])
        return scored

    def get_chunk_vectors(self, chunk_ids: List[int]) -> np.ndarray:
        """Return the BM25-weighted vectors for the given chunk IDs.

        Args:
            chunk_ids: List of chunk IDs whose vectors are needed.

        Returns:
            A 2D numpy array of BM25-weighted vectors.

        Raises:
            ValueError: If none of the provided chunk IDs are found in
                the matrix.
        """
        chunk_id_to_row = {c.id: r for r, c in self.matrix_row_to_chunk_map.items()}
        rows = []
        for cid in chunk_ids:
            row = chunk_id_to_row.get(cid)
            if row is not None:
                rows.append(row)
        if not rows:
            raise ValueError(
                f"None of the provided chunk_ids {chunk_ids} were found "
                "in the BM25 matrix."
            )
        return self._bm25_matrix[rows].toarray()

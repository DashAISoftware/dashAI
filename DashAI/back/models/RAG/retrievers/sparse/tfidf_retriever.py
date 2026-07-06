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
    schema_field,
    string_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.base_model import BaseModel
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.retrievers.sparse.sparse_retriever import SparseRetriever

log = logging.getLogger(__name__)


class TFIDFVectorizerSchema(BaseSchema):
    strip_accents: schema_field(
        enum_field(enum=["ascii", "unicode", "None"]),
        placeholder="None",
        description=MultilingualString(
            en="Whether to strip accents from the text.",
            es="Si se deben eliminar los acentos del texto.",
        ),
    )  # type: ignore

    lowercase: schema_field(
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en="Whether to convert all characters to lowercase.",
            es="Si se deben convertir todos los caracteres a minúsculas.",
        ),
    )  # type: ignore

    analyzer: schema_field(
        enum_field(enum=["word", "char", "char_wb"]),
        placeholder="word",
        description=MultilingualString(
            en="Whether the feature should be made of word or character n-grams.",
            es="Si las características deben ser n-gramas de palabras o caracteres.",
        ),
    )  # type: ignore

    stop_words: schema_field(
        list_field(string_field(), min_items=0),
        placeholder=[],
        description=MultilingualString(
            en="List of stop words. Leave empty to use none.",
            es="Lista de palabras vacías. Dejar vacío para no usar ninguna.",
        ),
    )  # type: ignore

    ngram_range: schema_field(
        list_field(int_field(), min_items=2, max_items=2),
        placeholder=[1, 1],
        description=MultilingualString(
            en="Lower and upper boundary of the n-gram range.",
            es="Límite inferior y superior del rango de n-gramas.",
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
        int_field(ge=0),
        placeholder=1000,
        description=MultilingualString(
            en="Maximum number of features. 0 means no limit.",
            es="Número máximo de características. 0 significa sin límite.",
        ),
    )  # type: ignore

    norm: schema_field(
        enum_field(enum=["l1", "l2", "None"]),
        placeholder="l2",
        description=MultilingualString(
            en="Norm used to normalize term vectors.",
            es="Norma utilizada para normalizar los vectores de términos.",
        ),
    )  # type: ignore

    use_idf: schema_field(
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en="Enable inverse-document-frequency reweighting.",
            es="Activar reponderación por frecuencia inversa de documento.",
        ),
    )  # type: ignore

    smooth_idf: schema_field(
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en="Smooth IDF weights to prevent zero divisions.",
            es="Suavizar pesos IDF para prevenir divisiones por cero.",
        ),
    )  # type: ignore

    sublinear_tf: schema_field(
        bool_field(),
        placeholder=False,
        description=MultilingualString(
            en="Apply sublinear TF scaling (1 + log(tf)).",
            es="Aplicar escalado sublineal de TF (1 + log(tf)).",
        ),
    )  # type: ignore


class TFIDFVectorizerModel(BaseModel):
    SCHEMA = TFIDFVectorizerSchema
    DISPLAY_NAME: str = MultilingualString(
        en="TF-IDF Vectorizer Model",
        es="Modelo de Vectorización TF-IDF",
    )
    DESCRIPTION: str = MultilingualString(
        en="Model component that encapsulates a TF-IDF vectorizer.",
        es="Componente del modelo que encapsula un vectorizador TF-IDF.",
    )

    def __init__(self, **kwargs) -> None:
        validated = self.SCHEMA.model_validate(kwargs)
        self.params = dict(validated)
        if self.params.get("strip_accents") == "None":
            self.params["strip_accents"] = None
        stop_words = self.params.get("stop_words") or None
        ngram_range = tuple(self.params.get("ngram_range"))
        self.model = TfidfVectorizer(
            strip_accents=self.params.get("strip_accents"),
            lowercase=self.params.get("lowercase"),
            analyzer=self.params.get("analyzer"),
            stop_words=stop_words,
            ngram_range=ngram_range,
            max_df=self.params.get("max_df"),
            min_df=self.params.get("min_df"),
            max_features=self.params.get("max_features"),
            norm=self.params.get("norm"),
            use_idf=self.params.get("use_idf"),
            smooth_idf=self.params.get("smooth_idf"),
            sublinear_tf=self.params.get("sublinear_tf"),
        )

    def save(self, filename: str = "") -> None:
        pass

    def load(self, filename: str = "") -> None:
        pass

    def train(self, **kwargs):
        return


class TFIDFRetrieverSchema(BaseSchema):
    TFIDFVectorizer: schema_field(
        component_field(parent="TFIDFVectorizerModel"),
        placeholder={"component": "TFIDFVectorizerModel", "params": {}},
        description=MultilingualString(
            en="TF-IDF Vectorizer parameters.",
            es="Parámetros del vectorizador TF-IDF.",
        ),
    )  # type: ignore

    similarity_function: schema_field(
        enum_field(["cityblock", "cosine", "euclidean", "l1", "l2", "manhattan"]),
        placeholder="cosine",
        description=MultilingualString(
            en="Distance metric for comparing TF-IDF vectors.",
            es="Métrica de distancia para comparar vectores TF-IDF.",
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


class TFIDFRetriever(SparseRetriever):
    FLAGS: list[str] = ["keyword", "sparse"]
    DISPLAY_NAME: str = MultilingualString(
        en="TF-IDF Retriever",
        es="Recuperador TF-IDF",
    )
    DESCRIPTION: str = MultilingualString(
        en="Sparse retriever using TF-IDF vectorization for document retrieval.",
        es="Recuperador disperso que usa vectorización TF-IDF para recuperar documentos.",
    )

    SCHEMA = TFIDFRetrieverSchema

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        vectorizer_model = self.params.pop("TFIDFVectorizer")
        self._vectorizer = vectorizer_model.model
        self.similarity_function_name = self.params.pop("similarity_function")
        self._top_k = self.params.pop("top_k")

    def init_model(self) -> None:
        if not self.load():
            self._fit()

    def load(self) -> bool:
        if self._persistence.model_dir is None:
            return False
        model_dir = self._persistence.model_dir
        try:
            with open(os.path.join(model_dir, "tfidf_vectorizer.pkl"), "rb") as f:
                self._vectorizer = pickle.load(f)
            with open(os.path.join(model_dir, "tf_idf_matrix.pkl"), "rb") as f:
                self._tf_idf_matrix = pickle.load(f)
            with open(
                os.path.join(model_dir, "matrix_row_to_chunk_map.pkl"), "rb"
            ) as f:
                self.matrix_row_to_chunk_map = pickle.load(f)
            return True
        except Exception as e:
            log.info("Error loading TFIDF state: %s", e)
            return False

    def save(self) -> None:
        model_dir = self._persistence.model_dir
        if model_dir is None:
            raise ValueError(
                "Cannot save TFIDFRetriever: persistence.model_dir is None."
            )
        os.makedirs(model_dir, exist_ok=True)
        to_save = {
            "tfidf_vectorizer.pkl": self._vectorizer,
            "tf_idf_matrix.pkl": self._tf_idf_matrix,
            "matrix_row_to_chunk_map.pkl": self.matrix_row_to_chunk_map,
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

        self._tf_idf_matrix = self._vectorizer.fit_transform(chunk_texts)

    @property
    def retrieval_top_k(self) -> int:
        return self._top_k



    def retrieve(self, query: str, top_k: int | None = None) -> List[Chunk]:
        self._check_infra()
        k = top_k if top_k is not None else self._top_k
        query_vector = self._vectorizer.transform([query])
        distances = pairwise_distances(
            query_vector,
            self._tf_idf_matrix,
            metric=self.similarity_function_name,
        ).flatten()
        top_indices = np.argsort(distances)[:k]
        return [self.matrix_row_to_chunk_map[idx] for idx in top_indices]

    def score_chunks(self, chunk_ids: List[int], query: str) -> List[Tuple[int, float]]:
        self._check_infra()
        query_vector = self._vectorizer.transform([query])
        chunk_id_to_row = {c.id: r for r, c in self.matrix_row_to_chunk_map.items()}
        rows, valid_ids = [], []
        for cid in chunk_ids:
            row = chunk_id_to_row.get(cid)
            if row is not None:
                rows.append(row)
                valid_ids.append(cid)
        if not rows:
            return []
        distances = pairwise_distances(
            query_vector,
            self._tf_idf_matrix[rows],
            metric=self.similarity_function_name,
        ).flatten()
        scored = list(zip(valid_ids, distances.tolist()))
        scored.sort(key=lambda x: x[1])
        return scored

    def get_chunk_vectors(self, chunk_ids: List[int]) -> np.ndarray:
        chunk_id_to_row = {c.id: r for r, c in self.matrix_row_to_chunk_map.items()}
        rows = []
        for cid in chunk_ids:
            row = chunk_id_to_row.get(cid)
            if row is not None:
                rows.append(row)
        if not rows:
            raise ValueError(
                f"None of the provided chunk_ids {chunk_ids} were found "
                "in the TF-IDF matrix."
            )
        return self._tf_idf_matrix[rows].toarray()

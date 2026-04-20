import os
import pickle
from typing import Dict, List, Tuple
from typing_extensions import Final

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import pairwise_distances
from sqlalchemy.orm import Session

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
from DashAI.back.dependencies.database.models import (
    RAGPipeline as PipelineDBModel,
)
from DashAI.back.dependencies.database.models import (
    RAGRetriever as RetrieverDBModel,
)
from DashAI.back.dependencies.database.models import (
    RAGSparseRetriever as SparseRetrieverDBModel,
)
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.base_model import BaseModel
from DashAI.back.models.RAG.documents import BaseDocument, Chunk
from DashAI.back.models.RAG.retrievers.sparse_retriever import SparseRetriever
from DashAI.back.models.RAG.extra_args_enum import (
    PIPELINE_ID,
    DB,
    COMPONENT_REGISTRY,
    ENV_RAG_PATH,
    DOCUMENTS,
    CHUNKS,
    CHUNKING_MODEL_ID,
    SPARSE_RETRIEVER_DB_MODEL_ENUM
)


class TFIDFVectorizerSchema(BaseSchema):
    strip_accents: schema_field(
        enum_field(
            enum=["ascii", "unicode", "None"],
        ),
        placeholder="None",
        description="Whether to strip accents from the text.",
    )  # type: ignore

    lowercase: schema_field(
        bool_field(),
        placeholder=True,
        description="Whether to convert all characters to lowercase.",
    )  # type: ignore

    analyzer: schema_field(
        enum_field(
            enum=["word", "char", "char_wb"],
        ),
        placeholder="word",
        description=(
            "Whether the feature should be made of word or character n-grams. "
            "Option 'char_wb' creates character n-grams only from text inside "
            "word boundaries; n-grams at the edges of words are padded with space."
        ),
    )  # type: ignore

    stop_words: schema_field(
        list_field(
            string_field(),
            min_items=0,
        ),
        placeholder=[],
        description=(
            "List of stop words to be used in the TF-IDF vectorization. "
            "Leave empty to use no stop words."
        ),
    )  # type: ignore

    ngram_range: schema_field(
        list_field(
            int_field(),
            min_items=2,
            max_items=2,
        ),
        placeholder=[1, 1],
        description=(
            "The lower and upper boundary of the range of n-values "
            "for different n-grams to be extracted."
        ),
    )  # type: ignore

    max_df: schema_field(
        float_field(
            ge=0.0,
            le=1.0,
        ),
        placeholder=1.0,
        description=(
            "When building the vocabulary ignore terms that have a document "
            "frequency strictly higher than the given threshold "
            "(corpus-specific stop words)."
        ),
    )  # type: ignore

    min_df: schema_field(
        float_field(
            ge=0.0,
            le=1.0,
        ),
        placeholder=1.0,
        description=(
            "When building the vocabulary ignore terms that have a document "
            "frequency strictly lower than the given threshold "
            "(corpus-specific stop words)."
        ),
    )  # type: ignore

    max_features: schema_field(
        int_field(
            ge=0,
        ),
        placeholder=0,
        description=(
            "If not 0, build a vocabulary that only consider the top "
            "max_features ordered by term frequency across the corpus."
        ),
    )  # type: ignore

    norm: schema_field(
        enum_field(
            enum=["l1", "l2", "None"],
        ),
        placeholder="l2",
        description=(
            "The norm used to normalize term vectors. "
            "If None, no normalization is applied."
        ),
    )  # type: ignore

    use_idf: schema_field(
        bool_field(),
        placeholder=True,
        description="Enable inverse-document-frequency reweighting.",
    )  # type: ignore

    smooth_idf: schema_field(
        bool_field(),
        placeholder=True,
        description=(
            "Smooth idf weights by adding one to document frequencies, "
            "as if an extra document was seen containing every term in the "
            "collection exactly once. This prevents zero divisions."
        ),
    )  # type: ignore

    sublinear_tf: schema_field(
        bool_field(),
        placeholder=False,
        description="Apply sublinear tf scaling, i.e. replace tf with 1 + log(tf).",
    )  # type: ignore


class TFIDFVectorizerModel(BaseModel):
    REQUIRED_EXTRA_KWARGS: Final[List[str]] = []
    SCHEMA = TFIDFVectorizerSchema

    def __init__(self, **kwargs) -> None:
        self.model = TfidfVectorizer(**kwargs)

    def save():
        pass

    def load(self):
        pass

    def train(self, **kwargs):
        return


class TFIDFRetrieverSchema(BaseSchema):
    """
    Schema for the TFIDFRetriever.
    """

    TFIDFVectorizer: schema_field(
        component_field(parent="TFIDFVectorizerModel"),
        placeholder={"component": "TFIDFVectorizerModel", "params": {}},
        description="TF-IDF Vectorizer parameters.",
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
        description="Similarity function to use for document retrieval.",
    )  # type: ignore

    top_k: schema_field(
        int_field(ge=1), placeholder=5, description="Number of chunks to select."
    )  # type: ignore

    similarity_threshold: schema_field(
        none_type(float_field()),
        placeholder=None,
        description=(
            "Maximum or minimum distance for retrieved documents "
            "based on the similarity_function. Leave empty to disable filtering."
        ),
    )  # type: ignore


class TFIDFRetriever(SparseRetriever):
    """
    A retriever that uses TF-IDF to retrieve documents based on a query.
    """

    SCHEMA = TFIDFRetrieverSchema
    REQUIRED_EXTRA_KWARGS: Final[List[str]] = [
        PIPELINE_ID, 
        DB, 
        COMPONENT_REGISTRY, 
        ENV_RAG_PATH, 
        DOCUMENTS, 
        CHUNKS, 
        CHUNKING_MODEL_ID,
        SPARSE_RETRIEVER_DB_MODEL_ENUM]

    db: Session
    component_registry: ComponentRegistry
    env_rag_path: str | os.PathLike

    documents: Dict[int, BaseDocument]
    chunks: Dict[int, Dict[int, Chunk]]
    chunking_model_id: int

    id: int
    sparse_retriever_db_model = SparseRetrieverDBModel

    matrix_row_to_chunk_id: Dict[int, int]
    chunk_id_to_doc_id: Dict[int, int]

    def __init__(
        self,
        **kwargs,
    ):
        """
        Initialize the TFIDFRetriever with the given parameters.

        Args:
            documents_paths (List[str]): A list of document texts to be indexed.
            similarity_function (str): Similarity function to use
                ('cosine' or 'euclidean').
            n_docs (int): The maximum number of documents to retrieve.
            distance_threshold (float): The maximum or minimum distance for
                retrieved documents based on the similarity_function.
            chunk_size (int): The size of chunks to split the documents into.
            chunk_overlap (int): The overlap between chunks.
        """
        self.parameters = kwargs.copy()
        for required_kwarg in self.REQUIRED_EXTRA_KWARGS:
            self.parameters.pop(required_kwarg)

        kwargs["class_name"] = self.__class__.__name__
        self.sparse_retriever_db_model = kwargs.pop(SPARSE_RETRIEVER_DB_MODEL_ENUM)
        self.id:int = self.sparse_retriever_db_model.id if self.sparse_retriever_db_model else None
        kwargs["TFIDFVectorizer"] = kwargs["TFIDFVectorizer"]["properties"]["params"]["comp"]
        super().__init__(**kwargs)

        vectorizer: TFIDFVectorizerModel = self.params.pop("TFIDFVectorizer")
        self.vectorizer_params = vectorizer.model
        self.similarity_function_name = kwargs.pop("similarity_function")
        self.top_k = kwargs.pop("top_k")

        loaded = self.load()

        # Attempt to load from cache
        if loaded:
            print(
                f"TFIDFRetriever loaded from db, "
                f"sparse retriever id: {self.sparse_retriever_db_model.id}."
            )
        else:
            print("Fitting new model...")
            self._fit()
            print(
                f"TFIDFRetriever fitted and waiting to be stored after db models creation."
            )

    def load(self) -> None:
        if self.sparse_retriever_db_model is None:
            return False
        storage_folder = self.sparse_retriever_db_model.storage_folder
        self._vectorizer_path = os.path.join(storage_folder, "tfidf_vectorizer.pkl")
        self._tf_idf_matrix_path = os.path.join(storage_folder, "tf_idf_matrix.pkl")
        self.matrix_row_to_chunk_path = os.path.join(
            storage_folder, "matrix_row_to_chunk_map.pkl"
        )
        try:
            with open(self._vectorizer_path, "rb") as f:
                self._vectorizer = pickle.load(f)
            with open(self._tf_idf_matrix_path, "rb") as f:
                self._tf_idf_matrix = pickle.load(f)
            with open(self.matrix_row_to_chunk_path, "rb") as f:
                self.matrix_row_to_chunk_map = pickle.load(f)
            return True
        except Exception as e:
            print(f"Error loading state: {e}")
            return False

    def save(self, **kwargs) -> None:
        self.sparse_retriever_db_model = kwargs.get(SPARSE_RETRIEVER_DB_MODEL_ENUM)
        if self.sparse_retriever_db_model is None:
            raise ValueError("sparse_retriever_db_model is required to save the model.")
        storage_folder = self.sparse_retriever_db_model.storage_folder
        os.makedirs(storage_folder, exist_ok=True)
        self._vectorizer_path = os.path.join(storage_folder, "tfidf_vectorizer.pkl")
        self._tf_idf_matrix_path = os.path.join(storage_folder, "tf_idf_matrix.pkl")
        self.matrix_row_to_chunk_path = os.path.join(
            storage_folder, "matrix_row_to_chunk_map.pkl"
        )
        with open(self._vectorizer_path, "wb") as f:
            pickle.dump(self._vectorizer, f)
        with open(self._tf_idf_matrix_path, "wb") as f:
            pickle.dump(self._tf_idf_matrix, f)
        with open(self.matrix_row_to_chunk_path, "wb") as f:
            pickle.dump(self.matrix_row_to_chunk_map, f)

    def save_model_to_db(self, **kwargs) -> None:
        """
        Save the retriever model to the database.
        This method should be called after fitting the model.
        """
        assert SPARSE_RETRIEVER_DB_MODEL_ENUM in kwargs, (
            f"{SPARSE_RETRIEVER_DB_MODEL_ENUM} is required to save the model."
        )
        self.save(**kwargs)

    def _fit(self):
        """
        Fit the TF-IDF model to the documents.
        This method should be called after initializing the retriever.
        """
        # Load chunks from the documents
        chunk_texts = []
        current_chunk_idx = 0
        self.matrix_row_to_chunk_map: Dict[int, Chunk] = {}

        for _doc_id, doc_chunks in self.chunks.items():
            for _chunk_pos, chunk in doc_chunks.items():
                chunk_texts.append(chunk.text)
                self.matrix_row_to_chunk_map[current_chunk_idx] = chunk
                current_chunk_idx += 1

        # Create the TF-IDF vectorizer and fit it to the chunks
        self._vectorizer = TfidfVectorizer()
        self._tf_idf_matrix = self._vectorizer.fit_transform(chunk_texts)

    def retrieve(self, query: str) -> List[Tuple[str, str, int]]:
        """
        Retrieve documents based on the query using TF-IDF.
        Args:
            query (str): The query string to search for.
        Returns:
            List[Tuple[str, str, int]]: A list of tuples containing the chunk
                text, document path, and chunk ID.
        """
        assert self._tf_idf_matrix is not None, (
            "Model is not fitted. Call _fit() before retrieving."
        )

        print(f"Retrieving documents for query: {query}")
        # Transform the query using the same vectorizer
        query_vector = self._vectorizer.transform([query])

        # Calculate the similarity scores
        similarities = pairwise_distances(
            query_vector, self._tf_idf_matrix, metric=self.similarity_function_name
        ).flatten()

        top_indices = np.argsort(similarities)[: self.top_k]

        results = []
        for idx in top_indices:
            chunk = self.matrix_row_to_chunk_map[idx]
            results.append(chunk)
        return results

    def set_id(self, id: int) -> None:
        """Set the ID of the retriever model from the database."""
        if self.id is None:
            self.id = id
        else:
            raise ValueError("ID is already set and cannot be modified.")
        
    def get_id(self) -> int:
        """Get the ID of the retriever model from the database."""
        return self.sparse_retriever_db_model.id
    
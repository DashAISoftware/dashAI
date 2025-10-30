import numpy as np
import os
from sqlalchemy.orm import Session
from typing import Dict, List, Tuple

import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import pairwise_distances

from DashAI.back.models.base_model import BaseModel
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
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.dependencies.database.models import (
    RAGPipeline as PipelineDBModel,
    RAGRetriever as RetrieverDBModel,
    RAGSparseRetriever as SparseRetrieverDBModel,
)
from DashAI.back.models.RAG.documents import BaseDocument, Chunk
from DashAI.back.models.RAG.Retrievers.sparse_retriever import SparseRetriever
from DashAI.back.models.RAG.utils import hash_function



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
        description="List of stop words to be used in the TF-IDF vectorization.",
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
    SCHEMA = TFIDFVectorizerSchema

    def __init__(self, **kwargs) -> None:
        self.model = TfidfVectorizer(**kwargs)

    def save():
        pass

    def load(self):
        pass


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
        enum_field([
            "cityblock", "cosine", "euclidean", "l1", "l2", "manhattan", "nan_euclidean",
            "braycurtis", "canberra", "chebyshev", "correlation", "dice", "hamming", "jaccard", 
            "mahalanobis", "minkowski", "rogerstanimoto", "russellrao", "seuclidean", 
            "sokalmichener", "sokalsneath", "sqeuclidean", "yule"
            ]),
        placeholder="cosine",
        description="Similarity function to use for document retrieval.",
    )  # type: ignore

    top_k: schema_field(
        int_field(ge=1), 
        placeholder=5, 
        description="Number of documents to retrieve."
    )  # type: ignore

    use_similarity_threshold: schema_field(
        bool_field(),
        placeholder=False,
        description="Whether to use a similarity threshold for filtering retrieved documents.",
    )  # type: ignore

    similarity_threshold: schema_field(
        float_field(),
        placeholder=0.5,
        description=(
            "Maximum or minimum distance for retrieved documents "
            "based on the similarity_function."
        ),
    )  # type: ignore


class TFIDFRetriever(SparseRetriever):
    """
    A retriever that uses TF-IDF to retrieve documents based on a query.
    """

    SCHEMA = TFIDFRetrieverSchema

    pipeline_id: int
    db: Session
    component_registry: ComponentRegistry
    env_rag_path: str|os.PathLike

    documents: Dict[int, BaseDocument]
    chunks: Dict[int, Dict[int, Chunk]]
    chunking_model_id: int

    id: int
    retriever_db_model = RetrieverDBModel
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
        self.retriever_db_model = None
        self.sparse_retriever_db_model = None
        kwargs["TFIDFVectorizer"] = kwargs["TFIDFVectorizer"]["properties"]["params"]["comp"]
        super().__init__(**kwargs)

        vectorizer: TFIDFVectorizerModel = self.params.pop("TFIDFVectorizer")
        self.vectorizer_params = vectorizer.model
        self.similarity_function_name = kwargs.pop("similarity_function")
        self.top_k = kwargs.pop("top_k")

        loaded = self.load()

        # Attempt to load from cache
        if loaded:
            print(f"TFIDFRetriever loaded from db (pipeline{self.pipeline_id}, sparse retriever {self.sparse_retriever_db_model.id}).")
        else:
            print(
                f"Fitting new model..."
            )
            self._fit()
            self.save()
            print(f"TFIDFRetriever fitted and saved (pipeline{self.pipeline_id}, sparse retriever {self.sparse_retriever_db_model.id}).")

    def load(self) -> None:
        self._fetch_db_models()
        if not self.sparse_retriever_db_model:
            return False
        storage_folder = self.sparse_retriever_db_model.storage_folder
        self._vectorizer_path = os.path.join(
            storage_folder, "tfidf_vectorizer.pkl"
        )
        self._tf_idf_matrix_path = os.path.join(
            storage_folder, "tf_idf_matrix.pkl"
        )
        self.matrix_row_to_chunk_path = os.path.join(
            storage_folder, "matrix_row_to_chunk_map.pkl"
        )
        try:
            with open(self._vectorizer_path, "rb") as f:
                self._vectorizer = pickle.load(f)
            with open(self._tf_idf_matrix_path, "rb") as f:
                self._tf_idf_matrix = pickle.load(f)
            with open(self.chunk_to_doc_path, "rb") as f:
                self.matrix_row_to_chunk_map = pickle.load(f)
            return True
        except Exception as e:
            print(f"Error loading state: {e}")
            return False
        

    def save(self) -> None:
        if not self.sparse_retriever_db_model:
            self._create_db_models()
        storage_folder = self.sparse_retriever_db_model.storage_folder 
        os.makedirs(storage_folder, exist_ok=True)
        storage_folder = self.sparse_retriever_db_model.storage_folder
        self._vectorizer_path = os.path.join(
            storage_folder, "tfidf_vectorizer.pkl"
        )
        self._tf_idf_matrix_path = os.path.join(
            storage_folder, "tf_idf_matrix.pkl"
        )
        self.matrix_row_to_chunk_path = os.path.join(
            storage_folder, "matrix_row_to_chunk_map.pkl"
        )
        with open(self._vectorizer_path, "wb") as f:
            pickle.dump(self._vectorizer, f)
        with open(self._tf_idf_matrix_path, "wb") as f:
            pickle.dump(self._tf_idf_matrix, f)
        with open(self.matrix_row_to_chunk_path, "wb") as f:
            pickle.dump(self.matrix_row_to_chunk_map, f)

    def _fetch_db_models(self):
        if not self.pipeline_id:
            return
        pipeline_db_model = self.db.query(PipelineDBModel).filter(
            PipelineDBModel.id == self.pipeline_id).first()

        if not pipeline_db_model:
            return
        retriever_id = pipeline_db_model.retriever_id
            
        self.retriever_db_model = self.db.query(RetrieverDBModel).filter(
            RetrieverDBModel.id == retriever_id).first()

        if not self.retriever_db_model:
            return
        
        sparse_retriever_id = self.retriever_db_model.sparse_retriever_id
        
        self.sparse_retriever_db_model = self.db.query(SparseRetrieverDBModel).filter(
            SparseRetrieverDBModel.id == sparse_retriever_id).first()

    def _create_db_models(self) -> None:
        self.sparse_retriever_db_model = SparseRetrieverDBModel(
            class_name = self.__class__.__name__,
            parameters = self.params,
            storage_folder = "" 
        )
        self.db.add(self.sparse_retriever_db_model)
        self.db.commit()
        storage_folder = os.path.join(
            self.env_rag_path,
            "retrievers",
            "sparse_retrievers",
            f"sparse_retriever_{self.sparse_retriever_db_model.id}"
        )
        self.sparse_retriever_db_model.storage_folder = storage_folder
        self.db.commit()
        os.makedirs(storage_folder, exist_ok=True)
        if self.retriever_db_model is None:
            self.retriever_db_model = RetrieverDBModel(
                class_name="SparseRetriever",
                dense_retriever_id=None,
                sparse_retriever_id=self.sparse_retriever_db_model.id,
            )
            self.db.add(self.retriever_db_model)
            self.db.commit()
    


    def _fit(self):
        """
        Fit the TF-IDF model to the documents.
        This method should be called after initializing the retriever.
        """
        # Load chunks from the documents
        chunk_texts = []
        current_chunk_idx = 0
        self.matrix_row_to_chunk_map = {}

        for doc_id, doc_chunks in self.chunks.items():
            for chunk_pos, chunk in doc_chunks.items():
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
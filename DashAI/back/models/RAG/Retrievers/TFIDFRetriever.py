import os
from .BaseRetriever import BaseRetriever
from DashAI.back.models.RAG.documents import BaseDocument, PDFDocument, TxtDocument
from typing import List, Dict, Any, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
import numpy as np
import hashlib
import pickle

from DashAI.back.core.schema_fields import (
    BaseSchema,
    schema_field,
    enum_field,
    float_field,
    int_field,
)

similarities = {
    "cosine": cosine_similarity,
    "euclidean": euclidean_distances
}


class TFIDFRetrieverSchema(BaseSchema):
    """
    Schema for the TFIDFRetriever.
    """

    similarity_function: schema_field(
        enum_field(['cosine', 'euclidean']),
        placeholder="cosine",
        description="Similarity function to use for document retrieval."
    )  # type: ignore

    n_docs: schema_field(
        int_field(ge=1),
        placeholder=5,
        description="Number of documents to retrieve."
    )  # type: ignore

    similarity_threshold: schema_field(
        float_field(),
        placeholder=0.5,
        description="Maximum or minimum distance for retrieved documents based on the similarity_function."
    )  # type: ignore

    chunk_size: schema_field(
        int_field(ge=1),
        placeholder=512,
        description="Size of chunks to split the documents into."
    )  # type: ignore

    chunk_overlap: schema_field(
        int_field(ge=0),
        placeholder=50,
        description="Overlap between chunks when splitting documents."
    )  # type: ignore

class TFIDFRetriever(BaseRetriever):
    """
    A retriever that uses TF-IDF to retrieve documents based on a query.
    """
    SCHEMA = TFIDFRetrieverSchema

    def __init__(
            self, 
            documents_paths: List[str],
            similarity_function: str,
            n_docs: int,
            similarity_threshold: float,
            chunk_size: int,
            chunk_overlap: int
            ):
        """
        Initialize the TFIDFRetriever with the given parameters.

        Args:
            documents_paths (List[str]): A list of document texts to be indexed.
            similarity_function (str): Similarity function to use ('cosine' or 'euclidean').
            n_docs (int): The maximum number of documents to retrieve.
            distance_threshold (float): The maximum or minimum distance for retrieved documents based on the similarity_function.
            chunk_size (int): The size of chunks to split the documents into.
            chunk_overlap (int): The overlap between chunks.
        """
        
        assert isinstance(documents_paths, list) and all(isinstance(doc, str) for doc in documents_paths), "Documents must be a list of strings."
        assert similarity_function in similarities, f"similarity_function must be one of {list(similarities.keys())}."
        assert n_docs > 0, "Number of documents to retrieve must be greater than 0."
        assert similarity_threshold >= 0, "Similarity threshold must be non-negative."
        assert chunk_size > 0, "Chunk size must be greater than 0."
        assert chunk_overlap >= 0, "Chunk overlap must be non-negative."
        assert chunk_size > chunk_overlap, "Chunk size must be greater than chunk overlap."
        BASE_DOC_PATH = 'THIS IS A PLACEHOLDER, should be unnecesary after implementing the document persistence storage in the database'
        new_documents_paths = []
        for doc_path in documents_paths:
            new_path = os.path.join(BASE_DOC_PATH, doc_path)
            new_documents_paths.append(new_path)
        documents_paths = new_documents_paths
        self._documents_paths = sorted(documents_paths) # Sort for consistent hashing
        self.similarity_function_name = similarity_function 
        self.similarity_function = similarities[similarity_function]
        self.n_docs = n_docs
        self.similarity_threshold = similarity_threshold
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.params = {
            "similarity_function_name": self.similarity_function_name,
            "similarity_function": self.similarity_function,
            "n_docs": n_docs,
            "similarity_threshold": similarity_threshold,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap
        }


        # Generate a unique hash for the current set of documents and chunking parameters
        self._cache_hash = self._generate_cache_hash()
        self._vectorizer_path, self._tf_idf_matrix, self.chunk_to_doc_path = self._get_cache_paths()


        # Attempt to load from cache
        if self._load_state():
            print(f"TFIDFRetriever loaded from cache: {self._cache_hash}")
        else:
            print(f"TFIDFRetriever cache not found or invalid for {self._cache_hash}. Fitting new model...")
            self._fit()
            self._save_state()

    def _get_cache_paths(self) -> tuple[str, str, str]:
        """
        Returns the file paths for the cached vectorizer, tfidf_matrix, and chunk_to_doc_id_map.
        """
        os.makedirs(self.RETRIEVERS_PATH, exist_ok=True) # Use BaseRetriever's constant
        base_name = os.path.join(self.RETRIEVERS_PATH, self._cache_hash)
        os.makedirs(base_name, exist_ok=True)
        vectorizer_path = os.path.join(base_name, "vectorizer")
        tfidf_matrix_path = os.path.join(base_name, "tfidf_matrix")
        map_path = os.path.join(base_name, "chunk_to_doc_id_map")
        return vectorizer_path, tfidf_matrix_path, map_path

    def get_hashable_parameters(self):
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
        }
    
    def _generate_cache_hash(self) -> str:
        hashable_params = self.get_hashable_parameters()
        text = f"{self._documents_paths}{hashable_params}"
        params_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        docs_hashes = []
        for doc_path in self._documents_paths:
            if doc_path.endswith('.pdf'):
                doc = PDFDocument(doc_path)
            elif doc_path.endswith('.txt'):
                doc = TxtDocument(doc_path)
            else:
                raise ValueError(f"Unsupported document type: {doc_path}")
    
            docs_hashes.append(doc.get_hash())
        docs_hash = hashlib.sha256("".join(docs_hashes).encode('utf-8')).hexdigest()
        return f"tfidf_retriever_{params_hash}_{docs_hash}"

    
    def _load_state(self) -> bool:
        """
        Load the retriever state from cache if available.
        
        Returns:
            bool: True if the state was successfully loaded, False otherwise.
        """
        if not os.path.exists(self._vectorizer_path):
            return False
        if not os.path.exists(self._tf_idf_matrix):
            return False
        if not os.path.exists(self.chunk_to_doc_path):
            return False
        
        try:
            self._vectorizer = pickle.load(open(self._vectorizer_path, 'rb'))
            self._tf_idf_matrix = pickle.load(open(self._tf_idf_matrix, 'rb'))
            self.chunk_to_doc_map = pickle.load(open(self.chunk_to_doc_path, 'rb'))
            return True
        except Exception as e:
            print(f"Error loading state: {e}")
            return False
        
    def _save_state(self):
        """
        Save the retriever state to cache.
        """
        try:
            pickle.dump(self._vectorizer, open(self._vectorizer_path, 'wb'))
            pickle.dump(self._tf_idf_matrix, open(self._tf_idf_matrix, 'wb'))
            pickle.dump(self.chunk_to_doc_map, open(self.chunk_to_doc_path, 'wb'))
        except Exception as e:
            print(f"Error saving state: {e}")

    def _fit(self):
        """
        Fit the TF-IDF model to the documents.
        This method should be called after initializing the retriever.
        """
        # Load chunks from the documents
        chunks = self.get_documents_chunks()
        chunk_texts = []
        current_chunk_idx = 0
        self.chunk_to_doc_map = {}

        for doc_path, doc_chunks in chunks.items():
            for i, chunk_text in enumerate(doc_chunks):
                chunk_texts.append(chunk_text)
                self.chunk_to_doc_map[current_chunk_idx] = (chunk_text, doc_path, i)
                current_chunk_idx += 1
            
        # Create the TF-IDF vectorizer and fit it to the chunks
        self._vectorizer = TfidfVectorizer()
        self._tf_idf_matrix = self._vectorizer.fit_transform(chunk_texts)
        self._save_state()

    def retrieve(self, query: str) -> List[Tuple[str, str, int]]:
        """
        Retrieve documents based on the query using TF-IDF.
        Args:
            query (str): The query string to search for.
        Returns:
            List[Tuple[str, str, int]]: A list of tuples containing the chunk text, document path, and chunk ID.
        """
        assert self._tf_idf_matrix is not None, "Model is not fitted. Call _fit() before retrieving."

        print(f"Retrieving documents for query: {query}")
        # Transform the query using the same vectorizer
        query_vector = self._vectorizer.transform([query])

        # Calculate the similarity scores
        similarities = self.similarity_function(query_vector, self._tf_idf_matrix).flatten()

        # Determine sorting order based on similarity_function
        if self.similarity_function == cosine_similarity:
            filtered_indices = np.where(similarities >= self.similarity_threshold)[0]
            ranked_indices = np.argsort(-similarities[filtered_indices])[:self.n_docs]
        
        elif self.similarity_function == euclidean_distances:
            filtered_indices = np.where(similarities <= self.similarity_threshold)[0]
            ranked_indices = np.argsort(similarities[filtered_indices])[:self.n_docs]

        else:
            raise ValueError(f"Unsupported similarity_function: {self.similarity_function}")
    
        # Get the top n_docs indices
        top_indices = ranked_indices[:self.n_docs]

        results: List[Tuple[str, str, int]] = []
        for idx in top_indices:
            results.append(self.chunk_to_doc_map[idx])

        return results
import os
from typing import List, Dict, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import hashlib
import pickle

from DashAI.back.core.schema_fields import (
    BaseSchema,
    list_field,
    schema_field,
    enum_field,
    float_field,
    int_field,
    bool_field,
    string_field,
    union_type,
    none_type
)

class BM25EncodingSchema(BaseSchema):

    strip_accents: schema_field(
        none_type(
            enum_field(
                enum=["ascii", "unicode"],
            )
        ),
        placeholder=None,
        description="""Remove accents and perform other character normalization during the preprocessing step. ‘ascii’ is a fast method that only works on characters that have a direct ASCII mapping. ‘unicode’ is a slightly slower method that works on any characters. None (default) means no character normalization is performed.""",
    ) # type: ignore

    lowercase: schema_field(
        bool_field(),
        placeholder=True,
        description="Whether to convert all characters to lowercase.",

    ) # type: ignore



    stop_words: schema_field(
        list_field(
            string_field(),
            min_items=1,
        ),
        placeholder=None,
        description="List of stop words to be used in the TF-IDF vectorization.",
    ) # type: ignore

    max_df: schema_field(
        float_field(
            ge=0.0,
            le=1.0,
        ),
        placeholder=1.0,
        description="When building the vocabulary ignore terms that have a document frequency strictly higher than the given threshold (corpus-specific stop words).",
    ) # type: ignore

    min_df: schema_field(
        float_field(
            ge=0.0,
            le=1.0,
        ),
        placeholder=1.0,
        description="When building the vocabulary ignore terms that have a document frequency strictly lower than the given threshold (corpus-specific stop words).",
    ) # type: ignore

    max_features: schema_field(

        int_field(
            ge=1,
        ),
        placeholder=None,
        description="If not None, build a vocabulary that only consider the top max_features ordered by term frequency across the corpus.",
    ) # type: ignore


class BM25Encoding:
    """
    BM25 encoding (embedding) model for text documents.
    This class implements the precomputation of BM25 scores for text documents.
    """

    def __init__(
            self, 
            documents_chunks: Dict[int, List[str]],
            k: float,
            b: float,
            delta: float,
            strip_accents: str,
            lowercase: bool,
            analyzer: str,
            stop_words: List[str],
            max_df: float,
            min_df: float,
            max_features: int,
            store_model: bool = True
    ) -> None:
        """
        Initialize the BM25 encoding model with the given document chunks.

        Args:
            documents_chunks (Dict[int, List[str]]): A dictionary where keys are document IDs and values are lists of text chunks.
        """
        # sort chunks by document ID to ensure consistency
        documents_chunks = dict(sorted(documents_chunks.items()))

        chunks_mapping = {}
        chunks_texts = []
        n_chunks = 0
        for doc_id, chunks in documents_chunks.items():
            for chunk_text in chunks:
                chunks_texts.append(chunk_text)
                chunks_mapping[n_chunks] = (doc_id, chunk_text)
                n_chunks += 1

        self.chunks_texts = chunks_texts
        self.chunks_mapping = chunks_mapping
        self.strip_accents = strip_accents
        self.lowercase = lowercase
        self.analyzer = analyzer
        self.stop_words = stop_words
        self.max_df = max_df
        self.min_df = min_df
        self.max_features = max_features

        self.hyperparameters = {
            "k": k,
            "b": b,
            "delta": delta,
            "strip_accents": strip_accents,
            "lowercase": lowercase,
            "analyzer": analyzer,
            "stop_words": stop_words,
            "max_df": max_df,
            "min_df": min_df,
            "max_features": max_features,
        }

        load_success = self._load_model()
        print(f"BM25 model loaded successfully: {load_success}")
        if not load_success:
            print("Fitting the BM25 model...")
            self._fit_model()
            if store_model:
                print("Saving the BM25 model...")
                self._save_model()
            print("BM25 model fitted and saved.")

    def _hash_function(self, input_string: str) -> str:
        """
        Generate a SHA-256 hash for the given input string.
        
        Args:
            input_string (str): The input string to hash.
        
        Returns:
            str: The SHA-256 hash of the input string.
        """
        return hashlib.sha256(input_string.encode('utf-8')).hexdigest()
    
    def _get_encoding_signature(self) -> str:
        """
        Generate a hash to identify the encoding (embeddings) for caching purposes.

        Hash is calculated over the documents' content to ensure consistency in encoding (embeddings), it must:
        - Be consistent across runs with the same documents content, chunking strategy and encoding (embeddings) model parameters.
        - Change if the documents are modified.
        - Change if the documents content is modified.
        - Change if the chunking strategy is modified.
        - Change if the encoding (embeddings) model parameters are modified.
k
        Returns:
            str: A hash string representing the encoding (embeddings).
        """
        params_hash = self._hash_function(str(self.hyperparameters))
        documents_chunks_hash = self._hash_function(str(self.chunks_mapping))
        return self._hash_function(params_hash + documents_chunks_hash)

    def _fit_model(self) -> None:
        """
        Fit the TF-IDF model to the document chunks.
        This method initializes the TF-IDF vectorizer and fits it to the document chunks.
        """
        self.vectorizer = TfidfVectorizer(
            strip_accents=self.strip_accents,
            lowercase=self.lowercase,
            analyzer=self.analyzer,
            stop_words=self.stop_words,
            ngram_range=tuple(self.ngram_range),
            max_df=self.max_df,
            min_df=self.min_df,
            max_features=self.max_features,
            
            norm=None,
            smooth_idf=False,
            sublinear_tf=False,
            use_idf=False,
        )

        tf_matrix = self.vectorizer.fit_transform(self.chunks_texts)
        document_lengths = tf_matrix.sum(axis=1)
        idf = np.log(tf_matrix.shape[0] / document_lengths)

        tf_matrix = tf_matrix.multiply(self.k + 1) / (tf_matrix + self.k * (1 - self.b + self.b * document_lengths))
        tf_matrix = tf_matrix.multiply(idf.reshape(-1, 1))

    def _get_model_paths(self) -> Tuple[str, str, str, str]:
        """
        Get the paths for saving the model components.
        Returns a tuple containing the folder path, vectorizer path, term matrix path, and feature names path.
        """
        folder_path = os.path.join(
            self.EMBEDDINGS_PATH,
            self._get_encoding_signature()
        )
        
        vectorizer_path = os.path.join(folder_path, "vectorizer.pkl")
        tf_matrix_path = os.path.join(folder_path, "tf_matrix.pkl")
        
        return folder_path, vectorizer_path, tf_matrix_path

    def _save_model(self) -> None:
        """
        Save the model components to disk.
        This method saves the vectorizer, term matrix, and feature names to their respective files.
        """

        folder_path, vectorizer_path, tf_matrix_path = self._get_model_paths()

        # Create the folder if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)

        with open(vectorizer_path, 'wb') as f:
            pickle.dump(self.vectorizer, f)

        with open(tf_matrix_path, 'wb') as f:
            pickle.dump(self._tf_matrix, f)

    def _load_model(self) -> bool:
        """
        Try to load the model components from disk.
        If the model components are not found, return False.
        If the model components are found, load them into the instance variables and return True.
        """
        folder_path, vectorizer_path, tf_matrix_path = self._get_model_paths()
        if not (
            os.path.exists(vectorizer_path) and
            os.path.exists(tf_matrix_path)):
            return False

        # Load the vectorizer
        with open(vectorizer_path, 'rb') as f:
            self.vectorizer = pickle.load(f)

        # Load the term matrix
        with open(tf_matrix_path, 'rb') as f:
            self._tf_matrix = pickle.load(f)

        self._document_lengths = self._tf_matrix.sum(axis=1)
        self._average_document_length = np.mean(self._document_lengths)
        self._idf = np.log(self._tf_matrix.shape[0] / self._document_lengths)

        return True

    def get_documents_chunks_encodings(self) -> Dict[int, List[np.ndarray]]:
        """
        Get the encodings (embeddings) for each document chunk.
        
        Returns:
            Dict[int, List[np.ndarray]]: A dictionary where keys are document IDs and values are lists of encodings (embeddings) for each chunk.
        """
        if not hasattr(self, 'vectorizer'):
            raise RuntimeError("The model has not been fitted yet. Call _fit_model() before getting encodings (embeddings).")
        
        encodings = self._tf_matrix.toarray()
        n_chunks = encodings.shape[0]

        # Map the encodings back to the document IDs using the chunks_mapping
        documents_chunks_encodings = {}
        for i in range(n_chunks):
            doc_id, _ = self.chunks_mapping[i]
            if doc_id not in documents_chunks_encodings:
                documents_chunks_encodings[doc_id] = []
            documents_chunks_encodings[doc_id].append(encodings[i])

        return documents_chunks_encodings

    def encode(self, text: str) -> List[float]:
        """
        Generate TF-IDF encodings (embeddings) for the given text.

        Args:
            text (str): The input text to embed.
        
        Returns:
            List[float]: A list representing the TF-IDF encodings (embeddings) of the input text.
        """
        if not hasattr(self, 'vectorizer'):
            raise RuntimeError("The model has not been fitted yet. Call _fit_model() before encoding (embedding) text.")
        
        # Transform the input text to get its TF-IDF representation
        tfidf_vector = self.vectorizer.transform([text])
        return tfidf_vector.toarray()
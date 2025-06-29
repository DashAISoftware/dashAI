#from chromadb import EmbeddingFunction, Embeddings
from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
import os

class TfidfEmbeddingFunction:#(EmbeddingFunction):
    """A dummy embedding function using TF-IDF."""
    def __init__(self, corpus: List[str], collection_name: str = None):
        if collection_name:
            stored_path = os.path.join(os.getcwd(), "saved_encoders", "tfidf", collection_name)
        
            if os.path.exists(stored_path):
                with open(stored_path, "rb") as f:
                    self.vectorizer = pickle.load(f)
                    return
                
        self.vectorizer = TfidfVectorizer()
        self.vectorizer.fit(corpus)

        if collection_name:
            os.makedirs(os.path.dirname(stored_path), exist_ok=True)
            with open(stored_path, "wb") as f:
                pickle.dump(self.vectorizer, f)

    def __call__(self, texts: List[str]):# -> Embeddings:
        """Transform the texts into TF-IDF embeddings."""
        return self.vectorizer.transform(texts).toarray().tolist()
    
    @staticmethod
    def name() -> str:
        return "default"
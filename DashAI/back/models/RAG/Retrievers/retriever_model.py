from abc import ABC
import os
from typing import Any, Dict, List, Final
from DashAI.back.models.RAG.documents import BaseDocument, PDFDocument, TxtDocument
import hashlib

from DashAI.back.models.base_model import BaseModel

SUPPORTED_DOCUMENT_TYPES = ['pdf', 'txt']

class RetrieverModel(BaseModel):
    """
    Abstract class to define the interface for retriever models.
    """

    RETRIEVERS_PATH = "./StoredRetrievers"
    COMPATIBLE_COMPONENTS = ["RAGTask"]


    def _load_document(self, document_path: str) -> BaseDocument:
        """
        Load a document from the specified path.
        
        Args:
            document_path (str): The path to the document file.
        
        Returns:
            BaseDocument: An instance of a document class (PDFDocument or TxtDocument).
        """
        if document_path.endswith('.pdf'):
            return PDFDocument(document_path)
        elif document_path.endswith('.txt'):
            return TxtDocument(document_path)
        else:
            raise ValueError(f"Unsupported document type: {document_path}")
        
    def get_documents(self) -> Dict[str, BaseDocument]:
        """
        Get the documents stored in the retriever.
        Returns:
            Dict[str, BaseDocument]: A dictionary where keys are document paths and values are document instances.
        """
        assert self._documents_paths is not None, "Document paths must be provided."
        assert len(self._documents_paths) > 0, "At least one document path must be provided."
        
        self._documents_paths = sorted(self._documents_paths)  # Sort for consistent hashing in signature
        documents = {}
        for path in self._documents_paths:
            doc = self._load_document(path)
            documents[path] = doc
        return documents
    
    def get_documents_chunks(self) -> Dict[str, List[str]]:
        """
        Get the chunks of documents stored in the retriever.

        Returns:
            Dict[str, Dict[int, str]]: A dictionary where keys are document paths and values are
            dictionaries of chunk indices and their corresponding text.
        """
        documents = self.get_documents()
        chunks = {}
        for filename, doc in documents.items():
            chunks[filename] = doc.get_chunks(self.chunk_size, self.chunk_overlap)
        return chunks
    
    def get_parameters(self) -> Dict[str, Any]:
        """
        Get the parameters of the retriever.
        
        Returns:
            Dict[str, Any]: A dictionary of retriever parameters.
        """
        assert self.params is not None, "Retriever parameters are not set."
        return self.params
    
    def get_signature_parameters(self) -> Dict[str, Any]:
        """
        Get the parameters used for storing the fitted retriever in the database.
        This parameters are a subset of the retriever parameters, the non-signature parameters are
        those whose change does not require a retraining of the retriever, i.e. n_docs, 
        max_distance, etc.
        
        Returns:
            Dict[str, Any]: A dictionary of parameters that can be used for hashing.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
    
    def _get_documents_signature(self) -> str:
        """
        Generate a hash representing the current set of documents.

        Returns:
            str: A hash string representing the documents.
        """
        documents = sorted(self.get_documents().items())
        hashes = ""
        for filename, doc in documents.items():
            doc_hash = doc.get_hash()
            hashes += f"{filename}{doc_hash}"
        return hashlib.sha256(hashes.encode('utf-8')).hexdigest()
    
    def _get_parameters_signature(self) -> str:
        """
        Generate a hash representing the retriever parameters.

        Args:
            parameters (Dict[str, Any]): A dictionary of retriever parameters.

        Returns:
            str: A hash string representing the parameters.
        """
        hashable_parameters = sorted(self.get_signature_parameters().items())
        params_string = "".join(f"{key}{value}" for key, value in hashable_parameters)
        return hashlib.sha256(params_string.encode('utf-8')).hexdigest()

    def _get_model_signature(self) -> str:
        """
        Generate a unique hash for the retriever based on its documents and parameters.

        Returns:
            str: A hash string representing the retriever's state.
        """
        documents_hash = self._get_documents_signature()
        parameters_hash = self._get_parameters_signature()
        return f"{self.__class__.__name__}_{documents_hash}_{parameters_hash}"

    def add_document(self, document: BaseDocument) -> None:
        """
        Add a document to the retriever.
        
        Args:
            document (BaseDocument): The document to add.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
    
    def remove_document(self, document_id: str) -> None:
        """
        Remove a document from the retriever by its ID.
        
        Args:
            document_id (str): The ID of the document to remove.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
    
    def retrieve(self, **kwargs) -> List[BaseDocument]:
        """
        Retrieve documents based on the provided parameters.
        
        Args:
            **kwargs: The parameters for the retrieval.
        
        Returns:
            List[BaseDocument]: A list of retrieved documents.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

    def validate_documents_in_folder(self, documents: List[BaseDocument]) -> bool:
        """
        Validate that the provided documents exist in their specified paths.

        Args:
            documents (List[BaseDocument]): A list of documents to validate.

        Returns:
            bool: True if all specified documents are present in the folder, False otherwise.
        """
        for doc in documents:
            if not os.path.exists(doc.file_path):
                print(f"Document {doc.file_path} is missing.")
                return False
        return True
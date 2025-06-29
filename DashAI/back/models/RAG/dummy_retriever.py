import os
#import chromadb
#from chromadb import Settings
from typing import List, Dict
from pypdf import PdfReader
from DashAI.back.models.RAG.encodings.tf_idf_encoding import TfidfEmbeddingFunction
from DashAI.back.models.RAG.text_splitter import TextSplitter
from DashAI.back.models.RAG.text_preprocessor import TextPreprocessor

def directory_has_documents(directory: str) -> bool:
    """Check if the directory contains any documents."""
    for filename in os.listdir(directory):
        if filename.endswith(".txt") or filename.endswith(".pdf"):
            return True
    return False
        
class DummyRetriever:
    """A dummy retriever using ChromaDB."""

    def __init__(
            self, 
            documents_path: str,
            collection_name: str, 
            distance_function: str, 
            n_docs: int, 
            max_distance: float,
            chunk_size: int,
            chunk_overlap: int
            ):
        """
        Initialize the DummyRetriever with dummy parameters.

        Args:
            collection_name (str): The name of the collection.
            distance_function (str): The distance function to use (e.g., "cosine", "euclidean").
            n_docs (int): The maximum number of documents to retrieve.
            max_distance (float): The maximum distance allowed for retrieved documents.
        """
        assert os.path.exists(documents_path), f"Documents path {documents_path} does not exist."
        assert directory_has_documents(documents_path), f"No txt or pdf documents found in {documents_path}."
        assert collection_name, "Collection name cannot be empty."
        assert distance_function in ["cosine", "L2", "inner"], "Invalid distance function. Choose 'cosine', 'L2', or 'inner'."
        assert n_docs > 0, "Number of documents must be greater than 0."
        assert max_distance > 0, "Max distance must be greater than 0."
        assert chunk_size > 0, "Chunk size must be greater than 0."
        assert chunk_overlap >= 0, "Chunk overlap must be greater than or equal to 0."

        self.documents_path = documents_path
        self.collection_name = collection_name.lower().strip().replace(" ", "_")
        self.distance_function = distance_function
        self.n_docs = n_docs
        self.max_distance = max_distance
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.collection = None #chromadb.Collection = None
        self.embedding = TfidfEmbeddingFunction(
            corpus=self.load_documents().values(),
            collection_name=self.collection_name,
            )
    
        print("Initializing ChromaDB storage")
        self.__init_chromadb__()

    def __init_chromadb__(self):
        """
        Initialize the ChromaDB storage
        if the collection already exists, it will be loaded.

        """
        print("Initializing ChromaDB client")
        client = None
        return
        """ chromadb.PersistentClient(
            settings=Settings(
                anonymized_telemetry=False,
                )) """

        print("Initializing ChromaDB collection")
        stored_collections = client.list_collections()
        stored_collections_names = [collection.name for collection in stored_collections]
        if self.collection_name in stored_collections_names:
            print(f"Collection {self.collection_name} already exists. Loading existing collection.")
            self.collection = client.get_collection(name=self.collection_name)
        else:
            print(f"Collection {self.collection_name} does not exist. Creating a new collection.")
            # Create a new collection with the specified embedding function
            self.collection = client.create_collection(
                name=self.collection_name,
                configuration={
                    "embedding_function": self.embedding.name(),
                },  
                embedding_function=self.embedding,
                metadata={
                    "distance_function": self.distance_function,
                },
            )
        print(f"Collection {self.collection_name} initialized with distance function {self.distance_function}.")

        documents = self.load_documents()
        self.add_documents_to_collection(documents)
            
    def parse_txt_file(self, file_path: str):
        """Parse a txt file and return its content."""
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        content = TextPreprocessor.preprocess_text(content)
        return content
    
    def parse_pdf_file(self, file_path: str):
        """Parse a pdf file and return its content."""
        with open(file_path, "rb") as file:
            reader = PdfReader(file)
            content = ""
            for page in reader.pages:
                content += page.extract_text()
        content = TextPreprocessor.preprocess_text(content)
        return content
    
    def load_documents(self)-> Dict[str, str]:
        """Load txt documents from the specified path."""

        documents = {}
        for filename in os.listdir(self.documents_path):
            file_path = os.path.join(self.documents_path, filename)
            if filename.endswith(".txt"):
                content = self.parse_txt_file(file_path)

            elif filename.endswith(".pdf"):
                content = self.parse_pdf_file(file_path)
            
            else:
                continue

            if len(content) > 0:
                documents[filename] = content
            else:
                print(f"File {filename} is empty or not valid. Skipping.")
                continue

        return documents
    
    def add_documents_to_collection(self, documents: Dict[str, str]):
        """
        Add documents to the ChromaDB collection.
        Args:
            documents (Dict[str, str]): A dictionary of documents with filenames as keys and content as values.
        """ 
        print(f"Adding {len(documents)} documents to the collection.")
        text_splitter = TextSplitter(self.chunk_size, self.chunk_overlap)
        splitted_documents = text_splitter.split_documents_texts(documents)
        print(f"Splitting documents into {len(splitted_documents)} chunks.")

        for i, (filename, chunk_index, chunk_text) in enumerate(splitted_documents):
            embedding = self.embedding([chunk_text])[0]
            try:
                print(f"Adding document {i+1}/{len(splitted_documents)}: {filename} chunk {chunk_index}")
                self.collection.add(
                    documents=chunk_text,
                    metadatas={"filename": filename, "chunk_index": chunk_index},
                    embeddings=embedding,
                    ids=f"{filename}_{chunk_index}",
                    )
            except Exception as e:
                print(f"Error adding document {filename} chunk {chunk_index}: {e}")
                continue
                
        print(f"Added {len(documents)} documents and {len(splitted_documents)} chunks to the collection.")

    def retrieve(self, query_texts: List[str], n_docs: int = None)-> Dict[str, str]:
        """
        Retrieve documents based on the query.

        Args:
            query_texts (List[str]): The query strings.
            n_docs (int): The number of documents to retrieve.

        Returns:
            list: A list of retrieved documents.
        """
        if n_docs is None:
            n_docs = self.n_docs
        
        results = self.collection.query(
            query_embeddings=self.embedding(query_texts),
            n_results= n_docs*len(query_texts),
            include=["documents", "metadatas", "distances"]
        )

        retrieved_documents = {}    
        for query_text, query_docs, query_metadatas, query_distances in zip(query_texts, results["documents"], results["metadatas"], results["distances"]):
            for doc, metadata, distance in zip(query_docs, query_metadatas, query_distances):
                if distance <= self.max_distance:
                    docname = metadata["filename"]+"_chunk_"+str(metadata["chunk_index"])
                    retrieved_documents[docname] = doc
                
        return retrieved_documents
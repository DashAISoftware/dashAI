from typing import Any, Tuple, List, Dict

from DashAI.back.core.schema_fields import (
    BaseSchema,
    component_field,
    schema_field,
    list_field,
    string_field
)

from DashAI.back.models.base_generative_model import BaseGenerativeModel
from DashAI.back.models.text_to_text_generation_model import TextToTextGenerationTaskModel
from DashAI.back.models.RAG.Retrievers import (
    TFIDFRetriever,
    DenseRetriever,
    RetrieverModel)

from DashAI.back.models.RAG.prompts import (
    ContextMergePrompt,
    AugmentationPrompt
)

from DashAI.back.models.hugging_face import (
    DeepSeekModel,
    QwenModel,
    GemmaModel)

retriever_models = {
    "TFIDFRetriever": TFIDFRetriever,
    "DenseRetriever": DenseRetriever,
}

generation_models = {
    "DeepSeekModel": DeepSeekModel,
    "QwenModel": QwenModel,
    "GemmaModel": GemmaModel,
}

class RAGPipelineSchema(BaseSchema):
    """Schema for RAG pipeline."""
    # Document collection parameters
    documents: schema_field(
        list_field(
            string_field(),
            min_items=1,
        ),
        placeholder=None,
        description="List of documents to be used in the RAG pipeline."
    ) # type: ignore

    chunking_model: schema_field(
        component_field(
            parent="BaseChunkingModel"),
        description="Chunking model used to split documents into smaller pieces.",
        placeholder={
            "component": "CharacterChunkModel",
            "params": {}
            }
        ) # type: ignore

    # RAG algorithm parameters
    retriever_model: schema_field(
        component_field(parent="RetrieverModel"),
        placeholder={"component": "TFIDFRetriever", "params": {}},
        description="Retriever component used in the RAG pipeline."
    ) # type: ignore

    generation_model: schema_field(
        component_field(parent="TextToTextGenerationTaskModel"),
        placeholder={"component": "DeepSeek", "params": {}},
        description="Text generation model used in the RAG pipeline."
    ) # type: ignore

class RAGPipeline(BaseGenerativeModel):
    """Retrieval-Augmented Generation (RAG) pipeline."""
    
    COMPATIBLE_COMPONENTS = ["RAGTask"]

    SCHEMA = RAGPipelineSchema

    def __init__(   self, 
                    **kwargs):
        """
        Initialize the DummyRetrieverModel with dummy parameters.

        Args:
            distance_function (str): The distance function to use (e.g., "cosine", "euclidean").
            n_docs (int): The maximum number of documents to retrieve.
            max_distance (float): The maximum distance allowed for retrieved documents.
        """
        print("Initializing RAG pipeline")
        try:
            documents_paths = kwargs['documents']
            retriever_args = kwargs['retriever_model']
            generation_model_args = kwargs['generation_model']
        except KeyError as e:
            raise ValueError(f"Missing required RAG pipeline parameter: {e}")
        
        try:
            retriever_model_class = retriever_models[retriever_args["component"]]
            retriever_params = retriever_args['params']
        except KeyError as e:
            raise ValueError(f"Invalid retriever model specified: {e}")
        
        try:
            generation_model_class = generation_models[generation_model_args["component"]]
            generation_params = generation_model_args['params']

        except KeyError as e:
            raise ValueError(f"Invalid generation model specified: {e}")
        
        assert isinstance(documents_paths, list) and len(documents_paths) > 0, "Documents must be a non-empty list."
        for path in documents_paths:
            assert isinstance(path, str), f"Each document path must be a string, got {type(path)}"

        print("Initializing LLM model")
        self.llm_model: TextToTextGenerationTaskModel = generation_model_class(**generation_params)


        new_retriever_args = {
            'documents_paths': documents_paths,
        }
        for key, value in retriever_params.items():
            new_retriever_args[key] = value

        print("Initializing retriever model")
        self.retriever: RetrieverModel = retriever_model_class(**new_retriever_args)

        self.retrieval_algorithm = "SINGLE_INTERACTION"
        print("RAG pipeline initialized")


    def single_interaction(self, input: str, history: List[Tuple[str, str]] = None) -> List[Tuple[str, str, int]]:
        """
        Single interaction retrieval algorithm: input -> retrieve documents.
        Args:
            input (str): The input query.
        Returns:
            str: The generated response.
        """

        documents = self.retriever.retrieve(input)

        return documents
        
    
    def augmented_interaction(self, input: str, history: List[Tuple[str, str]] = None) -> List[Tuple[str, str, int]]:
        """
        Augmented interaction RAG algorithm: input -> generate lookup tokens -> retrieve documents -> generate response.
        Args:
            input (str): The input query.
        Returns:
            str: The generated response.
        """
        augmentation_prompt = AugmentationPrompt.format(
            input=input,
            history=history,
            n_seach_terms=5
        )
        augementation_response = self.llm_model.generate(augmentation_prompt)[0]
        print(f"Augmentation response: {augementation_response}")
        search_terms = augementation_response.split("keywords:")[1].strip()
        search_terms = search_terms.split(",")
        if len(search_terms) > 5:
            search_terms = search_terms[:5]
        print(f"Augmentation search terms: {search_terms}")
        search_terms = [term.strip() for term in search_terms]

        documents = self.retriever.retrieve(search_terms)
        
        return documents
    
    def generate(self, input: Tuple[str, List[Tuple[str,str]]]) -> str:
        """
        Generate a response based on the input and the retrieved documents.
        Args:
        input: a tuple containing the input query and the conversation history.
            input (str): The input query.
            history (List[Tuple[str, str]]): The conversation history.
        Returns:
            str: The generated response.
        """
        message = input

        documents = self.single_interaction(message)
        documents_str = "RETRIEVED INFORMATION:\n\n"
        for doc_content, doc_file, chunk in documents:
            doc_name = doc_file.split("/")[-1]
            documents_str += f"Document '{doc_name}' in chunk: {chunk}:\n{doc_content}\n\n"

        prompt = ContextMergePrompt.format(
            input=message,
            history=None,
            documents=documents_str
        )

        print(f"Prompt: {prompt}")

        response = self.llm_model.generate(prompt)

        response = f"{response[0]}\n\nSources:{documents_str}"

        return [response]

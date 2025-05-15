from typing import Any, Tuple, List

from DashAI.back.models.base_generative_model import BaseGenerativeModel

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    float_field,
    schema_field,
    string_field
)

from DashAI.back.models.hugging_face.deep_seek_model import DeepSeekModel
from DashAI.back.models.hugging_face.qwen_model import QwenModel
from DashAI.back.models.llm_generation_model import LLMGenerationModel
from DashAI.back.models.RAG.dummy_retriever import DummyRetriever
from DashAI.back.models.RAG.prompts import (
    BasePrompt,
    ContextMergePrompt,
    AugmentationPrompt
)
from typing import Dict

class RAGPipelineSchema(BaseSchema):
    """Schema for RAG pipeline."""

    # RAG algorithm parameters
    RAG_algorithm: schema_field(
        enum_field(["SINGLE_INTERACTION", "AUGMENTED_INTERACTION"]),
        placeholder="SINGLE_INTERACTION",
        description="RAG algorithm to use for document retrieval and text generation.",
    )  # type: ignore


    # Retriever parameters 
    documments_path: schema_field(
        string_field(),
        placeholder="Path to the folder with documents",
        description="Path to the folder containing documents for retrieval.",
    )  # type: ignore

    collection_name: schema_field(
        string_field(),
        placeholder="My documents collection name",
        description="Name of the collection to use for document retrieval.",
    )  # type: ignore
        

    distance_function: schema_field(
        enum_field(["cosine", "L2", "inner"]),
        placeholder="cosine",
        description="Distance function to use for document retrieval.",
    )  # type: ignore

    n_docs: schema_field(
        int_field(ge=1),
        placeholder=5,
        description="Maximum number of documents to retrieve.",
    )  # type: ignore

    max_distance: schema_field(
        float_field(ge=0.0),
        placeholder=1.0,
        description="Maximum distance allowed for retrieved documents.",
    )  # type: ignore

    chunk_size: schema_field(
        int_field(ge=1),
        placeholder=1000,
        description="Size of the chunks to split the documents into.",
    )  # type: ignore

    chunk_overlap: schema_field(
        int_field(ge=0),
        placeholder=200,
        description="Overlap size between chunks.",
    )  # type: ignore


    # LLM parameters
    model_name: schema_field(
        enum_field(["DeepSeek", "Qwen2"]),
        placeholder="DeepSeek",
        description="LLM model to use for text generation.",
    )  # type: ignore

    max_tokens: schema_field(
        int_field(ge=1),
        placeholder=800,
        description="Maximum number of tokens to generate.",
    )  # type: ignore   

    temperature: schema_field(
        float_field(ge=0.0, le=1.0),
        placeholder=0.7,
        description="Sampling temperature. Higher values make the output more random, while lower values make it more focused and deterministic.",
    )  # type: ignore

    frequency_penalty: schema_field(
        float_field(ge=0.0, le=2.0),
        placeholder=0.1,
        description="Penalty for repeated tokens in the output. Higher values reduce the likelihood of repetition, encouraging more diverse text generation.",
    )  # type: ignore

    n_ctx: schema_field(
        int_field(ge=1),
        placeholder=4096,
        description="Maximum number of tokens the model can process in a single forward pass (context window size).",
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
        # Initialize the LLM model
        llm_classes = {
            "DeepSeek": DeepSeekModel,
            "Qwen2": QwenModel,
        }

        llm_kwargs = {
            "max_tokens": kwargs.get("max_tokens"),
            "temperature": kwargs.get("temperature"),
            "frequency_penalty": kwargs.get("frequency_penalty"),
            "n_ctx": kwargs.get("n_ctx"),
        }

        print("Initializing LLM model")
        self.llm_model: LLMGenerationModel = llm_classes[kwargs.get("model_name")](**llm_kwargs)

        # Initialize the retriever
        retriever_params = {
            "documents_path": kwargs.get("documments_path"),
            "collection_name": kwargs.get("collection_name"),
            "distance_function": kwargs.get("distance_function"),
            "n_docs": kwargs.get("n_docs"),
            "max_distance": kwargs.get("max_distance"),
            "chunk_size": kwargs.get("chunk_size"),
            "chunk_overlap": kwargs.get("chunk_overlap"),
        }

        print("Initializing retriever")
        self.retriever = DummyRetriever(**retriever_params)

        print("Definining rag algorithm")
        # Initialize the RAG algorithm
        if kwargs.get("RAG_algorithm") == "SINGLE_INTERACTION":
            self.retrieval_algorithm = self.single_interaction
        elif kwargs.get("RAG_algorithm") == "AUGMENTED_INTERACTION":
            self.retrieval_algorithm = self.augmented_interaction
        else:
            raise ValueError("Invalid RAG algorithm. Choose 'SINGLE_INTERACTION' or 'AUGMENTED_INTERACTION'.")
        print("RAG pipeline initialized")

    def single_interaction(self, input: str, history: List[Tuple[str, str]] = None) -> Dict[str, str]:
        """
        Single interaction retrieval algorithm: input -> retrieve documents.
        Args:
            input (str): The input query.
        Returns:
            str: The generated response.
        """

        documents = self.retriever.retrieve([input])

        return documents
        
    
    def augmented_interaction(self, input: str, history: List[Tuple[str, str]] = None) -> Dict[str, str]:
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
        message, history = input

        documents = self.retrieval_algorithm(message, history)
        documents_str = "\n\n".join([f"Document {name}:\n {content}" for name, content in documents.items()])

        prompt = ContextMergePrompt.format(
            input=message,
            history=history,
            documents=documents_str
        )

        print(f"Prompt: {prompt}")

        response = self.llm_model.generate(prompt)

        sources_str = ", ".join(doc_name for doc_name in documents.keys())
        response = f"{response[0]}\n\nSources:{sources_str}"

        return [response]

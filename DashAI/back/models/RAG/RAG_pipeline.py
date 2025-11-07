from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from DashAI.back.core.schema_fields import (
    BaseSchema,
    component_field,
    int_field,
    schema_field,
    list_field,
    string_field
)

from DashAI.back.dependencies.database.models import (
    Document as DBDocument,
    RAGPipeline as DBPipeline,
    RAGPrompt as PromptDBModel
    )

from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.base_generative_model import BaseGenerativeModel
from DashAI.back.models.text_to_text_generation_model import TextToTextGenerationTaskModel
from DashAI.back.models.RAG.chunking_models.base_chunking_model import BaseChunkingModel
from DashAI.back.models.RAG.chunking_models.chunking_models_factory import ChunkingModelsFactory
from DashAI.back.models.RAG.prompts import Prompt, DefaultGenerationPrompt, DefaultAugmentationPrompt
from DashAI.back.models.RAG.retrievers.retriever_model import RetrieverModel
from DashAI.back.models.RAG.retrievers.retriever_models_factory import RetrieverModelsFactory

from DashAI.back.models.RAG.documents import (
    BaseDocument,
    TxtDocument,
    PDFDocument,
    Chunk
)
documents_models: Dict[str, BaseDocument] = {
    "txt": TxtDocument,
    "pdf": PDFDocument,
}


class RAGPipelineParametersError(Exception):
    """Custom exception for invalid RAG pipeline parameters."""

    def __init__(self, message: str):
        super().__init__(message)

class RAGPipelineInitializationError(Exception):
    """Custom exception for errors during RAG pipeline initialization."""

    def __init__(self, message: str):
        super().__init__(message)

class RAGPipelineRuntimeError(Exception):
    """Custom exception for errors during RAG pipeline execution."""

    def __init__(self, message: str):
        super().__init__(message)

class RAGDatabaseError(Exception):
    """Custom exception for database-related errors in RAG pipeline."""

    def __init__(self, message: str):
        super().__init__(message)

class RAGPipelineSchema(BaseSchema):
    """Schema for RAG pipeline."""
    # Document collection parameters
    documents: schema_field(
        list_field(
            int_field(gt=0)
        ),
        placeholder=None,
        description="List of documents ids to be used in the RAG pipeline."
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

    prompt_id: schema_field(
        int_field(gt=0),
        placeholder=None,
        description="Database ID of the prompt template to be used in the RAG pipeline."
    ) # type: ignore

class RAGPipeline(BaseGenerativeModel):
    """Retrieval-Augmented Generation (RAG) pipeline.
    
    A pipeline that combines document retrieval with text generation to produce
    contextually informed responses. The pipeline processes input through several stages:
    1. Document loading and chunking
    2. Information retrieval
    3. Context-aware text generation
    """
    
    COMPATIBLE_COMPONENTS = ["RAGTask"]
    SCHEMA = RAGPipelineSchema

    session_id: int = None
    documents: Dict[int, BaseDocument]
    chunking_model: BaseChunkingModel
    chunking_model_id: int
    chunks: Dict[int, Dict[int, Chunk]]
    retriever: RetrieverModel
    llm_model: TextToTextGenerationTaskModel
    retrieval_algorithm: str

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the RAG pipeline with the specified components and configuration.

        Args:
            kwargs: Configuration dictionary containing:
                documents (List[int]): List of document IDs to use
                chunking_model (dict): Configuration for the document chunking model
                retriever_model (dict): Configuration for the retrieval model
                generation_model (dict): Configuration for the text generation model
                prompt_model (dict): Configuration for the prompt template
                db (Session): Database session for document retrieval

        Raises:
            RAGPipelineParametersError: If the configuration parameters are invalid
            RAGPipelineInitializationError: If any component fails to initialize
        """
        print("Initializing RAG pipeline")
        self.session_id: int = kwargs.pop("session_id")
        self.db: Session = kwargs.pop("db")
        self.component_registry: ComponentRegistry = kwargs.pop("component_registry")
        self.env_rag_path: str = kwargs.pop("env_rag_path")

        pipeline_db_model: DBPipeline = self.db.query(DBPipeline).filter_by(session_id=self.session_id).first()
        if pipeline_db_model:
            self.pipeline_db_model = pipeline_db_model
            self.pipeline_id = pipeline_db_model.id
        else:
            self.pipeline_db_model = None
            self.pipeline_id = None
        
        self.documents_ids: List[int] = kwargs.pop("documents")
        self.documents = self.load_documents_from_db(documents_ids=self.documents_ids)
        
        self.prompt_db_id: int = kwargs.pop("prompt_id")
        prompt_db_model: PromptDBModel = self.db.query(PromptDBModel).filter_by(id=self.prompt_db_id).first()
        if not prompt_db_model:
            raise RAGPipelineInitializationError(f"Prompt with ID {self.prompt_db_id} not found in the database.")
        prompt_class_name = prompt_db_model.class_name
        prompt_params = prompt_db_model.parameters

        self.validate_params(kwargs)

        try:
            chunking_model_class_name = kwargs['chunking_model']['component']
            chunking_model_params = kwargs['chunking_model']['params']
            retriever_model_class_name = kwargs['retriever_model']['component']
            retriever_model_params = kwargs['retriever_model']['params']
            generation_model_class_name = kwargs['generation_model']['component']
            generation_model_params = kwargs['generation_model']['params']

        except KeyError as e:
            raise RAGPipelineParametersError(f"Missing required parameter: {str(e)}")
        
        try:
            chunking_model_class = self.component_registry[chunking_model_class_name]['class']
            retriever_model_class = self.component_registry[retriever_model_class_name]['class']
            generation_model_class = self.component_registry[generation_model_class_name]['class']
            prompt_class = self.component_registry[prompt_class_name]['class']
        except KeyError as e:
            raise RAGPipelineInitializationError(f"Component '{str(e)}' not found in the component registry.")
        
        self.chunking_model_factory = ChunkingModelsFactory(
            db = self.db,
            documents=self.documents
            )
        self.chunking_model_id, self.chunking_model = self.chunking_model_factory.init_component(
            model_class=chunking_model_class,
            model_params=chunking_model_params
        )
        self.chunking_model_factory.update_db_models(self.chunking_model)
        self.chunks = self.chunking_model.get_chunks()

        self.retriever_model_factory = RetrieverModelsFactory(
            db = self.db,
            pipeline_id = self.pipeline_id,
            component_registry = self.component_registry,
            env_rag_path = self.env_rag_path,
            documents = self.documents,
            chunks = self.chunking_model.get_chunks(),
            chunking_model_id = self.chunking_model_id
            )
        self.retriever_id, self.retriever = self.retriever_model_factory.init_component(
            model_class=retriever_model_class,
            model_params=retriever_model_params
        )
        
            
        self.chunking_model_id = self.chunking_model.id

        self.llm_model: TextToTextGenerationTaskModel = generation_model_class(**generation_model_params)
        self.prompt_model: Prompt = prompt_class(**prompt_params)
        self.retrieval_algorithm = "SINGLE_INTERACTION"

    def validate_params(
            self, 
            params: dict):
        """Validate RAG pipeline parameters."""
        required_keys = ["chunking_model", "retriever_model", "generation_model"]
        for key in required_keys:
            if key not in params:
                raise RAGPipelineParametersError(f"Missing required parameter '{key}' in RAG pipeline configuration")
    
            
        # Validate model components
        for model in ["chunking_model", "retriever_model", "generation_model"]:
            args = params[model]
            if "component" not in args:
                raise RAGPipelineParametersError(f"Missing 'component' field in '{model}' configuration")
            if "params" not in args:
                raise RAGPipelineParametersError(f"Missing 'params' field in '{model}' configuration")
            if args["component"] not in self.component_registry:
                raise RAGPipelineParametersError(f"No components registered for type '{model}'")
       
    def single_interaction(
        self, 
        query: str, 
        history: Optional[List[Tuple[str, str]]] = None
    ) -> List[Chunk]:
        """Perform a single retrieval interaction based on the input query.

        Args:
            query: The input query to use for document retrieval
            history: Optional conversation history (not used in single interaction)

        Returns:
            List of tuples containing (document_content, document_file, chunk_id)

        Raises:
            RAGPipelineRuntimeError: If document retrieval fails
        """
        try:
            return self.retriever.retrieve(query)
        except Exception as e:
            raise RAGPipelineRuntimeError(f"Document retrieval failed: {str(e)}")
        
    def augmented_interaction(
        self, 
        query: str, 
        history: Optional[List[Tuple[str, str]]] = None,
        max_search_terms: int = 5
    ) -> List[Chunk]:
        """Perform an augmented retrieval interaction using generated search terms.

        Args:
            query: The input query
            history: Optional conversation history
            max_search_terms: Maximum number of search terms to use

        Returns:
            List of tuples containing (document_content, document_file, chunk_id)

        Raises:
            RAGPipelineRuntimeError: If any step of the augmented interaction fails
        """
        try:
            search_terms = self._generate_search_terms(query, history, max_search_terms)
            return self._retrieve_with_search_terms(search_terms)
        except RAGPipelineRuntimeError:
            raise
        except Exception as e:
            raise RAGPipelineRuntimeError(f"Failed during augmented interaction: {str(e)}")

    def _generate_search_terms(
        self, 
        query: str, 
        history: Optional[List[Tuple[str, str]]], 
        max_terms: int
    ) -> List[str]:
        """Generate search terms from the input using the LLM.

        Args:
            query: Input query to generate search terms from
            history: Optional conversation history
            max_terms: Maximum number of search terms to return

        Returns:
            List of generated search terms

        Raises:
            RAGPipelineRuntimeError: If search term generation or parsing fails
        """
        try:
            augmentation_prompt = DefaultAugmentationPrompt.format(
                input=query,
                history=history,
                n_search_terms=max_terms
            )
            augmentation_response = self.llm_model.generate(augmentation_prompt)[0]
            print(f"Augmentation response: {augmentation_response}")
            
            try:
                search_terms = augmentation_response.split("keywords:")[1].strip()
                search_terms = [term.strip() for term in search_terms.split(",")]
                return search_terms[:max_terms]
            except Exception as e:
                raise RAGPipelineRuntimeError(f"Failed to parse search terms from model response: {str(e)}")
        except Exception as e:
            raise RAGPipelineRuntimeError(f"Failed to generate search terms: {str(e)}")

    def _retrieve_with_search_terms(self, search_terms: List[str]) -> List[Chunk]:
        """Retrieve documents using the generated search terms.

        Args:
            search_terms: List of search terms to use for retrieval

        Returns:
            List of Chunk objects

        Raises:
            RAGPipelineRuntimeError: If document retrieval fails
        """
        try:
            print(f"Retrieving documents with search terms: {search_terms}")
            return self.retriever.retrieve(search_terms)
        except Exception as e:
            raise RAGPipelineRuntimeError(f"Document retrieval failed: {str(e)}")

    def generate(self, input_data: Tuple[str, List[Dict[str, str]]]) -> Tuple[str, Dict[str, Any]]:
        """Generate a response based on the input and retrieved documents.

        Args:
            input_data: Tuple containing (query, conversation_history)

        Returns:
            List containing the generated response with source information

        Raises:
            RAGPipelineRuntimeError: If any generation step fails
        """
        try:
            input_dict = input_data[-1]
            input_message = input_dict['content']
            history = input_data[:-1]
            chunks = self.single_interaction(input_message)
        except Exception as e:
            raise RAGPipelineRuntimeError(f"Failed during retrieval: {str(e)}")
        try:
            chunks_texts = []
            chunk_dict = {}
            for chunk in chunks:
                document_id = chunk.document_id
                document = self.documents[document_id]
                chunk_position = chunk.document_position
                chunk_text = chunk.text
                chunk = self.chunks[document_id][chunk_position]
                chunk_id = chunk.id
                chunk_dict[chunk_id] = {
                    "document_id": document_id,
                    "document_position": chunk_position,
                    "text": chunk_text
                }
                chunks_texts.append(f"Document {document.file_name}, chunk nº {chunk_position}, text:\n {chunk_text}")
            chunks_text = "\n\n".join(chunks_texts)
            prompt = self.prompt_model.format(
                input=input_message,
                chunks=chunks_text
            )
            print(f"Prompt: {prompt[:500]}...")
        except Exception as e:
            raise RAGPipelineRuntimeError(f"Failed during prompt formatting: {str(e)}")
        try:
            model_input = history + [{"role": "user", "content": prompt}]
            output = self.llm_model.generate(model_input)
            return [output[0], chunk_dict]
        except Exception as e:
            raise RAGPipelineRuntimeError(f"Failed during LLM generation: {str(e)}")

    
    def load_documents_from_db(self, documents_ids: List[int]) -> Dict[int, BaseDocument]:
        """
        Retrieve Document instances from the database based on their IDs.
        
        Args:
            documents_ids: List of document IDs to retrieve
            db: Database session for querying documents

        Raises:
            RAGDatabaseError: If a document ID is not found in the database

        Returns:
            List of BaseDocument instances corresponding to the provided IDs

        Raises:
            RAGDatabaseError: If a document ID is not found in the database
        """
        documents = {}
        for doc_id in documents_ids:
            db_doc: DBDocument = self.db.query(DBDocument).filter(DBDocument.id == doc_id).first()
            if not db_doc:
                raise RAGDatabaseError(f"Document with ID {doc_id} not found in the database.")
            doc_class = documents_models[db_doc.file_type]
            document: BaseDocument = doc_class(
                id = db_doc.id,
                file_name = db_doc.file_name,
                file_path = db_doc.file_path,
                created = db_doc.created,
                optional_metadata = db_doc.optional_metadata)
            documents[doc_id] = document
        return documents


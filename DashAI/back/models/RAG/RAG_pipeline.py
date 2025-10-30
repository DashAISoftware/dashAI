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
from DashAI.back.models.RAG.prompts import Prompt, DefaultGenerationPrompt, DefaultAugmentationPrompt
from DashAI.back.models.RAG.Retrievers.retriever_model import RetrieverModel

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
        self.prompt_db_id: int = kwargs.pop("prompt_id")
        prompt_db_model: PromptDBModel = self.db.query(PromptDBModel).filter_by(id=self.prompt_db_id).first()
        if not prompt_db_model:
            raise RAGPipelineInitializationError(f"Prompt with ID {self.prompt_db_id} not found in the database.")
        prompt_model_args = {
            'component': prompt_db_model.class_name,
            'params': prompt_db_model.parameters
        }

        self.documents = self.load_documents_from_db(documents_ids=self.documents_ids)
        self.validate_params(kwargs)

        try:
            
            config = {
                'chunking_model': kwargs.pop('chunking_model'),
                'retriever_model': kwargs.pop('retriever_model'),
                'generation_model': kwargs.pop('generation_model'),
                'prompt_model': prompt_model_args
            }
        except KeyError as e:
            raise RAGPipelineParametersError(f"Missing required parameter: {str(e)}")
        
        self.chunking_model = self.init_component(config["chunking_model"])
        self.chunks = self.chunking_model.get_chunks()
        self.chunking_model_id = self.chunking_model.id

        self.retriever = self.init_component(config["retriever_model"])
        self.retriever_id = self.retriever.retriever_db_model.id
        self.llm_model = self.init_component(config["generation_model"])
        self.prompt_model = self.init_component(config["prompt_model"])
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
    
    def generate(self, input_data: Tuple[str, List[Dict[str, str]]]) -> List[str]:
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
            for chunk in chunks:
                chunk_id = chunk.id
                document_id = chunk.document_id
                document_position = chunk.document_position
                document = self.documents[document_id]
                chunks_texts.append(f"Document {document.file_name}, chunk nº {document_position}, text:\n {chunk.text}")
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
            response_with_sources = f"{output[0]}\n\nSources:\n{chunks_texts}"
            return [response_with_sources]
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

    def init_component(
            self,
            config: Dict[str, Any]) -> Any:
        """
        Initialize a component based on the provided configuration, using the component registry.

        Args:
            model_name: The key in the config dict for the component to initialize
            config: Configuration dictionary containing component details

        Returns:
            An instance of the initialized component

        Raises:
            RAGPipelineInitializationError: If the component fails to initialize
        """
        
        model_class_name = config['component']
        model_params = config['params']
        model_registry = self.component_registry[model_class_name]
        model_class = model_registry['class']

        if 'db' in model_class.REQUIRED_EXTRA_KWARGS:
            model_params['db'] = self.db
            model_params['pipeline_id'] = self.pipeline_id
        if 'pipeline_id' in model_class.REQUIRED_EXTRA_KWARGS:
            model_params['pipeline_id'] = self.pipeline_id
        if 'component_registry' in model_class.REQUIRED_EXTRA_KWARGS:
            model_params['component_registry'] = self.component_registry
        if 'env_rag_path' in model_class.REQUIRED_EXTRA_KWARGS:
            model_params['env_rag_path'] = self.env_rag_path
        
        if 'documents' in model_class.REQUIRED_EXTRA_KWARGS:
            model_params['documents'] = self.documents
        if 'chunks' in model_class.REQUIRED_EXTRA_KWARGS:
            model_params['chunks'] = self.chunks
        if 'chunking_model_id' in model_class.REQUIRED_EXTRA_KWARGS:
            model_params['chunking_model_id'] = self.chunking_model_id
        try:
            model_instance = model_class(**model_params)
        except Exception as e:
            import traceback
            traceback.print_exc()
            
            raise RAGPipelineInitializationError(f"Failed to initialize {model_class_name}: {str(e)}")
        return model_instance
    
import gc
import logging
from typing import Any, Dict, List

import torch
from kink import inject
from sqlalchemy import exc
from sqlalchemy.orm import Session

from DashAI.back import pipeline
from DashAI.back.dependencies.database.models import (
    Document,
    GenerativeProcess,
    GenerativeSession,
    ProcessData,
    RAGChunk,
    RAGChunkingModel,
    RAGDenseRetriever,
    RAGEmbeddingModel,
    RAGPipeline,
    RAGSparseRetriever,

)
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.models.RAG.RAG_pipeline import RAGPipeline, RAGPipelineParametersError
from DashAI.back.models.RAG.chunking_models.base_chunking_model import BaseChunkingModel
from DashAI.back.tasks.RAG_task import RAGTask

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

    

class RAGJob(BaseJob):
    """RAGJob class responsible for executing the RAG pipeline as a background job.
    This class handles the entire lifecycle of a RAG generative process, including:
    - Retrieving the generative process and session from the database
    - Validating and instantiating the RAG pipeline components (chunking model, retriever model, generation model, prompt)
    - Running the pipeline to generate output based on the input and context
    - Processing and saving the output back to the database
    - Updating the status of the generative process throughout the execution
    """

    def set_status_as_delivered(self) -> None:
        """Set the status of the job as delivered."""
        generative_process_id: int = self.kwargs["generative_process_id"]
        db: Session = self.kwargs["db"]

        process: GenerativeProcess = db.get(GenerativeProcess, generative_process_id)
        if not process:
            raise JobError(
                f"Generative process {generative_process_id} does not exist in DB."
            )
        try:
            process.set_status_as_delivered()
            db.commit()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise JobError(
                "Internal database error",
            ) from e

    def create_chunking_model(
            self, 
            db: Session, 
            chunking_class: str, 
            chunking_params: Dict[str, Any]
            ) -> RAGChunkingModel:
        """Create and store a new chunking model in the database."""
        try:
            new_chunking_model = RAGChunkingModel(
                class_name=chunking_class,
                parameters=chunking_params
            )
            db.add(new_chunking_model)
            db.commit()
            db.refresh(new_chunking_model)
            return new_chunking_model
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise JobError("Internal database error") from e

    def create_RAG_chunk(
            self, 
            db: Session, 
            chunk_text: str, 
            document_id: int, 
            chunking_model_id: int) -> RAGChunk:
        """Create and store a new RAG chunk in the database."""
        try:
            new_chunk = RAGChunk(
                text=chunk_text,
                document_id=document_id,
                chunking_model_id=chunking_model_id
            )
            db.add(new_chunk)
            db.commit()
            db.refresh(new_chunk)
            return new_chunk
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise JobError("Internal database error") from e

    def create_RAG_retriever_model(
            self, 
            db: Session, 
            retriever_class: str, 
            retriever_params: Dict[str, Any], 
            chunk_embedding_model_id: int
            ) -> RAGDenseRetriever:
        """Create and store a new RAG retriever model in the database."""
        try:
            new_retriever = RAGDenseRetriever(
                class_name=retriever_class,
                parameters=retriever_params,
                chunk_embedding_model_id=chunk_embedding_model_id
            )
            db.add(new_retriever)
            db.commit()
            db.refresh(new_retriever)
            return new_retriever
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise JobError("Internal database error") from e

    def get_chunks_from_db(self, db: Session, documents: List[Document], chunking_class: str, chunking_params: Dict[str, Any]) -> Dict[int, List[RAGChunk]]:
        """Retrieve chunks from the database or return empty list if not found."""
        chunking_model: RAGChunkingModel = db.query(RAGChunkingModel).filter_by(
            component=chunking_class,
            parameters=chunking_params
        ).first()
        if not chunking_model:
            return []
        # Chunks generated with this chunking model
        chunks: List[RAGChunk] = db.query(RAGChunk).filter(RAGChunk.chunking_model == chunking_model).all()
        if not chunks or len(chunks) == 0:
            return []
        # Filter chunks to only those related to the provided documents
        document_ids = {doc.id for doc in documents}
        filtered_chunks = {}
        for doc_id in document_ids:
            doc_chunks = [chunk for chunk in chunks if chunk.document_id == doc_id]
            if not doc_chunks or len(doc_chunks) == 0:
                return {}
            filtered_chunks[doc_id] = doc_chunks
        return filtered_chunks

    def store_chunks_in_db(
            self, 
            db: Session, 
            documents: List[Document], 
            chunking_class: str, 
            chunking_params: Dict[str, Any], 
            chunked_documents: Dict[int, List[RAGChunk]],
            ) -> None:
        """Store chunked documents in the database."""
        try:
            chunking_model: RAGChunkingModel = db.query(RAGChunkingModel).filter_by(
                component=chunking_class,
                parameters=chunking_params
            ).first()
            if not chunking_model:
                self.create_chunking_model(db, chunking_class, chunking_params)
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise JobError("Internal database error") from e
        try:
            chunks_to_add = []
            for doc_id, chunks in chunked_documents.items():
                for chunk in chunks:
                    chunk.document_id = doc_id
                    chunk.chunking_model_id = chunking_model.id
                    chunks_to_add.append(chunk)
            db.add_all(chunks_to_add)
            db.commit()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise JobError("Internal database error") from e
        
    def run_chunking_model(self, chunking_model: BaseChunkingModel, documents: List[Document]) -> Dict[int, List[RAGChunk]]:
        """Run chunking model to process documents."""
        try:
            chunked_documents = chunking_model.chunk_documents(documents)
        except Exception as e:
            raise JobError("Error during document chunking.") from e
        return chunked_documents

    @inject
    async def run(
        self,
        component_registry: ComponentRegistry = lambda di: di["component_registry"],
        config=lambda di: di["config"],
    ) -> None:
        pipeline = None
        generative_process = None
        try:
            generative_process_id: int = self.kwargs["generative_process_id"]
            db: Session = self.kwargs["db"]

            try:
                generative_process: GenerativeProcess = db.get(
                    GenerativeProcess, generative_process_id
                )
                if not generative_process:
                    raise JobError(
                        f"Generative process {generative_process_id} not found in DB."
                    )
            except Exception as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError("Error retrieving generative process.") from e

            try:
                generative_session: GenerativeSession = db.get(
                    GenerativeSession, generative_process.session_id
                )
                if not generative_session:
                    raise JobError(
                        f"Session {generative_process.session_id} not found in DB."
                    )
            except Exception as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError("Error retrieving generative session.") from e

            try:
                model_class:RAGPipeline = component_registry[generative_session.model_name]["class"]
                assert type(model_class) is RAGPipeline, "Only RAG models are supported"
                params = generative_session.parameters
                params = model_class.validate_params(params)
            except RAGPipelineParametersError as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError(f"Invalid RAG pipeline parameters: {e}") from e
            try:
                documents_ids = params['documents']
                documents = []
                for doc_id in documents_ids:
                    doc = db.get(Document, doc_id)
                    if not doc:
                        raise JobError(f"Document {doc_id} not found in DB.")
                    documents.append(doc)
            except Exception as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError("Error retrieving documents from DB.") from e
            
            try:
                chunking_model_class_name = params['chunking_model']['component']
                chunking_model_class = component_registry[chunking_model_class_name]["class"]
                chunking_model_params = params['chunking_model']['params']
                chunking_model_params['documents'] = documents
                chunking_model = chunking_model_class(**chunking_model_params)
            except KeyError as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError(f"Invalid chunking model specified: {e}") from e
            except Exception as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError("Error instantiating chunking model.") from e
            
            try:
                retriever_model_class_name = params['retriever_model']['component']
                retriever_model_class = component_registry[retriever_model_class_name]["class"]
                retriever_model_params = params['retriever_model']['params']
                retriever_model = retriever_model_class(**retriever_model_params)
            except KeyError as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError(f"Invalid retriever model specified: {e}") from e
            except Exception as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError("Error instantiating retriever model.") from e
            
            try:
                generation_model_class_name = params['generation_model']['component']
                generation_model_class = component_registry[generation_model_class_name]["class"]
                generation_model_params = params['generation_model']['params']
                generation_model = generation_model_class(**generation_model_params)
            except KeyError as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError(f"Invalid generation model specified: {e}") from e
            except Exception as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError("Error instantiating generation model.") from e
            
            try:
                prompt_type = params['prompt']['type']
                prompt_template = params['prompt']['template']
                prompt_class = component_registry[prompt_type]["class"]
                prompt = prompt_class(prompt_template)
            except KeyError as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError(f"Invalid prompt type specified: {e}") from e
            except Exception as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError("Error instantiating prompt.") from e

            try:
                pipeline: RAGPipeline = RAGPipeline(documents, chunking_model, retriever_model, generation_model, prompt)
            except Exception as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError(
                    "Error instantiating model with given parameters."
                ) from e

            input_data = generative_process.input

            try:
                task: RAGTask = RAGTask()
            except KeyError as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError(
                    f"Task '{generative_session.task_name}' not found in registry."
                ) from e
            except Exception as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError("Error instantiating task.") from e

            try:
                history = [
                    (proc.input[0].data, proc.output[0].data)
                    for proc in db.query(GenerativeProcess)
                    .filter(GenerativeProcess.session_id == generative_session.id)
                    .filter(GenerativeProcess.status == "FINISHED")
                    .all()
                ]
                input_data = task.prepare_for_task(
                    input_data,
                    history=history,
                )
            except Exception as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError("Error preparing task with history.") from e

            try:
                generative_process.set_status_as_started()
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError("Failed to update process status in database.") from e

            try:
                output: Any = pipeline.generate(input_data)
            except Exception as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.add(
                    ProcessData(
                        data=f"Error details: {str(e)}",
                        data_type="str",
                        process_id=generative_process.id,
                        is_input=False,
                    )
                )
                db.commit()
                raise JobError("Error during model generation.") from e

            try:
                output: Any = task.process_output(
                    output, images_path=config["IMAGES_PATH"]
                )
                outputs_for_database = []
                for o in output:
                    if not isinstance(o, tuple) or len(o) != 2:
                        raise JobError(
                            "Output from task must be a list of tuples (data, type)."
                        )
                    output_data, output_type = o
                    process_data = ProcessData(
                        data=output_data,
                        data_type=output_type,
                        process_id=generative_process.id,
                        is_input=False,
                    )
                    outputs_for_database.append(process_data)

                db.add_all(outputs_for_database)
                db.commit()

                # Update the generative process with the output
                db.refresh(generative_process)
                generative_process.set_status_as_finished()
                db.commit()
            except Exception as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError("Error processing and saving generation output.") from e

        finally:
            if pipeline:
                del pipeline
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()

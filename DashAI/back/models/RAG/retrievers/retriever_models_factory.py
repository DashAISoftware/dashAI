import os
from DashAI.back.models.RAG.retrievers.retriever_model import RetrieverModel
from DashAI.back.models.RAG.retrievers.dense_retriever import DenseRetriever
from DashAI.back.models.RAG.retrievers.sparse_retriever import SparseRetriever
from DashAI.back.models.RAG.models_factory import ModelsFactory
from DashAI.back.dependencies.database.models import (
    RAGRetriever as RetrieverDBModel,
    RAGDenseRetriever as DenseRetrieverDBModel,
    RAGSparseRetriever as SparseRetrieverDBModel,
    Chunk as ChunkDBModel,
    RAGEmbeddingModel as EmbeddingDBModel,
    RAGEmbeddingMatrix as EmbeddingMatrixDBModel
)
from DashAI.back.models.RAG.extra_args_enum import (
    PIPELINE_ID,
    DB,
    COMPONENT_REGISTRY,
    ENV_RAG_PATH,
    DOCUMENTS,
    CHUNKS,
    CHUNKING_MODEL_ID,
    RETRIEVER_DB_MODEL as RETRIEVER_DB_MODEL_ENUM,
    SPARSE_RETRIEVER_DB_MODEL as SPARSE_RETRIEVER_DB_MODEL_ENUM,
    DENSE_RETRIEVER_DB_MODEL as DENSE_RETRIEVER_DB_MODEL_ENUM,
    EMBEDDING_DB_MODEL as EMBEDDING_DB_MODEL_ENUM,
    EMBEDDING_MATRICES_DB_MODELS as EMBEDDING_MATRICES_DB_MODELS_ENUM,
)
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Tuple
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.utils import hash_function
from DashAI.back.models.RAG.documents.base_document import BaseDocument
from DashAI.back.models.RAG.documents.chunk import Chunk

class RetrieverModelsFactory(ModelsFactory):
    """
    Class responsible for creating retriever model instances and storing their models in database.
    """

    def __init__(
            self,
            db: Session, 
            pipeline_id: int,
            component_registry: ComponentRegistry,
            env_rag_path: str,
            documents: List[BaseDocument],
            chunks: Dict[int, Dict[int, Chunk]],
            chunking_model_id: int
            ):
        super().__init__(
            pipeline_id = pipeline_id,
            db = db,
            component_registry = component_registry,
            env_rag_path = env_rag_path,
            documents = documents,
            chunks = chunks,
            chunking_model_id = chunking_model_id
        )

    def fetch_sparse_retriever_db_model(
            self,
            class_name: str,
            model_params: Dict[str, Any],
            document_ids: List[int]
            ) -> SparseRetrieverDBModel|None:
        """Fetch the sparse retriever database model if it exists."""
        model_params = dict(sorted(model_params.items()))
        document_ids = sorted(document_ids)
        existing_model = self.db.query(SparseRetrieverDBModel).filter_by(
                class_name=class_name,
                parameters=model_params,
                documents_ids=document_ids,
                chunking_model_id=self.chunking_model_id
            ).first()
        #if not existing_model:
            #new_model = SparseRetrieverDBModel(
                #class_name=class_name,
                #parameters=model_params,
                #storage_folder="",
                #documents_ids=document_ids,
                #chunking_model_id=self.chunking_model_id
            #)
            #self.db.add(new_model)
            #self.db.commit()
            #self.db.refresh(new_model)
            #new_model.storage_folder = os.path.join(
                #self.env_rag_path,
                #"sparse_retrievers",
                #f"sparse_retriever_id-{new_model.id}"
            #)
            #self.db.commit()
            #return new_model

        return existing_model
    
    def fetch_dense_retriever_db_models(
            self,
            class_name: str,
            model_params: Dict[str, Any],
            document_ids: List[int]
            ) -> Tuple[DenseRetrieverDBModel|None, EmbeddingDBModel|None, Dict[int, EmbeddingMatrixDBModel]]:

        documents_ids = sorted(document_ids)


        dense_retriever_db_model = self.db.query(DenseRetrieverDBModel).filter_by(
            class_name=class_name,
            parameters=model_params,
            document_ids=documents_ids,
            chunking_model_id=self.chunking_model_id
        ).first()

        embedding_dict = model_params["encoding_model"]["properties"]["params"]["comp"]
        embedding_class_name = embedding_dict["component"]
        embedding_params = embedding_dict["params"]
        embedding_params = dict(sorted(embedding_params.items()))
        embedding_db_model = self.db.query(EmbeddingDBModel).filter_by(
            class_name=embedding_class_name,
            parameters=embedding_params
        ).first()

        if embedding_db_model is None:
            embedding_db_model = EmbeddingDBModel(
                class_name=embedding_class_name,
                parameters=embedding_params
            )
            self.db.add(embedding_db_model)
            self.db.commit()
            self.db.refresh(embedding_db_model)
            embedding_matrices_db_models = {}
        else:
            embedding_matrices_db_models = {}
            for doc_id in document_ids:
                matrix_db_model = self.db.query(EmbeddingMatrixDBModel).filter_by(
                    document_id=doc_id,
                    chunking_model_id=self.chunking_model_id,
                    embedding_model_id=embedding_db_model.id
                ).first()
                if matrix_db_model:
                    embedding_matrices_db_models[doc_id] = matrix_db_model

        return dense_retriever_db_model, embedding_db_model, embedding_matrices_db_models

    def load_model_from_db(
            self, 
            model_class: RetrieverModel, 
            model_params: Dict[str, Any], 
            **kwargs) -> RetrieverModel|None:
        assert issubclass(model_class, RetrieverModel), "model_class must be a subclass of RetrieverModel"
        model_params = dict(sorted(model_params.items()))
        class_name = model_class.__name__
        document_ids = list(self.documents.keys())
        assert len(document_ids) > 0, "No documents provided to load retriever model."
        if issubclass(model_class, DenseRetriever):
            db_models = self.fetch_dense_retriever_db_models(
                class_name=class_name,
                model_params=model_params,
                document_ids=document_ids
            )
            subclass_db_model, embedding_db_model, embedding_matrices_db_models = db_models
            self.extra_kwargs[DENSE_RETRIEVER_DB_MODEL_ENUM] = subclass_db_model
            self.extra_kwargs[EMBEDDING_DB_MODEL_ENUM] = embedding_db_model
            self.extra_kwargs[EMBEDDING_MATRICES_DB_MODELS_ENUM] = embedding_matrices_db_models

            
        elif issubclass(model_class, SparseRetriever):
            subclass_db_model = self.fetch_sparse_retriever_db_model(
                class_name=class_name,
                model_params=model_params,
                document_ids=document_ids
            )
            self.extra_kwargs[SPARSE_RETRIEVER_DB_MODEL_ENUM] = subclass_db_model
        else:
            raise ValueError(f"Unsupported retriever model class: {model_class.__name__}")
        if subclass_db_model:
            for required_kwarg in model_class.REQUIRED_EXTRA_KWARGS:
                model_params[required_kwarg] = self.extra_kwargs[required_kwarg]
            instance = model_class(**model_params)
            return instance
    
    def save_dense_retriever_model_to_db(self, instance: DenseRetriever, **kwargs):
        for doc_id, matrix_db_model in instance.embedding_db_matrices.items():
            if matrix_db_model.id is None:
                self.db.add(matrix_db_model)
                self.db.commit()
                self.db.refresh(matrix_db_model)
                instance.embedding_db_matrices[doc_id] = matrix_db_model
                print(f"Saved embedding matrix DB model for document ID {doc_id} with ID {matrix_db_model.id}")
            else:
                print(f"Embedding matrix DB model for document ID {doc_id} already has ID {matrix_db_model.id}, skipping save.")
            
        dense_retriever_db_model = DenseRetrieverDBModel(
            class_name=instance.class_name,
            parameters=dict(sorted(instance.params.items())),
            document_ids=sorted(list(instance.documents.keys())),
            chunking_model_id=instance.chunking_model_id,
            embedding_model_id=instance.embedding_db_model.id
        )
        self.db.add(dense_retriever_db_model)
        self.db.commit()
        retriever_db_model = RetrieverDBModel(
            class_name=DenseRetriever.__name__,
            dense_retriever_id=dense_retriever_db_model.id,
        )
        self.db.add(retriever_db_model)
        self.db.commit()

        self.db.refresh(dense_retriever_db_model)
        self.db.refresh(retriever_db_model)

        return dense_retriever_db_model.id

    def save_sparse_retriever_model_to_db(self, instance: SparseRetriever, **kwargs):
        assert isinstance(instance, SparseRetriever), "instance must be an instance of SparseRetriever"
        parameters = dict(sorted(instance.parameters.items()))
        document_ids = list(sorted(instance.documents.keys()))
        sparse_db_model = SparseRetrieverDBModel(
            class_name=instance.class_name,
            parameters=parameters,
            storage_folder="",
            documents_ids=document_ids,
            chunking_model_id=instance.chunking_model_id
        )
        self.db.add(sparse_db_model)
        self.db.commit()
        storage_folder = os.path.join(
            self.env_rag_path,
            "sparse_retrievers",
            f"sparse_retriever_id-{sparse_db_model.id}"
        )
        sparse_db_model.storage_folder = storage_folder
        self.db.commit()
        
        retriever_db_model = RetrieverDBModel(
            class_name=SparseRetriever.__name__,
            sparse_retriever_id=sparse_db_model.id,
        )
        self.db.add(retriever_db_model)
        self.db.commit()
        self.db.refresh(sparse_db_model) 
        self.db.refresh(retriever_db_model)
        kwargs = {SPARSE_RETRIEVER_DB_MODEL_ENUM: sparse_db_model}
        
        instance.save_model_to_db(**kwargs)
        # Check that the storage folder is not empty
        assert os.path.exists(sparse_db_model.storage_folder), "Storage folder was not created."
        assert len(os.listdir(sparse_db_model.storage_folder)) > 0, "Storage folder is empty after saving the model."
        return sparse_db_model.id

    def save_model_to_db(self, instance, **kwargs):
        if isinstance(instance, DenseRetriever):
            return self.save_dense_retriever_model_to_db(instance, **kwargs)
        elif isinstance(instance, SparseRetriever):
            return self.save_sparse_retriever_model_to_db(instance, **kwargs)
        else:
            raise ValueError(f"Unsupported retriever model instance: {type(instance).__name__}")
    
    def update_db_models(self, instance, **kwargs):
        pass
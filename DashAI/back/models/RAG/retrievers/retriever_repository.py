"""Repository for retriever-related database operations.

Separates persistence logic (SQL queries, record creation) from
orchestration logic (component construction, DI, composites).
"""

from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from DashAI.back.dependencies.database.models import (
    RAGDenseRetriever as DenseRetrieverDBModel,
)
from DashAI.back.dependencies.database.models import (
    RAGEmbeddingMatrix as EmbeddingMatrixDBModel,
)
from DashAI.back.dependencies.database.models import (
    RAGEmbeddingModel as EmbeddingDBModel,
)
from DashAI.back.dependencies.database.models import (
    RAGRetriever as RetrieverDBModel,
)
from DashAI.back.dependencies.database.models import (
    RAGRetrieverChild,
)
from DashAI.back.dependencies.database.models import (
    RAGSparseRetriever as SparseRetrieverDBModel,
)


class RetrieverRepository:
    """All database operations for retriever models.

    This class owns every SQL query, INSERT, and DB-model construction
    related to retrievers. Factories use it as a collaborator; retriever
    instances never touch it.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_bridge(self, class_name: str, pipeline_id: int) -> RetrieverDBModel:
        """Insert a new canonical identity record in rag_retriever.

        Every retriever (unit or composite) gets one bridge record.
        Returns the persisted model with its auto-generated id.
        """
        bridge_record = RetrieverDBModel(
            class_name=class_name,
            pipeline_id=pipeline_id,
        )
        self.db.add(bridge_record)
        self.db.commit()
        self.db.refresh(bridge_record)
        return bridge_record

    def find_sparse(
        self,
        class_name: str,
        parameters: Dict[str, object],
        chunk_set_id: int,
    ) -> Optional[SparseRetrieverDBModel]:
        """Look up an existing sparse retriever record by its natural key.

        Parameters
        ----------
        class_name : str
            Concrete retriever class name (e.g. "TFIDFRetriever").
        parameters : dict
            Schema parameters, sorted for deterministic JSON serialisation.
        chunk_set_id : int
            Which chunk set this retriever was trained on.

        Returns
        -------
        SparseRetrieverDBModel or None
        """
        parameters = dict(sorted(parameters.items()))
        return (
            self.db.query(SparseRetrieverDBModel)
            .filter_by(
                class_name=class_name,
                parameters=parameters,
                chunk_set_id=chunk_set_id,
            )
            .first()
        )

    def save_sparse(
        self,
        class_name: str,
        parameters: Dict[str, object],
        storage_folder: str,
        bridge_id: int,
        chunk_set_id: int,
    ) -> SparseRetrieverDBModel:
        """Persist a new sparse retriever record and link it to its bridge.

        Returns the persisted model.
        """
        parameters = dict(sorted(parameters.items()))
        record = SparseRetrieverDBModel(
            bridge_id=bridge_id,
            chunk_set_id=chunk_set_id,
            class_name=class_name,
            parameters=parameters,
            storage_folder=storage_folder,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def find_dense(
        self,
        class_name: str,
        parameters: Dict[str, object],
        chunk_set_id: int,
    ) -> Optional[DenseRetrieverDBModel]:
        """Look up an existing dense retriever record by its natural key."""
        parameters = dict(sorted(parameters.items()))
        return (
            self.db.query(DenseRetrieverDBModel)
            .filter_by(
                class_name=class_name,
                parameters=parameters,
                chunk_set_id=chunk_set_id,
            )
            .first()
        )

    def save_dense(
        self,
        class_name: str,
        parameters: Dict[str, object],
        bridge_id: int,
        chunk_set_id: int,
        embedding_model_id: int,
    ) -> DenseRetrieverDBModel:
        """Persist a new dense retriever record and link it to its bridge."""
        parameters = dict(sorted(parameters.items()))
        record = DenseRetrieverDBModel(
            bridge_id=bridge_id,
            chunk_set_id=chunk_set_id,
            class_name=class_name,
            parameters=parameters,
            embedding_model_id=embedding_model_id,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def find_composite(
        self, pipeline_id: int, class_name: str
    ) -> Optional[RetrieverDBModel]:
        """Find the composite bridge record for a given pipeline."""
        return (
            self.db.query(RetrieverDBModel)
            .filter_by(
                pipeline_id=pipeline_id,
                class_name=class_name,
            )
            .first()
        )

    def find_composite_children(self, parent_id: int) -> List[RAGRetrieverChild]:
        """Return child links ordered by child_order."""
        return (
            self.db.query(RAGRetrieverChild)
            .filter_by(parent_id=parent_id)
            .order_by(RAGRetrieverChild.child_order)
            .all()
        )

    def save_composite(
        self,
        class_name: str,
        pipeline_id: int,
        child_bridge_ids: List[int],
    ) -> RetrieverDBModel:
        """Persist a composite bridge record and its child links.

        Parameters
        ----------
        class_name : str
            "SequentialRetriever" or "ParallelRetriever".
        pipeline_id : int
            Owning pipeline.
        child_bridge_ids : list[int]
            Ordered list of child bridge ids (rag_retriever.id).

        Returns
        -------
        RetrieverDBModel
            The persisted bridge record.
        """
        bridge_record = self.create_bridge(class_name, pipeline_id)
        for order, child_id in enumerate(child_bridge_ids):
            self.db.add(
                RAGRetrieverChild(
                    parent_id=bridge_record.id,
                    child_id=child_id,
                    child_order=order,
                )
            )
        self.db.commit()
        return bridge_record

    def find_or_create_embedding_model(
        self,
        class_name: str,
        parameters: Dict[str, object],
    ) -> EmbeddingDBModel:
        """Return an existing EmbeddingDBModel record or create one.

        This is idempotent: the same (class_name, parameters) pair
        always resolves to the same record.
        """
        parameters = dict(sorted(parameters.items()))
        existing = (
            self.db.query(EmbeddingDBModel)
            .filter_by(
                class_name=class_name,
                parameters=parameters,
            )
            .first()
        )
        if existing is not None:
            return existing
        record = EmbeddingDBModel(
            class_name=class_name,
            parameters=parameters,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    # NOTE: All embedding matrices are loaded into memory via np.load()
    # for simplicity — not suitable for very large document collections.
    def find_embedding_matrices(
        self,
        doc_ids: List[int],
        chunk_set_id: int,
        embedding_model_id: int,
    ) -> Dict[int, EmbeddingMatrixDBModel]:
        """Return existing embedding matrices keyed by document_id.

        Only matrices that actually exist in the database are returned.
        """
        result: Dict[int, EmbeddingMatrixDBModel] = {}
        for doc_id in doc_ids:
            matrix = (
                self.db.query(EmbeddingMatrixDBModel)
                .filter_by(
                    document_id=doc_id,
                    chunk_set_id=chunk_set_id,
                    embedding_model_id=embedding_model_id,
                )
                .first()
            )
            if matrix is not None:
                result[doc_id] = matrix
        return result

    def save_embedding_matrix(
        self,
        document_id: int,
        chunk_set_id: int,
        embedding_model_id: int,
        storage_folder: str,
        matrix_shape: List[int],
    ) -> EmbeddingMatrixDBModel:
        """Persist a new embedding matrix record.

        Returns the persisted model.
        """
        record = EmbeddingMatrixDBModel(
            document_id=document_id,
            chunk_set_id=chunk_set_id,
            embedding_model_id=embedding_model_id,
            storage_folder=storage_folder,
            matrix_shape=matrix_shape,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def find_embedding_matrix(
        self,
        document_id: int,
        chunk_set_id: int,
        embedding_model_id: int,
    ) -> Optional[EmbeddingMatrixDBModel]:
        """Look up a single embedding matrix record."""
        return (
            self.db.query(EmbeddingMatrixDBModel)
            .filter_by(
                document_id=document_id,
                chunk_set_id=chunk_set_id,
                embedding_model_id=embedding_model_id,
            )
            .first()
        )

    def find_sparse_by_bridge_id(
        self, bridge_id: int
    ) -> Optional[SparseRetrieverDBModel]:
        """Look up a sparse retriever sub-table record by its bridge_id."""
        return (
            self.db.query(SparseRetrieverDBModel).filter_by(bridge_id=bridge_id).first()
        )

    def find_dense_by_bridge_id(
        self, bridge_id: int
    ) -> Optional[DenseRetrieverDBModel]:
        """Look up a dense retriever sub-table record by its bridge_id."""
        return (
            self.db.query(DenseRetrieverDBModel).filter_by(bridge_id=bridge_id).first()
        )

    def find_bridge_for_sub_table(
        self,
        sub_db_model: SparseRetrieverDBModel | DenseRetrieverDBModel,
        class_name: str,
    ) -> Optional[RetrieverDBModel]:
        """Given a sub-table detail record, find its parent bridge record."""
        bridge = self.db.query(RetrieverDBModel).get(sub_db_model.bridge_id)
        if bridge is not None and bridge.class_name == class_name:
            return bridge
        return None

    def get_bridge_by_id(self, bridge_id: int) -> Optional[RetrieverDBModel]:
        """Fetch a bridge record by its primary key."""
        return self.db.query(RetrieverDBModel).get(bridge_id)

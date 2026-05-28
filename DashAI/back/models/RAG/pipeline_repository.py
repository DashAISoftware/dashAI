"""Persistence layer for the RAGPipeline DB record.

Keeps DB access out of the pipeline's __init__ so the pipeline can
focus on orchestration.
"""

from typing import Optional

from sqlalchemy.orm import Session

from DashAI.back.dependencies.database.models import RAGPipeline as PipelineDBModel


class PipelineRepository:
    """Manages the rag_pipeline DB record for a given session."""

    def __init__(self, db: Session):
        self._db = db

    def ensure_db_record(self, session_id: int) -> PipelineDBModel:
        """Return the existing pipeline record or create a placeholder.

        The placeholder has filler values for the FK columns; call
        ``update_db_record`` once the real component IDs are known.
        """
        existing: Optional[PipelineDBModel] = (
            self._db.query(PipelineDBModel).filter_by(session_id=session_id).first()
        )
        if existing is not None:
            return existing

        record = PipelineDBModel(
            session_id=session_id,
            name="",
            description=None,
            parameters=None,
            chunking_model_id=0,
            prompt_id=0,
            generation_model_id=0,
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return record

    def update_db_record(
        self,
        session_id: int,
        chunking_model_id: int,
        prompt_id: int,
        generation_model_id: int,
    ) -> None:
        """Patch the pipeline record with real component IDs."""
        pipeline_record: Optional[PipelineDBModel] = (
            self._db.query(PipelineDBModel).filter_by(session_id=session_id).first()
        )
        if pipeline_record is None:
            raise ValueError(f"No pipeline record for session {session_id}")
        pipeline_record.chunking_model_id = chunking_model_id
        pipeline_record.prompt_id = prompt_id
        pipeline_record.generation_model_id = generation_model_id
        self._db.commit()

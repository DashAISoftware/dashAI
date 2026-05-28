import hashlib
import json
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from DashAI.back.dependencies.database.models import (
    RAGChunkSet,
    RAGChunkSetDocument,
)


def _build_chunk_set_signature(
    document_ids: List[int],
    pipeline_config: Dict[str, Any],
) -> str:
    payload = json.dumps(
        {
            "doc_ids": sorted(document_ids),
            "config": dict(sorted(pipeline_config.items())),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


# NOTE: This does a SELECT then INSERT without a lock, which is safe for
# a single-user platform but could cause IntegrityError under concurrent
# session creation with identical document sets.
def get_or_create_chunk_set(
    db: Session,
    document_ids: List[int],
    pipeline_config: Dict[str, Any],
) -> RAGChunkSet:
    signature = _build_chunk_set_signature(document_ids, pipeline_config)
    existing = db.query(RAGChunkSet).filter_by(signature=signature).first()
    if existing:
        return existing

    chunk_set = RAGChunkSet(
        signature=signature,
        parameters=pipeline_config,
    )
    db.add(chunk_set)
    db.commit()
    db.refresh(chunk_set)

    for doc_id in sorted(document_ids):
        db.add(
            RAGChunkSetDocument(
                chunk_set_id=chunk_set.id,
                document_id=doc_id,
            )
        )

    db.commit()
    return chunk_set

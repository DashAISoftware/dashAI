import logging
import json
import os
import hashlib
from datetime import datetime
from typing import Any, Dict, List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    File,
    Form,
    UploadFile,
    Response,
)
from fastapi.responses import FileResponse
from kink import di
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker

from DashAI.back.api.api_v1.schemas import DocumentResponse
from DashAI.back.dependencies.database.models import Document
from DashAI.back.models.RAG.utils import hash_function

router = APIRouter()
log = logging.getLogger(__name__)


base_url = "/api/v1/document"
@router.get("/", response_model=List[DocumentResponse])
async def get_all_documents(
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get all documents with file_url included."""
    with session_factory() as db:
        try:
            documents = db.query(Document).all()

            documents_responses = []

            for doc in documents:
                documents_responses.append(
                    DocumentResponse(
                        id=doc.id,
                        file_name=doc.file_name,
                        file_type=doc.file_type,
                        file_hash=doc.file_hash,
                        created=doc.created,
                        last_modified=doc.last_modified,
                        optional_metadata=doc.optional_metadata,
                        related_sessions=[session.id for session in doc.related_sessions_ids] if doc.related_sessions_ids else None,
                        file_url=f"{base_url}/{doc.id}/download",
                    )
                )

            return documents_responses
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get metadata of a document by its ID."""
    with session_factory() as db:
        try:
            document = db.get(Document, document_id)
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document {document_id} does not exist in DB.",
                )
            return DocumentResponse(
                id=document.id,
                file_name=document.file_name,
                file_hash=document.file_hash,
                created=document.created,
                optional_metadata=document.optional_metadata,
                related_sessions=[session.id for session in document.related_sessions_ids] if document.related_sessions_ids else None,
                file_url=f"{base_url}/{document.id}/download",
            )
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/{document_id}/download", response_class=FileResponse)
async def download_document(
    document_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Download the actual file content of a document."""
    with session_factory() as db:
        document = db.get(Document, document_id)
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found",
            )
        if not os.path.exists(document.file_path):
            raise HTTPException(
                status_code=500,
                detail=f"File not found at {document.file_path}",
            )
        return FileResponse(
            path=document.file_path,
            file_name=document.file_name,
            media_type="application/octet-stream",
        )


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    metadata: str = Form(...),
    config: Dict[str, Any] = Depends(lambda: di["config"]),
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """
    Upload a new document to the RAG system with file content and metadata.
    The metadata should be a JSON string with required fields and an 'optional_metadata' dict.
    """
    docs_folder_path = config["DOCUMENTS_PATH"]
    if not docs_folder_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Documents folder {docs_folder_path} does not exist.",
        )
    try:
        metadata_dict = json.loads(metadata)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in metadata")

    file_name = metadata_dict.get("file_name")
    last_modified = metadata_dict.get("last_modified")
    if not file_name or not last_modified:
        raise HTTPException(
            status_code=400,
            detail="Missing required metadata fields: 'filename' and 'last_modified'",
        )
    optional_metadata = metadata_dict.get("optional_metadata", {})
    if not isinstance(optional_metadata, dict):
        raise HTTPException(
            status_code=400,
            detail="'optional_metadata' must be a dictionary",
        )
    try:
        content_bytes = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read file content")

    file_content_hash = hash_function(content_bytes)
    with session_factory() as db:
        existing_doc = db.query(Document).filter_by(file_hash=file_content_hash).first()
        if existing_doc:
            # Update existing document's information
            existing_doc.file_name = file_name
            existing_doc.optional_metadata = optional_metadata
            existing_doc.created = datetime.now()
            db.commit()
            return DocumentResponse(
                id=existing_doc.id,
                file_name=existing_doc.file_name,
                file_type=existing_doc.file_type,
                file_hash=existing_doc.file_hash,
                created=existing_doc.created,
                last_modified=existing_doc.last_modified,
                related_sessions=[session.id for session in existing_doc.related_sessions_ids],
                optional_metadata=existing_doc.optional_metadata,
                file_url=f"{base_url}/{existing_doc.id}/download"
            )
        else:
            # Create a new document entry
            try:
                max_id = db.query(Document.id).order_by(Document.id.desc()).first()
                new_id = (max_id[0] + 1) if max_id else 1
                file_path = os.path.join(docs_folder_path, f"{new_id}__{file_name}")

                with open(file_path, "wb") as f:
                    f.write(content_bytes)

                # Get file type from file extension
                file_type = os.path.splitext(file_name)[1].lstrip('.') or 'unknown'
                
                doc = Document(
                    file_name=file_name,
                    file_type=file_type,
                    file_path=str(file_path),
                    file_hash=file_content_hash,
                    optional_metadata=optional_metadata or None,
                )
                db.add(doc)
                db.commit()
                db.refresh(doc)

                return DocumentResponse(
                    id=doc.id,
                    file_name=doc.file_name,
                    file_type=doc.file_type,
                    file_hash=doc.file_hash,
                    created=doc.created,
                    last_modified=doc.last_modified,
                    related_sessions=None,
                    optional_metadata=doc.optional_metadata,
                    file_url=f"{base_url}/{doc.id}/download",
                )
            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal database error",
                ) from e

@router.get("/related-sessions/{document_id}", response_model=List[int])
async def get_related_sessions(
    document_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get all generative session IDs related to a specific document."""
    with session_factory() as db:
        try:
            document = db.get(Document, document_id)
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document {document_id} does not exist in DB.",
                )
            if not document.related_sessions_ids:
                return []
            related_session_ids = [session.id for session in document.related_sessions_ids]
            return related_session_ids
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Delete a document from the RAG system by its ID."""
    with session_factory() as db:
        try:
            document = db.get(Document, document_id)
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document {document_id} does not exist in DB.",
                )
            
            # Delete the physical file
            if os.path.exists(document.file_path):
                os.remove(document.file_path)
            
            # Delete the database record
            db.delete(document)
            db.commit()
            
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
        except OSError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error deleting physical file",
            ) from e


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document_metadata(
    document_id: int,
    metadata: str = Form(...),
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Update a document's metadata."""
    with session_factory() as db:
        try:
            document = db.get(Document, document_id)
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document {document_id} does not exist in DB.",
                )
            
            try:
                metadata_dict = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON in metadata")
            
            # Update fields that are allowed to be modified
            if "file_name" in metadata_dict:
                document.file_name = metadata_dict["file_name"]
                # Update file_type when file_name changes
                document.file_type = os.path.splitext(metadata_dict["file_name"])[1].lstrip('.') or 'unknown'
            
            if "optional_metadata" in metadata_dict:
                optional_metadata = metadata_dict["optional_metadata"]
                if not isinstance(optional_metadata, dict):
                    raise HTTPException(
                        status_code=400,
                        detail="'optional_metadata' must be a dictionary",
                    )
                document.optional_metadata = optional_metadata
            
            document.last_modified = datetime.now()
            
            db.commit()
            db.refresh(document)
            
            return DocumentResponse(
                id=document.id,
                file_name=document.file_name,
                file_hash=document.file_hash,
                created=document.created,
                optional_metadata=document.optional_metadata,
                related_sessions=[session.id for session in document.related_sessions_ids] if document.related_sessions_ids else None,
                file_url=f"{base_url}/{document.id}/download",
            )
            
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
        
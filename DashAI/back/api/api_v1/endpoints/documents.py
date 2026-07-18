import json
import logging
import os
from typing import Any, Dict, List
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from kink import di
from sqlalchemy.orm import sessionmaker

from DashAI.back.api.api_v1.schemas import DocumentResponse
from DashAI.back.models.RAG.exceptions import RAGDocumentFileTypeError
from DashAI.back.models.RAG.documents import DocumentFileType
from DashAI.back.services.RAG.document_service import DocumentService

router = APIRouter()
log = logging.getLogger(__name__)


base_url = "/api/v1/document"


@router.get("/", response_model=List[DocumentResponse])
async def get_all_documents(
    request: Request,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get all documents with file_url included."""
    with session_factory() as db:
        base = str(request.base_url).rstrip("/")
        return DocumentService(db).get_all(base_url=base)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    request: Request,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get metadata of a document by its ID."""
    with session_factory() as db:
        try:
            return DocumentService(db).get(document_id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from e


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Download the actual file content of a document."""

    with session_factory() as db:
        try:
            content, media_type, filename = DocumentService(db).download(document_id)
            encoded_name = quote(filename, safe="")
            return Response(
                content=content,
                media_type=media_type,
                headers={
                    "Content-Disposition": (
                        f"attachment; filename*=UTF-8''{encoded_name}"
                    )
                },
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from e


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    metadata: str = Form(...),
    config: Dict[str, Any] = Depends(lambda: di["config"]),
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Upload a new document to the RAG system with file content and metadata."""
    docs_folder_path = config["DOCUMENTS_PATH"]
    if not docs_folder_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Documents folder {docs_folder_path} does not exist.",
        )
    try:
        metadata_dict = json.loads(metadata)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400, detail="Invalid JSON in metadata"
        ) from None
    file_name = metadata_dict.get("file_name")
    if not file_name:
        raise HTTPException(
            status_code=400, detail="Missing required 'file_name' in metadata"
        )
    optional_metadata = metadata_dict.get("optional_metadata", {})
    if not isinstance(optional_metadata, dict):
        raise HTTPException(
            status_code=400, detail="'optional_metadata' must be a dictionary"
        )
    try:
        content_bytes = await file.read()
    except Exception:
        raise HTTPException(
            status_code=400, detail="Failed to read file content"
        ) from None
    ext = os.path.splitext(file_name)[1].lstrip(".")
    try:
        file_type = DocumentFileType(ext)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}",
        ) from None
    with session_factory() as db:
        return DocumentService(db).upload(
            content_bytes,
            file_name,
            file_type,
            str(docs_folder_path),
            optional_metadata,
        )


@router.get("/session/{session_id}", response_model=List[DocumentResponse])
async def get_documents_by_session(
    session_id: int,
    request: Request,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get all documents associated with a specific RAG session."""
    with session_factory() as db:
        try:
            base = str(request.base_url).rstrip("/")
            return DocumentService(db).get_by_session(session_id, base_url=base)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from e


@router.get("/related-sessions/{document_id}", response_model=List[int])
async def get_related_sessions(
    document_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get all generative session IDs related to a specific document."""
    with session_factory() as db:
        try:
            return DocumentService(db).get_related_sessions(document_id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from e


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Delete a document from the RAG system by its ID."""

    with session_factory() as db:
        try:
            DocumentService(db).delete(document_id)
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
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
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="Invalid JSON in metadata"
            ) from None
        file_name = metadata_dict.get("file_name")
        optional_metadata = metadata_dict.get("optional_metadata")

        try:
            return DocumentService(db).update_metadata(
                document_id,
                file_name=file_name,
                optional_metadata=optional_metadata,
            )
        except RAGDocumentFileTypeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e

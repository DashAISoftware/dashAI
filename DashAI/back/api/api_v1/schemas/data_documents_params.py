"""Schemas for the persistent documents of the Data module."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from DashAI.back.api.api_v1.schemas.folders_params import Folder
from DashAI.back.core.enums.status import DocumentStatus
from DashAI.back.dataloaders.classes.document_dataloader import redact_params

MAX_NAME_LENGTH = 255


class BatchDocumentFile(BaseModel):
    """One file of ``POST /api/v1/documents/batch``.

    Unknown keys are rejected, so a typo such as ``folder`` instead of
    ``folder_name`` fails the request instead of silently creating the
    documents somewhere else.

    Attributes
    ----------
    name : str
        Unique document name, at most 255 characters.
    file_name : str
        Name of the file the user is about to upload. Its extension must be
        one the loader supports.
    dataloader : str
        Registry name of a ``DocumentDataLoader`` component.
    dataloader_params : Dict[str, Any]
        Loader parameters. Missing keys take the loader defaults.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=MAX_NAME_LENGTH)
    file_name: str = Field(max_length=MAX_NAME_LENGTH)
    dataloader: str
    dataloader_params: Dict[str, Any] = Field(default_factory=dict)


class DocumentPipelineStep(BaseModel):
    """One converter of a document pipeline.

    The pipeline is batch-level: every document of the request runs the same
    steps. Each step runs on the content types its converter declares and is
    skipped when the document has none of them.

    Attributes
    ----------
    converter : str
        Registry name of a document converter component.
    params : Dict[str, Any]
        Converter parameters. Missing keys take the converter defaults.
    """

    model_config = ConfigDict(extra="forbid")

    converter: str
    params: Dict[str, Any] = Field(default_factory=dict)


class DataDocumentCreateParams(BatchDocumentFile):
    """Body of ``POST /api/v1/documents/``.

    Attributes
    ----------
    name : str
        Unique document name, at most 255 characters.
    file_name : str
        Name of the file the user is about to upload. Its extension must be
        one the loader supports.
    dataloader : str
        Registry name of a ``DocumentDataLoader`` component.
    dataloader_params : Dict[str, Any]
        Loader parameters. Missing keys take the loader defaults.
    folder_id : Optional[int]
        Folder receiving the document, or None to leave it loose. Only an
        integer is accepted: ``true`` and ``"1"`` are rejected.
    converter_pipeline : Optional[List[DocumentPipelineStep]]
        Converters the parse applies after loading the file, in order.
    """

    folder_id: Optional[int] = Field(default=None, strict=True)
    converter_pipeline: Optional[List[DocumentPipelineStep]] = None


class DataDocumentBatchCreateParams(BaseModel):
    """Body of ``POST /api/v1/documents/batch``.

    Unknown keys are rejected; see ``BatchDocumentFile``.

    Attributes
    ----------
    folder_name : Optional[str]
        Folder created for the documents, at most 255 characters. When
        omitted the documents are left loose.
    files : List[BatchDocumentFile]
        Documents to create, at least one. There is no upper bound.
    converter_pipeline : Optional[List[DocumentPipelineStep]]
        Converters every document of the batch runs after loading its file,
        in order.
    """

    model_config = ConfigDict(extra="forbid")

    folder_name: Optional[str] = Field(default=None, max_length=MAX_NAME_LENGTH)
    files: List[BatchDocumentFile] = Field(min_length=1)
    converter_pipeline: Optional[List[DocumentPipelineStep]] = None


class DataDocumentFromNotebookParams(BaseModel):
    """Body of ``POST /api/v1/documents/from-notebook``.

    Attributes
    ----------
    name : str
        Unique name of the new document.
    notebook_id : int
        The document notebook whose working copy becomes the new document.
    """

    name: str
    notebook_id: int


class DataDocumentUpdateParams(BaseModel):
    """Body of ``PATCH /api/v1/documents/{id}``.

    Attributes
    ----------
    name : Optional[str]
        New name, or None to keep the current one.
    folder_id : Optional[int]
        Folder to move into. Sending ``null`` explicitly removes the folder;
        leaving the key out keeps it.
    """

    name: Optional[str] = None
    folder_id: Optional[int] = None


class DataDocumentSchema(BaseModel):
    """A ``DataDocument`` row as the API serves it.

    Attributes
    ----------
    id : int
        Primary key.
    name : str
        Unique document name.
    file_name : Optional[str]
        Original file name.
    file_type : Optional[str]
        Lowercase extension without the dot.
    file_path : Optional[str]
        The ``<DOCUMENTS_PATH>/<uuid>`` folder, empty until the job starts.
    dataloader : Optional[str]
        Loader component name.
    dataloader_params : Optional[Dict[str, Any]]
        Resolved loader parameters.
    content_counts : Optional[Dict[str, int]]
        Items per DashAI type name, for example ``{"Text": 12, "Image": 3}``.
    converter_pipeline : Optional[List[Dict[str, Any]]]
        Converters applied while parsing, or None when none were requested.
    total_pages : Optional[int]
        Number of pages, None for formats without pages.
    folder_id : Optional[int]
        Folder holding the document.
    status : DocumentStatus
        Parsing status.
    created : datetime
        Creation time.
    last_modified : datetime
        Last change time.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    file_path: Optional[str] = None
    dataloader: Optional[str] = None
    dataloader_params: Optional[Dict[str, Any]] = None
    content_counts: Optional[Dict[str, int]] = None
    converter_pipeline: Optional[List[Dict[str, Any]]] = None
    total_pages: Optional[int] = None
    folder_id: Optional[int] = None
    status: DocumentStatus
    created: datetime
    last_modified: datetime

    @field_validator("dataloader_params")
    @classmethod
    def _hide_secrets(cls, value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Never return sensitive loader parameters such as passwords.

        Parameters
        ----------
        value : Optional[Dict[str, Any]]
            Stored loader parameters.

        Returns
        -------
        Optional[Dict[str, Any]]
            The parameters with sensitive values blanked.
        """
        return None if value is None else redact_params(value)


class DataDocumentBatchSchema(BaseModel):
    """Response of ``POST /api/v1/documents/batch``.

    Attributes
    ----------
    folder : Optional[Folder]
        The folder created with the documents, or None when the batch was
        created without one.
    documents : List[DataDocumentSchema]
        The created rows, in the order the request listed them.
    """

    folder: Optional[Folder] = None
    documents: List[DataDocumentSchema]

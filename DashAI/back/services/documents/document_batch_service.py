"""Validate and store the Data documents created by the upload flow.

The endpoint only parses the request and translates the errors raised here into
HTTP codes. Everything else, including the folder row and the single
transaction, lives in this module.
"""

import logging
import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Set,
)

from pydantic import ValidationError
from sqlalchemy import exc, select

from DashAI.back.api.api_v1.schemas.data_documents_params import (
    BatchDocumentFile,
    DataDocumentCreateParams,
    DataDocumentSchema,
)
from DashAI.back.api.api_v1.schemas.folders_params import Folder as FolderSchema
from DashAI.back.core.enums.status import DocumentStatus
from DashAI.back.dataloaders.classes.dataloader import (
    DataKindMismatchError,
    require_data_kind,
)
from DashAI.back.dependencies.database.models import DataDocument, Folder
from DashAI.back.services.documents.document_pipeline_service import (
    DocumentPipelineDownloadError,
    DocumentPipelineInvalidError,
    DocumentPipelineService,
    PipelineStep,
)
from DashAI.back.services.documents.folder_lock import lock_folder_row

if TYPE_CHECKING:
    from sqlalchemy.orm import Session, sessionmaker

    from DashAI.back.dataloaders.classes.document_dataloader import DocumentDataLoader
    from DashAI.back.dependencies.registry import ComponentRegistry

log = logging.getLogger(__name__)

NAME_LOOKUP_CHUNK_SIZE = 500


class InvalidDocumentUploadError(ValueError):
    """The upload cannot be stored as requested (HTTP 422)."""


class DocumentUploadConflictError(ValueError):
    """A name is taken or a loader is not downloaded yet (HTTP 409)."""


class FolderNotFoundError(LookupError):
    """The folder receiving a document does not exist (HTTP 404)."""


class DocumentStorageError(RuntimeError):
    """Storing the rows failed for a reason other than a name conflict (HTTP 500)."""


class _PreparedUpload(NamedTuple):
    """A document upload whose loader, extension and parameters are valid."""

    name: str
    file_name: str
    file_type: str
    dataloader: str
    dataloader_params: Dict[str, Any]


@dataclass(frozen=True)
class BatchResult:
    """What a batch creation stored.

    Attributes
    ----------
    folder : Optional[FolderSchema]
        The created folder, or None when the documents are loose.
    documents : List[DataDocumentSchema]
        The created rows, in request order.
    """

    folder: Optional[FolderSchema]
    documents: List[DataDocumentSchema]


def name_chunks(
    names: Sequence[str], size: int = NAME_LOOKUP_CHUNK_SIZE
) -> Iterator[List[str]]:
    """Split names into chunks small enough for one ``IN (...)`` clause.

    Parameters
    ----------
    names : Sequence[str]
        Names to look up.
    size : int
        Maximum number of names per chunk.

    Yields
    ------
    List[str]
        One bounded slice of ``names``.

    Raises
    ------
    ValueError
        If ``size`` is not positive.
    """
    if size <= 0:
        raise ValueError("Chunk size must be positive.")
    for start in range(0, len(names), size):
        yield list(names[start : start + size])


def _has_visible_characters(text: str) -> bool:
    """Tell whether a text has at least one character that renders.

    ``str.strip()`` only removes surrounding whitespace, so a name made of
    zero-width spaces, joiners or a byte order mark would survive it and show
    up as a blank row in the interface. Format, control and separator
    characters do not count as visible.

    Parameters
    ----------
    text : str
        Name to inspect.

    Returns
    -------
    bool
        True when some character is neither a control-nor a separator-like
        Unicode category.
    """
    return any(unicodedata.category(char)[0] not in {"C", "Z"} for char in text)


class DocumentBatchService:
    """Validate and store the documents of the upload flow.

    Each call opens its own database session, so an instance lives for one
    request. Loader resolution and the download gate are memoized per
    dataloader for the lifetime of the instance.

    Parameters
    ----------
    session_factory : sessionmaker
        Factory of the database sessions.
    component_registry : ComponentRegistry
        Registry used to resolve the loader components.
    """

    def __init__(
        self,
        session_factory: "sessionmaker",
        component_registry: "ComponentRegistry",
    ):
        self._session_factory = session_factory
        self._component_registry = component_registry
        self._loaders: Dict[str, type] = {}
        self._instances: Dict[str, "DocumentDataLoader"] = {}

    def loader_class(self, name: str) -> type:
        """Resolve a document loader class by name, once per service.

        Parameters
        ----------
        name : str
            Loader component name.

        Returns
        -------
        type
            The loader class, ready to be inspected.

        Raises
        ------
        InvalidDocumentUploadError
            422 case: the name is unknown or the loader does not produce
            documents.
        """
        if name not in self._loaders:
            self._loaders[name] = self._resolve_loader(name)
        return self._loaders[name]

    def loader_instance(self, name: str) -> "DocumentDataLoader":
        """Return the loader instance of a dataloader, once per service.

        Loaders keep no per-file state: ``resolve_params`` only reads the
        class schema, so one instance serves every file of the request. The
        download gate runs here, after the extension check, so an unsupported
        extension is a 422 even when the loader was never downloaded.

        Parameters
        ----------
        name : str
            Loader component name.

        Returns
        -------
        DocumentDataLoader
            The reusable loader instance.

        Raises
        ------
        InvalidDocumentUploadError
            422 case: the name is unknown or the loader does not produce
            documents.
        DocumentUploadConflictError
            409 case: the loader still has to be downloaded.
        """
        if name not in self._instances:
            loader_class = self.loader_class(name)
            if getattr(
                loader_class, "REQUIRES_DOWNLOAD", False
            ) and not self._component_registry.refresh_download_status(name):
                raise DocumentUploadConflictError(
                    f"Document loader {name} must be downloaded before use."
                )
            self._instances[name] = loader_class()
        return self._instances[name]

    def prepare(
        self,
        name: str,
        file_name: str,
        dataloader: str,
        dataloader_params: Dict[str, Any],
    ) -> _PreparedUpload:
        """Validate one upload and resolve its loader parameters.

        The loader, the extension and the parameters are checked first, and
        only then the download gate, so an unsupported extension is a 422 even
        when the loader was never downloaded.

        Parameters
        ----------
        name : str
            Requested document name.
        file_name : str
            Name of the file to upload; only its base name is kept.
        dataloader : str
            Loader component name.
        dataloader_params : Dict[str, Any]
            Loader parameters to resolve.

        Returns
        -------
        _PreparedUpload
            The cleaned name, base file name, extension and resolved
            parameters.

        Raises
        ------
        InvalidDocumentUploadError
            422 case: empty or invisible-only name, wrong loader, unsupported
            extension or invalid parameters.
        DocumentUploadConflictError
            409 case: the loader still has to be downloaded.
        """
        clean_name = name.strip()
        if not clean_name:
            raise InvalidDocumentUploadError("Name cannot be empty")
        if not _has_visible_characters(clean_name):
            raise InvalidDocumentUploadError("Name must contain a visible character")
        base_name = os.path.basename(file_name)
        loader_class = self.loader_class(dataloader)
        if not loader_class.supports_file(base_name):
            accepted = ", ".join(sorted(loader_class.SUPPORTED_EXTENSIONS))
            raise InvalidDocumentUploadError(
                f"{dataloader} accepts {accepted} files, not '{base_name}'."
            )
        loader = self.loader_instance(dataloader)
        try:
            resolved_params = loader.resolve_params(dataloader_params)
        except ValidationError as e:
            raise InvalidDocumentUploadError(str(e)) from e
        return _PreparedUpload(
            name=clean_name,
            file_name=base_name,
            file_type=Path(base_name).suffix.lower().lstrip("."),
            dataloader=dataloader,
            dataloader_params=resolved_params,
        )

    def create(
        self,
        files: List[BatchDocumentFile],
        folder_name: Optional[str],
        converter_pipeline: Optional[List[Any]] = None,
    ) -> BatchResult:
        """Create the documents and, optionally, their folder atomically.

        Every file, the folder name and the converter pipeline are validated
        before anything is written. The folder and its documents are then
        flushed and committed together; the response models are built from the
        flushed rows so a failure after the commit cannot turn a success into
        a 500.

        Parameters
        ----------
        files : List[BatchDocumentFile]
            Documents to create, at least one.
        folder_name : Optional[str]
            Folder to create with them, or None to leave them loose.
        converter_pipeline : Optional[List[Any]]
            Converters every document runs after parsing, or None.

        Returns
        -------
        BatchResult
            The created folder and documents.

        Raises
        ------
        InvalidDocumentUploadError
            422 case: empty folder name or file name, wrong loader,
            unsupported extension, invalid parameters or an invalid pipeline.
        DocumentUploadConflictError
            409 case: a folder or document name is taken, a name repeats
            inside the batch, or a loader or converter still has to be
            downloaded.
        DocumentStorageError
            500 case: the transaction failed.
        """
        clean_folder = self._clean_folder_name(folder_name)
        pipeline = self._pipeline(converter_pipeline)
        prepared = [
            self.prepare(
                item.name, item.file_name, item.dataloader, item.dataloader_params
            )
            for item in files
        ]
        self._ensure_unique_in_batch(prepared)
        with self._session_factory() as db:
            try:
                self._ensure_names_free(db, prepared, clean_folder)
                folder = Folder(name=clean_folder) if clean_folder else None
                if folder is not None:
                    db.add(folder)
                documents = []
                for item in prepared:
                    documents.append(self._new_document(item, folder, pipeline))
                db.add_all(documents)
                db.flush()
                result = self._result(folder, documents)
                db.commit()
            except exc.IntegrityError as e:
                db.rollback()
                raise DocumentUploadConflictError(
                    "A document or folder with that name already exists"
                ) from e
            except exc.SQLAlchemyError as e:
                db.rollback()
                log.exception(e)
                raise DocumentStorageError("Internal database error") from e
        return result

    def create_one(self, params: DataDocumentCreateParams) -> DataDocumentSchema:
        """Create one document, optionally inside an existing folder.

        The folder is checked first because it is the cheapest validation and
        a missing folder is a 404 even when the rest of the body is invalid.
        The folder row is locked before that check: SQLite has foreign keys
        disabled here, so without the lock a concurrent folder delete could
        commit between the check and the INSERT and leave the new document
        pointing at a folder that no longer exists.

        Parameters
        ----------
        params : DataDocumentCreateParams
            Name, file name, loader, loader parameters, folder and pipeline.

        Returns
        -------
        DataDocumentSchema
            The created row.

        Raises
        ------
        FolderNotFoundError
            404 case: the folder does not exist.
        InvalidDocumentUploadError
            422 case: empty name, wrong loader, unsupported extension,
            invalid parameters or an invalid pipeline.
        DocumentUploadConflictError
            409 case: the name is taken, the loader still has to be downloaded
            or a converter of the pipeline does.
        DocumentStorageError
            500 case: the transaction failed.
        """
        with self._session_factory() as db:
            try:
                if params.folder_id is not None:
                    lock_folder_row(db, params.folder_id)
                folder = self._existing_folder(db, params.folder_id)
                pipeline = self._pipeline(params.converter_pipeline)
                prepared = self.prepare(
                    params.name,
                    params.file_name,
                    params.dataloader,
                    params.dataloader_params,
                )
                taken = db.execute(
                    select(DataDocument.id).where(DataDocument.name == prepared.name)
                ).scalar()
                if taken:
                    raise DocumentUploadConflictError(
                        f"A document with the name '{prepared.name}' already exists"
                    )
                document = self._new_document(prepared, folder, pipeline)
                db.add(document)
                db.flush()
                schema = DataDocumentSchema.model_validate(document)
                db.commit()
            except exc.IntegrityError as e:
                db.rollback()
                raise DocumentUploadConflictError(
                    "A document with that name already exists"
                ) from e
            except exc.SQLAlchemyError as e:
                db.rollback()
                log.exception(e)
                raise DocumentStorageError("Internal database error") from e
        return schema

    def _pipeline(self, pipeline: Optional[List[Any]]) -> Optional[List[PipelineStep]]:
        """Validate a converter pipeline and translate its errors.

        The service error types are private to the pipeline module; the
        endpoint only knows the upload errors, so they are mapped here.

        Parameters
        ----------
        pipeline : Optional[List[Any]]
            Pipeline steps as the request sent them.

        Returns
        -------
        Optional[List[PipelineStep]]
            The normalized pipeline, or None when there was none.

        Raises
        ------
        InvalidDocumentUploadError
            422 case: the pipeline has an unknown, non document, supervised
            or row-changing converter, or invalid parameters.
        DocumentUploadConflictError
            409 case: a converter still has to be downloaded.
        """
        try:
            return DocumentPipelineService(self._component_registry).validate(pipeline)
        except DocumentPipelineInvalidError as e:
            raise InvalidDocumentUploadError(str(e)) from e
        except DocumentPipelineDownloadError as e:
            raise DocumentUploadConflictError(str(e)) from e

    def _resolve_loader(self, name: str) -> type:
        """Look the loader up in the registry and check it produces documents.

        Parameters
        ----------
        name : str
            Loader component name.

        Returns
        -------
        type
            The loader class.

        Raises
        ------
        InvalidDocumentUploadError
            422 case: the name is unknown or the loader does not produce
            documents.
        """
        if name not in self._component_registry:
            raise InvalidDocumentUploadError(
                f"Document loader '{name}' does not exist."
            )
        loader_class = self._component_registry[name]["class"]
        try:
            require_data_kind(loader_class, "document")
        except DataKindMismatchError as e:
            raise InvalidDocumentUploadError(str(e)) from e
        return loader_class

    @staticmethod
    def _clean_folder_name(folder_name: Optional[str]) -> Optional[str]:
        """Strip a requested folder name and reject it when empty.

        Parameters
        ----------
        folder_name : Optional[str]
            Folder name from the request.

        Returns
        -------
        Optional[str]
            The stripped name, or None when no folder was requested.

        Raises
        ------
        InvalidDocumentUploadError
            422 case: the name has no visible characters.
        """
        if folder_name is None:
            return None
        clean_name = folder_name.strip()
        if not clean_name:
            raise InvalidDocumentUploadError("Folder name cannot be empty")
        if not _has_visible_characters(clean_name):
            raise InvalidDocumentUploadError(
                "Folder name must contain a visible character"
            )
        return clean_name

    @staticmethod
    def _existing_folder(db: "Session", folder_id: Optional[int]) -> Optional[Folder]:
        """Fetch the folder a document goes into, if any.

        Parameters
        ----------
        db : Session
            An open session.
        folder_id : Optional[int]
            Requested folder, or None for a loose document.

        Returns
        -------
        Optional[Folder]
            The folder row, or None.

        Raises
        ------
        FolderNotFoundError
            404 case: there is no folder with that id.
        """
        if folder_id is None:
            return None
        folder = db.get(Folder, folder_id)
        if folder is None:
            raise FolderNotFoundError("Folder not found")
        return folder

    @staticmethod
    def _ensure_unique_in_batch(prepared: List[_PreparedUpload]) -> None:
        """Reject names repeated inside the batch.

        Parameters
        ----------
        prepared : List[_PreparedUpload]
            The validated uploads.

        Raises
        ------
        DocumentUploadConflictError
            409 case: a name appears more than once.
        """
        seen: Set[str] = set()
        for item in prepared:
            if item.name in seen:
                raise DocumentUploadConflictError(
                    f"The document name '{item.name}' appears more than once"
                )
            seen.add(item.name)

    def _ensure_names_free(
        self,
        db: "Session",
        prepared: List[_PreparedUpload],
        folder_name: Optional[str],
    ) -> None:
        """Check the folder and document names before anything is written.

        Parameters
        ----------
        db : Session
            An open session.
        prepared : List[_PreparedUpload]
            The validated uploads.
        folder_name : Optional[str]
            Folder to create, or None when the batch is loose.

        Raises
        ------
        DocumentUploadConflictError
            409 case: the folder name or a document name is stored already.
        """
        if folder_name is not None:
            taken_folder = db.execute(
                select(Folder.id).where(Folder.name == folder_name)
            ).scalar()
            if taken_folder:
                raise DocumentUploadConflictError(
                    f"A folder with the name '{folder_name}' already exists"
                )
        taken_names = self._stored_names(db, [item.name for item in prepared])
        if taken_names:
            raise DocumentUploadConflictError(
                f"A document with the name '{taken_names[0]}' already exists"
            )

    @staticmethod
    def _stored_names(db: "Session", names: List[str]) -> List[str]:
        """Return the names already stored, querying in bounded chunks.

        SQLite refuses a statement with too many bound parameters, so the
        lookup is split instead of failing on a very large batch.

        Parameters
        ----------
        db : Session
            An open session.
        names : List[str]
            Document names to look up.

        Returns
        -------
        List[str]
            The subset already present in the database.
        """
        stored: List[str] = []
        for chunk in name_chunks(names):
            stored.extend(
                db.execute(
                    select(DataDocument.name).where(DataDocument.name.in_(chunk))
                ).scalars()
            )
        return stored

    @staticmethod
    def _new_document(
        prepared: _PreparedUpload,
        folder: Optional[Folder],
        converter_pipeline: Optional[List[Any]],
    ) -> DataDocument:
        """Build a NOT_STARTED row for a validated upload.

        Parameters
        ----------
        prepared : _PreparedUpload
            The validated upload.
        folder : Optional[Folder]
            Folder receiving the document, or None for a loose one.
        converter_pipeline : Optional[List[Any]]
            Normalized pipeline the parse applies, or None.

        Returns
        -------
        DataDocument
            The row, not yet added to a session.
        """
        return DataDocument(
            name=prepared.name,
            file_name=prepared.file_name,
            file_type=prepared.file_type,
            file_hash="",
            file_path="",
            dataloader=prepared.dataloader,
            dataloader_params=prepared.dataloader_params,
            converter_pipeline=converter_pipeline,
            content_counts={},
            folder=folder,
            status=DocumentStatus.NOT_STARTED,
        )

    @staticmethod
    def _result(folder: Optional[Folder], documents: List[DataDocument]) -> BatchResult:
        """Snapshot the flushed rows as response models.

        Building the schemas before the commit keeps the session open for the
        attribute access and keeps the endpoint from doing one refresh per
        document.

        Parameters
        ----------
        folder : Optional[Folder]
            The folder added to the session, or None.
        documents : List[DataDocument]
            The documents added to the session.

        Returns
        -------
        BatchResult
            The response models.
        """
        return BatchResult(
            folder=FolderSchema.model_validate(folder) if folder is not None else None,
            documents=[
                DataDocumentSchema.model_validate(document) for document in documents
            ],
        )

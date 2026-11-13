"""Import a ``.dashai`` file as a new generative session.

Importing checks the manifest and validates the configuration the same way
creating a session does, then adds one new session row and its first
parameter history entry. Nothing that already exists is changed: a name that
clashes gets a number. A model that still has to be downloaded does not stop
the import; it is reported so the app can ask for the download.

A file with a conversation adds its processes too. Their media files are
copied into IMAGES_PATH under new names. A RAG file adds its documents to the
Data module and links them to the new session, which then waits to be
indexed. A document that this DashAI already has, from the same file parsed
the same way, is reused instead of copied. The conversation's citations are
pointed at the documents' new ids. A failure halfway removes every row and
file the import created.
"""

import json
import re
import shutil
import tempfile
import uuid
import warnings
import zipfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from DashAI.back.core.utils import MultilingualString
from DashAI.back.dependencies.downloads.nested import missing_downloads
from DashAI.back.generative_package.export import (
    CONTENTS,
    DOCUMENT_FIELDS,
    DOCUMENTS_ENTRY,
    GENERATIVE_FORMAT_VERSION,
    KIND_GENERATIVE_SESSION,
    MEDIA_ENTRY,
    MEDIA_TYPES,
    SESSION_ENTRY,
    SESSION_FIELDS,
    component_names,
)
from DashAI.back.model_package.manifest import (
    MANIFEST_ENTRY,
    MissingComponentError,
    ModelPackageError,
    check_manifest,
)
from DashAI.back.session_package.load import _date, safe_extract, unique_name

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

NOT_A_GENERATIVE_SESSION = "{path} is not a DashAI generative session file"
# A chunk reference, "<document_id>_<position>", as RAG answers store them.
CHUNK_REF = re.compile(r"^(\d+)_(\d+)$")
# RAG output rows whose chunk references name documents.
CITATION_TYPES = ("Dict", "Trace")


class InvalidSessionParametersError(ModelPackageError):
    """The configuration in the file is not valid for this DashAI."""

    code = "invalid_parameters"


def _read_package(path: Union[str, Path], workdir: Path):
    """Extract the file, check its manifest and return the recipe and notes.

    Raises
    ------
    ModelPackageError
        If the file is not a generative session file, is unsafe, is newer
        than this DashAI reads or needs a plugin that is not installed.
    """
    try:
        with zipfile.ZipFile(path) as archive:
            safe_extract(archive, workdir)
        manifest = json.loads((workdir / MANIFEST_ENTRY).read_text(encoding="utf-8"))
    except (
        zipfile.BadZipFile,
        FileNotFoundError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as e:
        raise ModelPackageError(NOT_A_GENERATIVE_SESSION.format(path=path)) from e
    if not isinstance(manifest, dict):
        raise ModelPackageError(NOT_A_GENERATIVE_SESSION.format(path=path))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        check_manifest(manifest, KIND_GENERATIVE_SESSION, GENERATIVE_FORMAT_VERSION)
    notes = [str(warning.message) for warning in caught]
    unknown = [part for part in manifest.get("contents", []) if part not in CONTENTS]
    if unknown:
        notes.append(
            "This file has parts this DashAI does not know and skipped: "
            + ", ".join(unknown)
        )

    try:
        recipe = json.loads((workdir / SESSION_ENTRY).read_text(encoding="utf-8"))
        session = recipe["session"]
        missing = [field for field in SESSION_FIELDS if field not in session]
        if missing or not isinstance(session["parameters"], dict):
            raise KeyError(missing)
        for process in recipe.get("processes") or []:
            for row in [*process["input"], *process["output"]]:
                _check_row(row, workdir)
        for document in recipe.get("documents") or []:
            _check_document(document, workdir)
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError) as e:
        raise ModelPackageError(NOT_A_GENERATIVE_SESSION.format(path=path)) from e
    return recipe, notes


def _check_row(row: Dict[str, Any], workdir: Path) -> None:
    """Refuse a conversation row the importer could not store safely.

    A media row must name a file inside the ``media`` folder of the package;
    any other row must hold its content as text.

    Raises
    ------
    KeyError
        If the row is malformed or its media file is missing or elsewhere.
    """
    if not isinstance(row["data_type"], str):
        raise KeyError("data_type")
    if row["data_type"] not in MEDIA_TYPES:
        if not isinstance(row["data"], str):
            raise KeyError("data")
        return
    media_root = (workdir / MEDIA_ENTRY).resolve()
    source = (workdir / row["media_entry"]).resolve()
    if not source.is_relative_to(media_root) or not source.is_file():
        raise KeyError("media_entry")


def _check_document(document: Dict[str, Any], workdir: Path) -> None:
    """Refuse a document entry the importer could not store safely.

    Its folder must sit inside the ``documents`` folder of the package and
    hold the parsed content the Data module reads.

    Raises
    ------
    KeyError
        If a field is missing or the folder is missing or elsewhere.
    """
    missing = [f for f in (*DOCUMENT_FIELDS, "ref", "entry") if f not in document]
    if missing or not isinstance(document["name"], str):
        raise KeyError(missing or "name")
    documents_root = (workdir / DOCUMENTS_ENTRY).resolve()
    folder = (workdir / document["entry"]).resolve()
    if not folder.is_relative_to(documents_root) or not (folder / "document").is_dir():
        raise KeyError("entry")


def _reusable_documents(
    documents: List[Dict[str, Any]], session_factory: "sessionmaker"
) -> Dict[Any, int]:
    """Documents of the file this DashAI already has, by their ``ref``.

    One is reused only when a finished document has the same source file
    (``file_hash``) parsed by the same dataloader, with the same parameters
    and converter pipeline: the same file parsed another way holds other
    content.
    """
    from DashAI.back.core.enums.status import DocumentStatus
    from DashAI.back.dependencies.database.models import DataDocument

    hashes = {d["file_hash"] for d in documents if d["file_hash"]}
    if not hashes:
        return {}
    with session_factory() as db:
        candidates = (
            db.query(DataDocument)
            .filter(
                DataDocument.file_hash.in_(hashes),
                DataDocument.status == DocumentStatus.FINISHED,
            )
            .order_by(DataDocument.id)
            .all()
        )
        reusable = {}
        for document in documents:
            match = next(
                (
                    c.id
                    for c in candidates
                    if c.file_hash == document["file_hash"]
                    and c.dataloader == document["dataloader"]
                    and (c.dataloader_params or {})
                    == (document["dataloader_params"] or {})
                    and (c.converter_pipeline or [])
                    == (document["converter_pipeline"] or [])
                ),
                None,
            )
            if match is not None:
                reusable[document["ref"]] = match
        return reusable


def _remap_ref(ref: str, id_map: Dict[str, int]) -> str:
    """Point a chunk reference at its document's new id.

    A document the file did not carry, because it had been deleted where the
    session was exported, keeps a reference that no new document can take,
    so its citation never names an unrelated document here.
    """
    match = CHUNK_REF.match(ref)
    if match is None:
        return ref
    old_id, position = match.groups()
    if old_id in id_map:
        return f"{id_map[old_id]}_{position}"
    return f"missing-{old_id}_{position}"


def _remap_document_id(value: Any, id_map: Dict[str, int]) -> Any:
    """The new id of a cited document, or None if the file did not carry it.

    None is how a citation of a deleted document is stored, so the chat shows
    it without offering to open it.
    """
    if value is None or isinstance(value, bool):
        return value
    return id_map.get(str(value))


def _remap_trace(node: Any, id_map: Dict[str, int]) -> Any:
    """A copy of a retrieval trace with its chunk references remapped.

    Retrievers, plugins included, put references wherever their technique
    needs (``chunks`` lists, ``scores`` keys), so every string shaped like a
    reference is remapped, except the text of a query.
    """
    if isinstance(node, dict):
        return {
            _remap_ref(key, id_map): (
                value if key == "query" else _remap_trace(value, id_map)
            )
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [_remap_trace(item, id_map) for item in node]
    if isinstance(node, str):
        return _remap_ref(node, id_map)
    return node


def remap_citations(data_type: str, data: str, id_map: Dict[str, int]) -> str:
    """Point the citations of a RAG output row at the new document ids.

    Parameters
    ----------
    data_type : str
        The row's type; only ``Dict`` and ``Trace`` rows cite documents.
    data : str
        The row's JSON content.
    id_map : dict of str to int
        The document ids of the exporting DashAI, as strings, to their ids
        here.

    Returns
    -------
    str
        The content with every reference and document id remapped, or as it
        was when it is not JSON of the expected shape.
    """
    if data_type not in CITATION_TYPES:
        return data
    try:
        parsed = json.loads(data)
    except (TypeError, ValueError):
        return data
    if data_type == "Dict":
        if not isinstance(parsed, dict):
            return data
        remapped = {}
        for ref, info in parsed.items():
            if isinstance(info, dict) and "document_id" in info:
                info = {
                    **info,
                    "document_id": _remap_document_id(info["document_id"], id_map),
                }
            remapped[_remap_ref(ref, id_map)] = info
        return json.dumps(remapped, ensure_ascii=False)
    return json.dumps(_remap_trace(parsed, id_map), ensure_ascii=False)


def _check_components(recipe_session: Dict[str, Any], component_registry: Any) -> None:
    for name in component_names(recipe_session):
        if name not in component_registry:
            raise MissingComponentError(
                f"This session needs '{name}', which this DashAI does not have. "
                "Install the plugin that provides it and try again.",
                component=name,
            )


def _validated_parameters(
    recipe_session: Dict[str, Any],
    db: Any,
    component_registry: Any,
    language: str,
) -> Dict[str, Any]:
    """The parameters as creating the session would store them.

    Runs the same checks as ``POST /generative-session/`` except the download
    gate: the task and the model must be generative, a RAG configuration is
    normalized and every model parameter must match its schema.

    Raises
    ------
    InvalidSessionParametersError
        If the task or model is not generative or a parameter is invalid.
    """
    from DashAI.back.models.base_generative_model import BaseGenerativeModel
    from DashAI.back.models.RAG.exceptions.base import RAGWorkflowError
    from DashAI.back.services.RAG.session_validation_service import (
        SessionValidationService,
    )
    from DashAI.back.tasks.base_generative_task import BaseGenerativeTask
    from DashAI.back.tasks.RAG_task import RAGTask

    model_class = component_registry[recipe_session["model_name"]]["class"]
    task_class = component_registry[recipe_session["task_name"]]["class"]
    if not issubclass(model_class, BaseGenerativeModel) or not issubclass(
        task_class, BaseGenerativeTask
    ):
        raise InvalidSessionParametersError(
            "This file does not describe a generative session."
        )

    parameters = dict(recipe_session["parameters"])
    try:
        if task_class == RAGTask:
            parameters = SessionValidationService(
                db, component_registry
            ).prepare_RAG_params(parameters, language)
        model_class.SCHEMA.model_validate(parameters)
    except (ValueError, RAGWorkflowError) as e:
        raise InvalidSessionParametersError(
            f"The session configuration is not valid in this DashAI: {e}",
            reason=str(e),
        ) from e
    return parameters


def _display_name(component_registry: Any, name: str, language: str) -> str:
    display = component_registry[name].get("display_name")
    if isinstance(display, MultilingualString):
        return display.get(language)
    return display or name


def _missing_downloads(
    model_name: str,
    parameters: Dict[str, Any],
    component_registry: Any,
    language: str,
) -> List[Dict[str, str]]:
    """The model and nested components that must be downloaded before use."""
    names = [model_name] + [
        m["name"] for m in missing_downloads(parameters, component_registry)
    ]
    missing: List[str] = []
    for name in dict.fromkeys(names):
        component_class = component_registry[name]["class"]
        if not getattr(component_class, "REQUIRES_DOWNLOAD", False):
            continue
        if component_registry.refresh_download_status(name):
            continue
        missing.append(name)
    return [
        {
            "name": name,
            "display_name": _display_name(component_registry, name, language),
        }
        for name in missing
    ]


def import_generative_package(
    path: Union[str, Path],
    session_factory: "sessionmaker",
    component_registry: Any,
    language: Optional[str] = "en",
    images_path: Optional[Path] = None,
    documents_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Create a new generative session from a ``.dashai`` file.

    ``images_path`` is where the media files of a conversation are copied,
    and ``documents_path`` where the documents of a RAG session are; each is
    required for a file that carries them.

    Returns
    -------
    dict
        ``session_id``, its ``task_name``, the final ``session_name``, whether
        it was ``renamed``, version ``warnings``, the ``message_count`` it
        brought, its ``document_count`` and how many of those documents were
        already here (``reused_document_count``), and ``needs_download``: the
        model
        and nested components (``name`` and ``display_name`` in ``language``)
        that must be downloaded before the session can be used.

    Raises
    ------
    ModelPackageError
        If the file is not a DashAI generative session, is unsafe, is newer
        than this DashAI reads, needs a missing plugin or component, or holds
        a configuration this DashAI rejects.
    """
    import os

    from DashAI.back.core.enums.status import DocumentStatus, RunStatus
    from DashAI.back.dependencies.database.models import (
        DataDocument,
        GenerativeProcess,
        GenerativeSession,
        GenerativeSessionParameterHistory,
        ProcessData,
        RAGSessionDocument,
    )
    from DashAI.back.models.RAG.RAG_constants import RAG_PARAM_DOCUMENTS
    from DashAI.back.tasks.RAG_task import RAGTask

    language = language or "en"
    workdir = Path(tempfile.mkdtemp(prefix="dashai-import-"))
    # Every file below gets a fresh uuid name, so removing them on failure
    # never touches anything that existed before the import.
    created: List[Path] = []
    try:
        recipe, notes = _read_package(path, workdir)
        recipe_session = recipe["session"]
        _check_components(recipe_session, component_registry)
        processes = recipe.get("processes") or []
        is_rag = component_registry[recipe_session["task_name"]]["class"] == RAGTask
        documents = (recipe.get("documents") or []) if is_rag else []
        reused = _reusable_documents(documents, session_factory)

        try:
            # Files are copied before the transaction opens, as the session
            # importer does, so a long copy never holds the SQLite write lock.
            media_names: Dict[str, str] = {}
            for process in processes:
                for row in [*process["input"], *process["output"]]:
                    if row["data_type"] not in MEDIA_TYPES:
                        continue
                    source = workdir / row["media_entry"]
                    name = f"{uuid.uuid4()}{source.suffix}"
                    target = Path(images_path) / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    created.append(target)
                    shutil.copy2(source, target)
                    media_names[row["media_entry"]] = name

            document_folders: Dict[Any, Path] = {}
            for document in documents:
                if document["ref"] in reused:
                    continue
                folder = Path(documents_path) / str(uuid.uuid4())
                created.append(folder)
                shutil.copytree(workdir / document["entry"], folder)
                document_folders[document["ref"]] = folder

            with session_factory() as db:
                try:
                    parameters = _validated_parameters(
                        recipe_session, db, component_registry, language
                    )
                    taken = {name for (name,) in db.query(GenerativeSession.name)}
                    session_name = unique_name(recipe_session["name"], taken)
                    now = datetime.now()

                    document_ids = dict(reused)
                    taken_documents = {n for (n,) in db.query(DataDocument.name)}
                    for document in documents:
                        if document["ref"] in reused:
                            continue
                        name = unique_name(document["name"], taken_documents)
                        taken_documents.add(name)
                        row = DataDocument(
                            **{
                                field: document[field]
                                for field in DOCUMENT_FIELDS
                                if field != "name"
                            },
                            name=name,
                            file_path=os.path.realpath(
                                document_folders[document["ref"]]
                            ),
                            status=DocumentStatus.FINISHED,
                        )
                        db.add(row)
                        db.flush()
                        document_ids[document["ref"]] = row.id
                    if is_rag:
                        parameters[RAG_PARAM_DOCUMENTS] = sorted(
                            set(document_ids.values())
                        )
                    citation_map = {
                        str(ref): new_id for ref, new_id in document_ids.items()
                    }
                    session = GenerativeSession(
                        name=session_name,
                        description=recipe_session["description"],
                        task_name=recipe_session["task_name"],
                        model_name=recipe_session["model_name"],
                        parameters=parameters,
                        created=now,
                        last_modified=now,
                    )
                    db.add(session)
                    db.flush()
                    db.add_all(
                        RAGSessionDocument(
                            session_id=session.id, data_document_id=document_id
                        )
                        for document_id in sorted(set(document_ids.values()))
                    )
                    db.add(
                        GenerativeSessionParameterHistory(
                            session_id=session.id,
                            parameters=parameters,
                            model_name=session.model_name,
                            modified_at=now,
                        )
                    )
                    for entry in processes:
                        process = GenerativeProcess(
                            session_id=session.id,
                            status=RunStatus.FINISHED,
                            start_time=_date(entry.get("start_time")),
                            end_time=_date(entry.get("end_time")),
                        )
                        if entry.get("created"):
                            process.created = _date(entry["created"])
                        db.add(process)
                        db.flush()
                        for is_input, rows in (
                            (True, entry["input"]),
                            (False, entry["output"]),
                        ):
                            db.add_all(
                                ProcessData(
                                    process_id=process.id,
                                    is_input=is_input,
                                    data_type=row["data_type"],
                                    data=(
                                        media_names[row["media_entry"]]
                                        if row["data_type"] in MEDIA_TYPES
                                        else remap_citations(
                                            row["data_type"],
                                            row["data"],
                                            citation_map,
                                        )
                                        if is_rag
                                        else row["data"]
                                    ),
                                )
                                for row in rows
                            )
                    db.commit()
                    session_id = session.id
                except BaseException:
                    db.rollback()
                    raise
        except BaseException:
            for created_path in reversed(created):
                if created_path.is_dir():
                    shutil.rmtree(created_path, ignore_errors=True)
                else:
                    created_path.unlink(missing_ok=True)
            raise
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    return {
        "session_id": session_id,
        "task_name": recipe_session["task_name"],
        "session_name": session_name,
        "renamed": session_name != recipe_session["name"],
        "warnings": notes,
        "message_count": len(processes),
        "document_count": len(documents),
        "reused_document_count": len(reused),
        "needs_download": _missing_downloads(
            recipe_session["model_name"], parameters, component_registry, language
        ),
    }

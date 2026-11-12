"""Import a ``.dashai`` file as a new generative session.

Importing checks the manifest and validates the configuration the same way
creating a session does, then adds one new session row and its first
parameter history entry. Nothing that already exists is changed: a name that
clashes gets a number. A model that still has to be downloaded does not stop
the import; it is reported so the app can ask for the download.

A file with a conversation adds its processes too. Their media files are
copied into IMAGES_PATH under new names; a failure halfway removes every row
and file the import created.
"""

import json
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
) -> Dict[str, Any]:
    """Create a new generative session from a ``.dashai`` file.

    ``images_path`` is where the media files of a conversation are copied;
    it is required for a file that carries one.

    Returns
    -------
    dict
        ``session_id``, its ``task_name``, the final ``session_name``, whether
        it was ``renamed``, version ``warnings``, the ``message_count`` it
        brought and ``needs_download``: the model
        and nested components (``name`` and ``display_name`` in ``language``)
        that must be downloaded before the session can be used.

    Raises
    ------
    ModelPackageError
        If the file is not a DashAI generative session, is unsafe, is newer
        than this DashAI reads, needs a missing plugin or component, or holds
        a configuration this DashAI rejects.
    """
    from DashAI.back.core.enums.status import RunStatus
    from DashAI.back.dependencies.database.models import (
        GenerativeProcess,
        GenerativeSession,
        GenerativeSessionParameterHistory,
        ProcessData,
    )

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

            with session_factory() as db:
                try:
                    parameters = _validated_parameters(
                        recipe_session, db, component_registry, language
                    )
                    taken = {name for (name,) in db.query(GenerativeSession.name)}
                    session_name = unique_name(recipe_session["name"], taken)
                    now = datetime.now()
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
        "needs_download": _missing_downloads(
            recipe_session["model_name"], parameters, component_registry, language
        ),
    }

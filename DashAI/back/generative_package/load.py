"""Import a ``.dashai`` file as a new generative session.

Importing checks the manifest and validates the configuration the same way
creating a session does, then adds one new session row and its first
parameter history entry. Nothing that already exists is changed: a name that
clashes gets a number. A model that still has to be downloaded does not stop
the import; it is reported so the app can ask for the download.
"""

import json
import shutil
import tempfile
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
from DashAI.back.session_package.load import safe_extract, unique_name

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
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError) as e:
        raise ModelPackageError(NOT_A_GENERATIVE_SESSION.format(path=path)) from e
    return recipe, notes


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
) -> Dict[str, Any]:
    """Create a new generative session from a ``.dashai`` file.

    Returns
    -------
    dict
        ``session_id``, its ``task_name``, the final ``session_name``, whether it was
        ``renamed``, version ``warnings`` and ``needs_download``: the model
        and nested components (``name`` and ``display_name`` in ``language``)
        that must be downloaded before the session can be used.

    Raises
    ------
    ModelPackageError
        If the file is not a DashAI generative session, is unsafe, is newer
        than this DashAI reads, needs a missing plugin or component, or holds
        a configuration this DashAI rejects.
    """
    from DashAI.back.dependencies.database.models import (
        GenerativeSession,
        GenerativeSessionParameterHistory,
    )

    language = language or "en"
    workdir = Path(tempfile.mkdtemp(prefix="dashai-import-"))
    try:
        recipe, notes = _read_package(path, workdir)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    recipe_session = recipe["session"]
    _check_components(recipe_session, component_registry)

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
            db.commit()
            session_id = session.id
        except BaseException:
            db.rollback()
            raise

    return {
        "session_id": session_id,
        "task_name": recipe_session["task_name"],
        "session_name": session_name,
        "renamed": session_name != recipe_session["name"],
        "warnings": notes,
        "needs_download": _missing_downloads(
            recipe_session["model_name"], parameters, component_registry, language
        ),
    }

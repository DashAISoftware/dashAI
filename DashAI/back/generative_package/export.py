"""Build a ``.dashai`` file from a generative session.

The file is a zip with the session configuration as readable JSON: its task,
its model and the model parameters. IDs stay out, since importing assigns new
ones. A RAG session travels without its documents for now, so its document
list is written empty.

When asked for, the file also carries the conversation: every finished
process with its input and output rows. A media row (an image, audio or
video) stores its file under ``media/`` in the zip instead of its path on
disk, so the importer never reads a path from the file.
"""

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from DashAI.back.core.component_validation import find_component_refs
from DashAI.back.model_package.export import _zip_directory
from DashAI.back.model_package.manifest import (
    MANIFEST_ENTRY,
    ModelPackageError,
    current_versions,
    plugin_distributions,
)
from DashAI.back.models.RAG.RAG_constants import RAG_PARAM_DOCUMENTS
from DashAI.back.session_package.export import session_filename

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

GENERATIVE_FORMAT_VERSION = 1
KIND_GENERATIVE_SESSION = "generative_session"
SESSION_ENTRY = "generative_session.json"
MEDIA_ENTRY = "media"
CONTENT_SESSION = "session"
CONTENT_CONVERSATION = "conversation"
CONTENTS = [CONTENT_SESSION, CONTENT_CONVERSATION]
SESSION_FIELDS = ("name", "description", "task_name", "model_name", "parameters")
# Row types whose ``data`` names a file under IMAGES_PATH rather than holding
# the content itself.
MEDIA_TYPES = frozenset({"Image", "Audio", "Video"})


class GenerativeSessionNotFoundError(ModelPackageError):
    """The generative session to export does not exist."""


def generative_session_filename(session_name: str) -> str:
    """Turn a session name into a safe file name with the ``.dashai`` extension."""
    return session_filename(session_name)


def component_names(recipe_session: Dict[str, Any]) -> List[str]:
    """Every component the session needs: task, model and nested components.

    Nested components are the ``{"component": ..., "params": ...}`` values in
    the parameters, such as the retriever or the generation model of a RAG
    session. Each name appears once, in the order found.
    """
    names = [recipe_session["task_name"], recipe_session["model_name"]]
    names += [name for _, name, _ in find_component_refs(recipe_session["parameters"])]
    return list(dict.fromkeys(names))


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _media_path(row, images_path: Path) -> Optional[Path]:
    """The file a media row points to, or None if it is not on disk.

    ``data`` is a name relative to IMAGES_PATH, or an absolute path for tasks
    that store one; joining keeps an absolute path as it is.
    """
    path = Path(os.path.join(images_path, row.data))
    return path if path.is_file() else None


def _finished_processes(db, session_id: int) -> List[Any]:
    from DashAI.back.core.enums.status import RunStatus
    from DashAI.back.dependencies.database.models import GenerativeProcess

    return (
        db.query(GenerativeProcess)
        .filter(
            GenerativeProcess.session_id == session_id,
            GenerativeProcess.status == RunStatus.FINISHED,
        )
        .order_by(GenerativeProcess.id)
        .all()
    )


def export_preview(
    session_id: int, session_factory: "sessionmaker", images_path: Path
) -> Dict[str, Any]:
    """What the export dialog shows: the conversation and what it weighs.

    Returns
    -------
    dict
        ``session_name``, ``message_count`` (finished exchanges that would be
        exported), ``unfinished_count`` (still running or failed, never
        exported) and ``media_size_bytes`` (files the conversation carries).

    Raises
    ------
    GenerativeSessionNotFoundError
        If the session does not exist.
    """
    from DashAI.back.dependencies.database.models import (
        GenerativeProcess,
        GenerativeSession,
    )

    with session_factory() as db:
        session = db.get(GenerativeSession, session_id)
        if session is None:
            raise GenerativeSessionNotFoundError(
                f"Generative session {session_id} does not exist."
            )
        finished = _finished_processes(db, session_id)
        total = (
            db.query(GenerativeProcess)
            .filter(GenerativeProcess.session_id == session_id)
            .count()
        )
        media_size = 0
        for process in finished:
            for row in [*process.input, *process.output]:
                if row.data_type in MEDIA_TYPES:
                    path = _media_path(row, images_path)
                    media_size += path.stat().st_size if path else 0
        return {
            "session_name": session.name,
            "message_count": len(finished),
            "unfinished_count": total - len(finished),
            "media_size_bytes": media_size,
        }


def _conversation(
    db, session_id: int, images_path: Path, staging: Path
) -> List[Dict[str, Any]]:
    """The finished processes as recipe entries, copying their media files.

    A media row whose file is gone is left out: the importer could only point
    it at nothing.
    """
    processes = []
    media_count = 0
    for process in _finished_processes(db, session_id):
        entry = {
            "created": _iso(process.created),
            "start_time": _iso(process.start_time),
            "end_time": _iso(process.end_time),
            "input": [],
            "output": [],
        }
        for side, rows in (("input", process.input), ("output", process.output)):
            for row in rows:
                if row.data_type not in MEDIA_TYPES:
                    entry[side].append({"data": row.data, "data_type": row.data_type})
                    continue
                source = _media_path(row, images_path)
                if source is None:
                    continue
                media_entry = f"{MEDIA_ENTRY}/{media_count}{source.suffix}"
                media_count += 1
                target = staging / media_entry
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                entry[side].append(
                    {"data_type": row.data_type, "media_entry": media_entry}
                )
        processes.append(entry)
    return processes


def build_generative_package(
    session_id: int,
    destination: Path,
    session_factory: "sessionmaker",
    component_registry: Any,
    include_conversation: bool = False,
    images_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Write a ``.dashai`` file for a generative session.

    Parameters
    ----------
    include_conversation : bool
        Whether to add the finished processes and their media files.
    images_path : Path, optional
        Where the media files of the conversation live. Required when
        ``include_conversation`` is true.

    Returns
    -------
    dict
        The manifest written into the file.

    Raises
    ------
    GenerativeSessionNotFoundError
        If the session does not exist.
    """
    from DashAI.back.dependencies.database.models import GenerativeSession

    with tempfile.TemporaryDirectory(prefix="dashai-generative-") as staging_dir:
        staging = Path(staging_dir)
        with session_factory() as db:
            session = db.get(GenerativeSession, session_id)
            if session is None:
                raise GenerativeSessionNotFoundError(
                    f"Generative session {session_id} does not exist."
                )
            recipe_session = {
                field: getattr(session, field) for field in SESSION_FIELDS
            }
            processes = (
                _conversation(db, session_id, Path(images_path), staging)
                if include_conversation
                else None
            )

        parameters = dict(recipe_session["parameters"] or {})
        if RAG_PARAM_DOCUMENTS in parameters:
            parameters[RAG_PARAM_DOCUMENTS] = []
        recipe_session["parameters"] = parameters

        provider_classes = [
            component_registry[name]["class"]
            for name in component_names(recipe_session)
            if name in component_registry
        ]

        recipe = {"session": recipe_session}
        contents = [CONTENT_SESSION]
        if processes is not None:
            recipe["processes"] = processes
            contents.append(CONTENT_CONVERSATION)
        (staging / SESSION_ENTRY).write_text(json.dumps(recipe, indent=2))

        manifest = {
            "format_version": GENERATIVE_FORMAT_VERSION,
            "kind": KIND_GENERATIVE_SESSION,
            "versions": current_versions(),
            "plugins": plugin_distributions(provider_classes),
            "contents": contents,
            "info": {
                "session_name": recipe_session["name"],
                "task_name": recipe_session["task_name"],
                "model_name": recipe_session["model_name"],
                "message_count": len(processes) if processes is not None else 0,
                "exported_at": datetime.now().isoformat(),
            },
        }
        (staging / MANIFEST_ENTRY).write_text(json.dumps(manifest, indent=2))
        _zip_directory(staging, Path(destination))

    return manifest

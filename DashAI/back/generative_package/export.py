"""Build a ``.dashai`` file from a generative session.

The file is a zip with the session configuration as readable JSON: its task,
its model and the model parameters. IDs stay out, since importing assigns new
ones. A RAG session travels without its documents for now, so its document
list is written empty.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

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
CONTENTS = ["session"]
SESSION_FIELDS = ("name", "description", "task_name", "model_name", "parameters")


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


def build_generative_package(
    session_id: int,
    destination: Path,
    session_factory: "sessionmaker",
    component_registry: Any,
) -> Dict[str, Any]:
    """Write a ``.dashai`` file with the configuration of a generative session.

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

    with session_factory() as db:
        session = db.get(GenerativeSession, session_id)
        if session is None:
            raise GenerativeSessionNotFoundError(
                f"Generative session {session_id} does not exist."
            )
        recipe_session = {field: getattr(session, field) for field in SESSION_FIELDS}

    parameters = dict(recipe_session["parameters"] or {})
    if RAG_PARAM_DOCUMENTS in parameters:
        parameters[RAG_PARAM_DOCUMENTS] = []
    recipe_session["parameters"] = parameters

    provider_classes = [
        component_registry[name]["class"]
        for name in component_names(recipe_session)
        if name in component_registry
    ]

    with tempfile.TemporaryDirectory(prefix="dashai-generative-") as staging_dir:
        staging = Path(staging_dir)
        recipe = {"session": recipe_session}
        (staging / SESSION_ENTRY).write_text(json.dumps(recipe, indent=2))

        manifest = {
            "format_version": GENERATIVE_FORMAT_VERSION,
            "kind": KIND_GENERATIVE_SESSION,
            "versions": current_versions(),
            "plugins": plugin_distributions(provider_classes),
            "contents": CONTENTS,
            "info": {
                "session_name": recipe_session["name"],
                "task_name": recipe_session["task_name"],
                "model_name": recipe_session["model_name"],
                "exported_at": datetime.now().isoformat(),
            },
        }
        (staging / MANIFEST_ENTRY).write_text(json.dumps(manifest, indent=2))
        _zip_directory(staging, Path(destination))

    return manifest

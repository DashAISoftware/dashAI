"""rename the LLM-evaluated retrieval family to agentic

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-11-10 00:00:00

The retrieval family that asks a language model to judge a retrieval pool was
renamed in code:

* ``LLMEvaluatedRetriever`` -> ``AgenticRetriever``
* ``LLMEvaluatedDepthRetriever`` -> ``AgenticSingleRetriever``
* ``LLMEvaluatedEnsembleRetriever`` -> ``AgenticEnsembleRetriever``
* ``LLMFilterRetriever`` -> ``AgenticRerankerRetriever``
* the retrieval-sufficiency prompts -> the agentic retriever prompts
* the LLM filter prompts -> the agentic reranker prompts

Component names are persisted, so the migration rewrites the retriever class
names, the prompt class names (recomputing the class-aware ``parameters_hash``
and the built-in default display names) and every nested ``{"component": ...}``
or ``{"class_name": ...}`` reference stored in the session, pipeline and
parameter-history JSON blobs.

Downgrade reverses the rewrites. It is lossy for a default prompt row a user
renamed after the upgrade: the old display name is only restored when the row
still carries the name the upgrade wrote.
"""

import hashlib
import json
from collections.abc import Mapping
from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, Sequence[str], None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

#: Retriever component renames (persisted in ``rag_retriever.class_name``).
_RETRIEVER_RENAMES = {
    "LLMEvaluatedDepthRetriever": "AgenticSingleRetriever",
    "LLMEvaluatedEnsembleRetriever": "AgenticEnsembleRetriever",
    "LLMFilterRetriever": "AgenticRerankerRetriever",
}

#: Prompt component renames (persisted in ``rag_prompt.class_name``).
_PROMPT_RENAMES = {
    "RetrievalSufficiencyPrompt": "AgenticRetrieverPrompt",
    "CustomRetrievalSufficiencyPrompt": "CustomAgenticRetrieverPrompt",
    "DefaultRetrievalSufficiencyPrompt": "DefaultAgenticRetrieverPrompt",
    "LLMFilterPrompt": "AgenticRerankerPrompt",
    "CustomLLMFilterPrompt": "CustomAgenticRerankerPrompt",
    "DefaultLLMFilterPrompt": "DefaultAgenticRerankerPrompt",
}

#: Display name the built-in default rows of each renamed class must carry.
_DEFAULT_PROMPT_NAMES = {
    "DefaultRetrievalSufficiencyPrompt": "Default Agentic Retriever Prompt",
    "DefaultLLMFilterPrompt": "Default Agentic Reranker Prompt",
}

#: Display name each renamed default row had before the upgrade.
_LEGACY_DEFAULT_PROMPT_NAMES = {
    "DefaultRetrievalSufficiencyPrompt": "Default Retrieval Sufficiency Prompt",
    "DefaultLLMFilterPrompt": "Default LLM Filter Prompt",
}

_RETRIEVER_RENAMES_INVERSE = {new: old for old, new in _RETRIEVER_RENAMES.items()}
_PROMPT_RENAMES_INVERSE = {new: old for old, new in _PROMPT_RENAMES.items()}

#: Every component rename, used to rewrite the nested configuration references.
_ALL_RENAMES = {**_RETRIEVER_RENAMES, **_PROMPT_RENAMES}
_ALL_RENAMES_INVERSE = {**_RETRIEVER_RENAMES_INVERSE, **_PROMPT_RENAMES_INVERSE}

#: JSON columns that may hold nested component references.
_JSON_COLUMNS = (
    ("rag_retriever", "parameters"),
    ("rag_pipeline", "parameters"),
    ("generative_session", "parameters"),
    ("parameter_history", "parameters"),
    ("parameter_history", "prompt_bindings"),
)

#: Keys whose string value names a component.
_COMPONENT_REF_KEYS = frozenset({"component", "class_name"})


def _normalize(parameters: Any) -> Any:
    """Return a deterministically key-sorted copy of ``parameters``."""
    return json.loads(json.dumps(parameters, sort_keys=True))


def _prompt_hash(class_name: str, parameters: Any) -> str:
    """Build the class-aware prompt hash used by the application."""
    payload = {"class_name": class_name, "parameters": _normalize(parameters)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _load_json(raw: Any) -> Any:
    """Return a JSON value stored in a SQLite JSON column."""
    if isinstance(raw, (str, bytes, bytearray)):
        return json.loads(raw)
    return raw


def _rename_refs(value: Any, renames: Mapping[str, str]) -> tuple[Any, bool]:
    """Return ``value`` with every component reference renamed.

    Walks nested dictionaries and lists, so a ``prompt`` or ``children``
    reference nested anywhere in a stored configuration is rewritten too.

    Parameters
    ----------
    value : Any
        Stored JSON value.
    renames : Mapping[str, str]
        Old component name to new component name.

    Returns
    -------
    tuple of (Any, bool)
        The rewritten value and whether anything changed.
    """
    if isinstance(value, dict):
        renamed: dict[str, Any] = {}
        changed = False
        for key, item in value.items():
            if key in _COMPONENT_REF_KEYS and isinstance(item, str):
                new_name = renames.get(item, item)
                renamed[key] = new_name
                changed = changed or new_name != item
                continue
            new_item, child_changed = _rename_refs(item, renames)
            renamed[key] = new_item
            changed = changed or child_changed
        return renamed, changed
    if isinstance(value, list):
        renamed_items = []
        changed = False
        for item in value:
            new_item, child_changed = _rename_refs(item, renames)
            renamed_items.append(new_item)
            changed = changed or child_changed
        return renamed_items, changed
    return value, False


def _table_columns(connection, table: str) -> set:
    """Return the column names the migration connection sees for ``table``."""
    return {column["name"] for column in sa.inspect(connection).get_columns(table)}


def _rewrite_json_column(connection, table, column, renames) -> None:
    """Rename the component references stored in one JSON column."""
    rows = connection.execute(
        text(f"SELECT id, {column} FROM {table}")  # noqa: S608 - fixed identifiers
    ).fetchall()
    for row in rows:
        stored = _load_json(getattr(row, column))
        if stored is None:
            continue
        updated, changed = _rename_refs(stored, renames)
        if not changed:
            continue
        connection.execute(
            text(f"UPDATE {table} SET {column} = :value WHERE id = :id"),  # noqa: S608
            {"value": json.dumps(updated), "id": row.id},
        )


def _rewrite_json_columns(connection, renames) -> None:
    """Rename the component references of every stored configuration blob."""
    for table, column in _JSON_COLUMNS:
        if column not in _table_columns(connection, table):
            continue
        _rewrite_json_column(connection, table, column, renames)


def _rename_prompt_row(connection, row, class_name, display_name) -> None:
    """Persist a new class name, display name and content hash for one row."""
    parameters = _load_json(row.parameters)
    if parameters is None:
        parameters = {}
    normalized = _normalize(parameters)
    connection.execute(
        text(
            "UPDATE rag_prompt SET class_name = :class_name, name = :name, "
            "parameters = :parameters, parameters_hash = :parameters_hash "
            "WHERE id = :id"
        ),
        {
            "class_name": class_name,
            "name": display_name,
            "parameters": json.dumps(normalized),
            "parameters_hash": _prompt_hash(class_name, normalized),
            "id": row.id,
        },
    )


def upgrade() -> None:
    connection = op.get_bind()

    for old_name, new_name in _RETRIEVER_RENAMES.items():
        connection.execute(
            text(
                "UPDATE rag_retriever SET class_name = :new_name "
                "WHERE class_name = :old_name"
            ),
            {"new_name": new_name, "old_name": old_name},
        )

    # The mapping is injective and every new hash covers a class name no stored
    # row uses, so the global UNIQUE on ``parameters_hash`` cannot collide and
    # does not need to be dropped around the rewrites.
    rows = connection.execute(
        text("SELECT id, class_name, name, parameters FROM rag_prompt")
    ).fetchall()
    for row in rows:
        new_name = _PROMPT_RENAMES.get(row.class_name)
        if new_name is None:
            continue
        display_name = _DEFAULT_PROMPT_NAMES.get(row.class_name, row.name)
        _rename_prompt_row(connection, row, new_name, display_name)

    _rewrite_json_columns(connection, _ALL_RENAMES)


def downgrade() -> None:
    connection = op.get_bind()

    for new_name, old_name in _RETRIEVER_RENAMES_INVERSE.items():
        connection.execute(
            text(
                "UPDATE rag_retriever SET class_name = :old_name "
                "WHERE class_name = :new_name"
            ),
            {"new_name": new_name, "old_name": old_name},
        )

    rows = connection.execute(
        text("SELECT id, class_name, name, parameters FROM rag_prompt")
    ).fetchall()
    for row in rows:
        old_name = _PROMPT_RENAMES_INVERSE.get(row.class_name)
        if old_name is None:
            continue
        display_name = row.name
        expected_name = _DEFAULT_PROMPT_NAMES.get(old_name)
        if expected_name is not None and row.name == expected_name:
            display_name = _LEGACY_DEFAULT_PROMPT_NAMES[old_name]
        _rename_prompt_row(connection, row, old_name, display_name)

    _rewrite_json_columns(connection, _ALL_RENAMES_INVERSE)

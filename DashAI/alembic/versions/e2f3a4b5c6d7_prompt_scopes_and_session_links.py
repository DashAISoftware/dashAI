"""add prompt scopes, lineage and session-prompt links

Revision ID: e2f3a4b5c6d7
Revises: a7c1e2f3b4d5
Create Date: 2026-11-09 00:00:00

Prompts become a content-addressed catalog split into three scopes:

* ``is_default`` marks code-owned defaults, which are immutable.
* ``is_library`` marks user-owned rows, which are editable.
* neither flag marks an internal draft written by ``get_or_create``.

The parameters hash now covers ``class_name`` too, so the existing global
UNIQUE on ``parameters_hash`` can keep two prompt families with identical
parameters apart. ``based_on_id`` records fork lineage, and
``rag_session_prompt`` maps each session prompt slot to its row.
"""

import copy
import hashlib
import json
from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "a7c1e2f3b4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PROMPT_FK_NAME = "fk_rag_pipeline_prompt_id_rag_prompt"
_UNIQUE_NAME = "uq_rag_prompt_params_hash"


def _prompt_hash(class_name: str, parameters: Any) -> str:
    """Build the class-aware prompt hash used by the application."""
    payload = {"class_name": class_name, "parameters": parameters}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _parameters_hash(parameters: Any) -> str:
    """Hash ``parameters`` the way the previous version of the schema did."""
    return hashlib.sha256(json.dumps(parameters, sort_keys=True).encode()).hexdigest()


def _load_parameters(raw: Any) -> Any:
    """Return a JSON value stored in a SQLite JSON column."""
    if isinstance(raw, (str, bytes, bytearray)):
        return json.loads(raw)
    return raw


def _recompute_hashes(*, class_aware: bool) -> None:
    """Rewrite every ``rag_prompt.parameters_hash`` in Python.

    The UNIQUE constraint must be dropped before this runs: the new hashes are
    computed from a different payload than the stored ones.
    """
    connection = op.get_bind()
    rows = connection.execute(
        text("SELECT id, class_name, parameters FROM rag_prompt")
    ).fetchall()
    for row in rows:
        parameters = _load_parameters(row.parameters)
        if parameters is None:
            parameters = {}
        if class_aware:
            digest = _prompt_hash(row.class_name, parameters)
        else:
            digest = _parameters_hash(parameters)
        connection.execute(
            text("UPDATE rag_prompt SET parameters_hash = :digest WHERE id = :id"),
            {"digest": digest, "id": row.id},
        )


_PROMPT_COMPONENT_KEY = "component"
_PROMPT_PARAMS_KEY = "params"
_PROMPT_PROMPT_KEY = "prompt"
_PROMPT_ID_KEY = "prompt_id"
_PROMPT_LANGUAGE_KEY = "language"
_GENERATION_SLOT_PATH = "generation"

_INSERT_PROMPT_SQL = (
    "INSERT INTO rag_prompt "
    "(class_name, name, parameters, parameters_hash, is_library, is_default, "
    "based_on_id, created, last_modified) "
    "VALUES (:class_name, NULL, :parameters, :parameters_hash, :is_library, "
    ":is_default, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
)


def _normalize(parameters: Any) -> Any:
    """Return a deterministically key-sorted copy of ``parameters``."""
    return json.loads(json.dumps(parameters, sort_keys=True))


def _is_component_ref(value: Any) -> bool:
    """Whether ``value`` is a ``{"component", "params"}`` reference."""
    return isinstance(value, dict) and (
        _PROMPT_COMPONENT_KEY in value and _PROMPT_PARAMS_KEY in value
    )


def _is_prompt_reference(value: Any) -> bool:
    """Whether ``value`` describes a prompt slot binding."""
    return isinstance(value, dict) and (
        _PROMPT_COMPONENT_KEY in value or _PROMPT_ID_KEY in value
    )


def _walk_prompt_refs(node: dict, prefix: str, refs: dict[str, Any]) -> None:
    """Collect nested ``prompt`` keys, following the slot-path grammar.

    Paths mirror ``PromptService.discover_prompt_slots``: component ``params``
    wrappers are skipped, while list children are addressed as
    ``children[0]``. Extracted references are removed from ``node``.
    """
    for key in list(node.keys()):
        value = node[key]
        if key == _PROMPT_PARAMS_KEY and isinstance(value, dict):
            _walk_prompt_refs(value, prefix, refs)
        elif key == _PROMPT_PROMPT_KEY and _is_component_ref(value):
            slot_path = f"{prefix}.prompt" if prefix else _GENERATION_SLOT_PATH
            refs[slot_path] = node.pop(key)
        elif isinstance(value, dict):
            child_path = f"{prefix}.{key}" if prefix else key
            _walk_prompt_refs(value, child_path, refs)
        elif isinstance(value, list):
            child_path = f"{prefix}.{key}" if prefix else key
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    _walk_prompt_refs(item, f"{child_path}[{index}]", refs)


def _extract_prompt_references(
    parameters: Any,
) -> tuple[Any, dict[str, Any], Any]:
    """Split prompts out of a stored parameters payload.

    Returns the prompt-free parameters, the extracted references keyed by slot
    path, and the top-level ``prompt_id`` (also removed from the result).
    """
    cleaned = copy.deepcopy(parameters) if isinstance(parameters, dict) else {}
    refs: dict[str, Any] = {}

    prompt_id = cleaned.pop(_PROMPT_ID_KEY, None)
    generation = cleaned.get(_PROMPT_PROMPT_KEY)
    if isinstance(generation, dict):
        cleaned.pop(_PROMPT_PROMPT_KEY)
        if _is_prompt_reference(generation):
            refs[_GENERATION_SLOT_PATH] = generation

    _walk_prompt_refs(cleaned, "", refs)
    return cleaned, refs, prompt_id


def _restore_prompt_reference(
    node: dict, prefix: str, slot_path: str, reference: Any
) -> bool:
    """Put ``reference`` back at ``slot_path`` in ``node``.

    Mirrors :func:`_walk_prompt_refs` so a reference the migration cannot
    resolve can be left embedded in the parameters instead of being dropped.
    """
    for key in list(node.keys()):
        value = node[key]
        if key == _PROMPT_PARAMS_KEY and isinstance(value, dict):
            if _restore_prompt_reference(value, prefix, slot_path, reference):
                return True
        elif key == _PROMPT_PROMPT_KEY and _is_component_ref(value):
            current = f"{prefix}.prompt" if prefix else _GENERATION_SLOT_PATH
            if current == slot_path:
                node[key] = reference
                return True
        elif isinstance(value, dict):
            child_path = f"{prefix}.{key}" if prefix else key
            if _restore_prompt_reference(value, child_path, slot_path, reference):
                return True
        elif isinstance(value, list):
            child_path = f"{prefix}.{key}" if prefix else key
            for index, item in enumerate(value):
                if isinstance(item, dict) and _restore_prompt_reference(
                    item, f"{child_path}[{index}]", slot_path, reference
                ):
                    return True
    return False


def _keep_embedded_reference(
    cleaned: dict[str, Any], slot_path: str, reference: Any
) -> None:
    """Re-insert an unresolved reference into the prompt-free parameters."""
    if slot_path == _GENERATION_SLOT_PATH:
        cleaned[_PROMPT_PROMPT_KEY] = reference
        return
    _restore_prompt_reference(cleaned, "", slot_path, reference)


def _ensure_prompt_row(
    connection: sa.Connection,
    class_name: str,
    parameters: dict[str, Any],
    *,
    is_default: bool,
) -> int:
    """Return the id of the prompt row holding ``class_name``/``parameters``.

    Defaults are deduplicated by class *and* content: a ``Default*`` class can
    legitimately be bound to several different templates maps (legacy sessions
    each stayed on the text they were saved with), and collapsing them onto the
    first row would silently rewrite every other session's prompt. When no
    default row matches, the exact parameters are kept in a content-addressed
    draft. Everything non-canonical is content-addressed by the class-aware
    hash and stored as an internal draft.
    """
    normalized = _normalize(parameters or {})
    digest = _prompt_hash(class_name, normalized)

    if is_default:
        rows = connection.execute(
            text(
                "SELECT id, parameters FROM rag_prompt "
                "WHERE class_name = :class_name AND is_default = 1 "
                "ORDER BY id"
            ),
            {"class_name": class_name},
        ).fetchall()
        for row in rows:
            if _normalize(_load_parameters(row.parameters) or {}) == normalized:
                return row.id
        if not rows:
            result = connection.execute(
                text(_INSERT_PROMPT_SQL),
                {
                    "class_name": class_name,
                    "parameters": json.dumps(normalized, sort_keys=True),
                    "parameters_hash": digest,
                    "is_library": 0,
                    "is_default": 1,
                },
            )
            return int(result.lastrowid)
        # A canonical row already owns this class but a different content.
        # Keep the exact parameters as a content-addressed draft instead of
        # reusing (and thereby rewriting) another session's default.
        return _ensure_prompt_row(connection, class_name, parameters, is_default=False)

    row = connection.execute(
        text(
            "SELECT id, is_default FROM rag_prompt "
            "WHERE parameters_hash = :digest LIMIT 1"
        ),
        {"digest": digest},
    ).fetchone()
    if row is not None:
        if bool(row.is_default):
            # A legacy ``Default*`` row whose body only carries a template
            # already owns this content hash. Keep its text by demoting it to
            # a draft instead of leaving a default without the language
            # templates map, which the read path cannot resolve.
            connection.execute(
                text(
                    "UPDATE rag_prompt SET is_default = 0, is_library = 0 "
                    "WHERE id = :id"
                ),
                {"id": row.id},
            )
        return row.id
    result = connection.execute(
        text(_INSERT_PROMPT_SQL),
        {
            "class_name": class_name,
            "parameters": json.dumps(normalized, sort_keys=True),
            "parameters_hash": digest,
            "is_library": 0,
            "is_default": 0,
        },
    )
    return int(result.lastrowid)


def _has_language_templates(params: Any) -> bool:
    """Whether a prompt body carries the canonical multi-language map."""
    return (
        isinstance(params, dict)
        and isinstance(params.get("templates"), dict)
        and bool(params["templates"])
    )


def _has_usable_template(params: Any) -> bool:
    """Whether a prompt body carries any text that can actually render."""
    if not isinstance(params, dict):
        return False
    template = params.get("template")
    if isinstance(template, str) and template.strip():
        return True
    return _has_language_templates(params)


def _find_default_row(connection: sa.Connection, class_name: str) -> Any:
    """Return the canonical default row for ``class_name``, if one exists.

    Rows that actually carry the language templates map are preferred; a
    legacy default that only stores a language selector is still usable because
    the runtime falls back to the registered component metadata.
    """
    rows = connection.execute(
        text(
            "SELECT id, parameters FROM rag_prompt "
            "WHERE class_name = :class_name AND is_default = 1 "
            "ORDER BY id"
        ),
        {"class_name": class_name},
    ).fetchall()
    for row in rows:
        if _has_language_templates(_load_parameters(row.parameters) or {}):
            return row
    return rows[0] if rows else None


def _resolve_prompt_reference(
    connection: sa.Connection, reference: dict[str, Any]
) -> tuple[int, Any] | None:
    """Resolve one extracted reference to ``(prompt_id, binding_language)``.

    A legacy ``Default*`` prompt may only store its active text as ``template``.
    Such a row cannot be used as a built-in default: the catalog expects the
    language ``templates`` map, and the read path would fail to resolve it.
    Those references are kept as a draft row with the exact stored parameters,
    so the session keeps the text it was saved with. A ``Default*`` reference
    that does carry a templates map reuses the canonical default row, which is
    what keeps sessions pointing at the live built-in.

    A ``Default*`` reference with *no usable text at all* (``{\"language\":
    \"en\"}`` or ``{\"language\": \"en\", \"template\": \"\"}``) is not turned
    into a draft: there is no text to keep. It binds the existing canonical
    default row with the selected language when one is present; otherwise it
    returns ``None`` so the reference stays embedded in the session parameters,
    where the runtime resolves it from the registered component metadata.
    """
    if _PROMPT_COMPONENT_KEY in reference:
        class_name = reference.get(_PROMPT_COMPONENT_KEY)
        if not isinstance(class_name, str) or not class_name:
            return None
        params = reference.get(_PROMPT_PARAMS_KEY) or {}
        if not isinstance(params, dict):
            params = {}
        is_default_class = class_name.startswith("Default")
        if is_default_class and _has_language_templates(params):
            prompt_id = _ensure_prompt_row(
                connection, class_name, params, is_default=True
            )
            return prompt_id, params.get(_PROMPT_LANGUAGE_KEY)
        if is_default_class and not _has_usable_template(params):
            canonical = _find_default_row(connection, class_name)
            if canonical is None:
                # No built-in row to bind yet. Leave the reference embedded;
                # a draft with no text would be unreadable.
                return None
            return canonical.id, params.get(_PROMPT_LANGUAGE_KEY)
        # Custom prompts and legacy text-only defaults share the content-
        # addressed draft path.
        prompt_id = _ensure_prompt_row(connection, class_name, params, is_default=False)
        return prompt_id, None

    prompt_id = reference.get(_PROMPT_ID_KEY)
    if prompt_id is None:
        return None
    row = connection.execute(
        text(
            "SELECT id, class_name, parameters, is_default FROM rag_prompt "
            "WHERE id = :id"
        ),
        {"id": prompt_id},
    ).fetchone()
    if row is None:
        return None
    params = _load_parameters(row.parameters) or {}
    if bool(row.is_default):
        if _has_language_templates(params):
            return row.id, params.get(_PROMPT_LANGUAGE_KEY)
        if not _has_usable_template(params):
            canonical = _find_default_row(connection, row.class_name)
            if canonical is None:
                return None
            return canonical.id, params.get(_PROMPT_LANGUAGE_KEY)
        # A default row written before the templates map existed. Keep its
        # text by pointing the binding at a draft with the same content.
        draft_id = _ensure_prompt_row(
            connection, row.class_name, params, is_default=False
        )
        return draft_id, None
    return row.id, None


def _upsert_binding(
    connection: sa.Connection,
    session_id: int,
    slot_path: str,
    prompt_id: int,
    language: Any,
) -> None:
    """Insert or replace the binding of one session slot."""
    connection.execute(
        text(
            "INSERT OR REPLACE INTO rag_session_prompt "
            "(session_id, slot_path, prompt_id, language) "
            "VALUES (:session_id, :slot_path, :prompt_id, :language)"
        ),
        {
            "session_id": session_id,
            "slot_path": slot_path,
            "prompt_id": prompt_id,
            "language": language,
        },
    )


def _binding_snapshot(
    connection: sa.Connection, prompt_id: int, language: Any
) -> dict[str, Any]:
    """Build the history binding snapshot for a resolved prompt row."""
    row = connection.execute(
        text(
            "SELECT class_name, name, parameters, is_library, is_default "
            "FROM rag_prompt WHERE id = :id"
        ),
        {"id": prompt_id},
    ).fetchone()
    return {
        "prompt_id": prompt_id,
        "class_name": row.class_name,
        "name": row.name,
        "parameters": _load_parameters(row.parameters) or {},
        "is_default": bool(row.is_default),
        "is_library": bool(row.is_library),
        "language": language,
    }


def _backfill_session_prompts(connection: sa.Connection) -> None:
    """Move prompts stored inside RAG sessions into bindings.

    Every legacy session keeps prompt-free parameters, gains
    ``rag_session_prompt`` rows for each extracted slot, and its pipeline
    snapshot starts pointing at the generation binding.
    """
    rows = connection.execute(
        text(
            "SELECT id, parameters FROM generative_session WHERE task_name = 'RAGTask'"
        )
    ).fetchall()
    for row in rows:
        stored = _load_parameters(row.parameters)
        if not isinstance(stored, dict):
            continue

        cleaned, refs, prompt_id = _extract_prompt_references(stored)
        if not refs and prompt_id is None:
            continue

        bindings: dict[str, tuple[int, Any]] = {}
        for slot_path, reference in refs.items():
            resolved = _resolve_prompt_reference(connection, reference)
            if resolved is None:
                # Nothing to bind: leave the legacy reference inside the
                # parameters so the runtime can resolve it.
                _keep_embedded_reference(cleaned, slot_path, reference)
                continue
            bound_id, language = resolved
            bindings[slot_path] = (bound_id, language)
            _upsert_binding(connection, row.id, slot_path, bound_id, language)

        if _GENERATION_SLOT_PATH not in bindings and prompt_id is not None:
            resolved = _resolve_prompt_reference(
                connection, {_PROMPT_ID_KEY: prompt_id}
            )
            if resolved is not None:
                bound_id, language = resolved
                bindings[_GENERATION_SLOT_PATH] = (bound_id, language)
                _upsert_binding(
                    connection, row.id, _GENERATION_SLOT_PATH, bound_id, language
                )
            else:
                cleaned[_PROMPT_ID_KEY] = prompt_id

        connection.execute(
            text(
                "UPDATE generative_session SET parameters = :parameters WHERE id = :id"
            ),
            {"parameters": json.dumps(cleaned, sort_keys=True), "id": row.id},
        )

        generation = bindings.get(_GENERATION_SLOT_PATH)
        if generation is not None:
            connection.execute(
                text(
                    "UPDATE rag_pipeline SET prompt_id = :prompt_id "
                    "WHERE session_id = :session_id"
                ),
                {"prompt_id": generation[0], "session_id": row.id},
            )


def _backfill_history_prompts(connection: sa.Connection) -> None:
    """Move prompts out of history entries into per-entry snapshots.

    Rows without prompt references are left untouched; their parameters are
    already complete.
    """
    rows = connection.execute(
        text("SELECT id, parameters FROM parameter_history")
    ).fetchall()
    for row in rows:
        stored = _load_parameters(row.parameters)
        if not isinstance(stored, dict):
            continue

        cleaned, refs, prompt_id = _extract_prompt_references(stored)
        if not refs and prompt_id is None:
            continue

        snapshots: dict[str, dict[str, Any]] = {}
        for slot_path, reference in refs.items():
            resolved = _resolve_prompt_reference(connection, reference)
            if resolved is None:
                _keep_embedded_reference(cleaned, slot_path, reference)
                continue
            bound_id, language = resolved
            snapshots[slot_path] = _binding_snapshot(connection, bound_id, language)

        if _GENERATION_SLOT_PATH not in snapshots and prompt_id is not None:
            resolved = _resolve_prompt_reference(
                connection, {_PROMPT_ID_KEY: prompt_id}
            )
            if resolved is not None:
                bound_id, language = resolved
                snapshots[_GENERATION_SLOT_PATH] = _binding_snapshot(
                    connection, bound_id, language
                )
            else:
                cleaned[_PROMPT_ID_KEY] = prompt_id

        connection.execute(
            text(
                "UPDATE parameter_history SET parameters = :parameters, "
                "prompt_bindings = :prompt_bindings WHERE id = :id"
            ),
            {
                "parameters": json.dumps(cleaned, sort_keys=True),
                "prompt_bindings": json.dumps(snapshots, sort_keys=True),
                "id": row.id,
            },
        )


def _backfill_prompt_bindings() -> None:
    """Backfill sessions and history entries from their stored prompts."""
    connection = op.get_bind()
    _backfill_session_prompts(connection)
    _backfill_history_prompts(connection)


def _merge_colliding_prompt_rows(connection: sa.Connection) -> None:
    """Merge prompt rows that collide under the pre-redesign hash.

    Downgrading recomputes ``parameters_hash`` from the parameters only, so
    rows that differ only by class now collide. Keep the lowest id, repoint
    every reference to it, and delete the duplicates before the old UNIQUE
    constraint is re-added.
    """
    rows = connection.execute(
        text("SELECT id, parameters_hash FROM rag_prompt ORDER BY id")
    ).fetchall()
    kept: dict[str, int] = {}
    duplicates: list[tuple[int, int]] = []
    for row in rows:
        keeper = kept.get(row.parameters_hash)
        if keeper is None:
            kept[row.parameters_hash] = row.id
        else:
            duplicates.append((row.id, keeper))
    if not duplicates:
        return

    tables = {
        row[0]
        for row in connection.execute(
            text("SELECT name FROM sqlite_master WHERE type = 'table'")
        ).fetchall()
    }
    for duplicate_id, keeper_id in duplicates:
        if "rag_session_prompt" in tables:
            connection.execute(
                text(
                    "UPDATE rag_session_prompt SET prompt_id = :keeper "
                    "WHERE prompt_id = :duplicate"
                ),
                {"keeper": keeper_id, "duplicate": duplicate_id},
            )
        connection.execute(
            text(
                "UPDATE rag_pipeline SET prompt_id = :keeper "
                "WHERE prompt_id = :duplicate"
            ),
            {"keeper": keeper_id, "duplicate": duplicate_id},
        )
        connection.execute(
            text(
                "UPDATE rag_prompt SET based_on_id = :keeper "
                "WHERE based_on_id = :duplicate AND id != :keeper"
            ),
            {"keeper": keeper_id, "duplicate": duplicate_id},
        )
        connection.execute(
            text("DELETE FROM rag_prompt WHERE id = :duplicate"),
            {"duplicate": duplicate_id},
        )


def upgrade() -> None:
    with op.batch_alter_table(
        "rag_prompt",
        schema=None,
        table_kwargs={"sqlite_autoincrement": True},
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_default",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(sa.Column("based_on_id", sa.Integer(), nullable=True))

    op.execute("UPDATE rag_prompt SET is_default = 1 WHERE class_name LIKE 'Default%'")

    # Recompute every hash from the new class-aware payload. At most one row
    # exists per old parameters hash, so no collisions can appear here.
    with op.batch_alter_table(
        "rag_prompt",
        schema=None,
        table_kwargs={"sqlite_autoincrement": True},
    ) as batch_op:
        batch_op.drop_constraint(_UNIQUE_NAME, type_="unique")

    _recompute_hashes(class_aware=True)

    with op.batch_alter_table(
        "rag_prompt",
        schema=None,
        table_kwargs={"sqlite_autoincrement": True},
    ) as batch_op:
        batch_op.create_unique_constraint(_UNIQUE_NAME, ["parameters_hash"])

    op.create_table(
        "rag_session_prompt",
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("slot_path", sa.String(), nullable=False),
        sa.Column("prompt_id", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["generative_session.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["prompt_id"],
            ["rag_prompt.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("session_id", "slot_path"),
    )

    with op.batch_alter_table("rag_pipeline", schema=None) as batch_op:
        batch_op.drop_constraint(_PROMPT_FK_NAME, type_="foreignkey")
        batch_op.create_foreign_key(
            _PROMPT_FK_NAME,
            "rag_prompt",
            ["prompt_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("parameter_history", schema=None) as batch_op:
        batch_op.add_column(sa.Column("prompt_bindings", sa.JSON(), nullable=True))

    # Move prompts stored inside sessions/history into the new binding table.
    _backfill_prompt_bindings()


def downgrade() -> None:
    with op.batch_alter_table("parameter_history", schema=None) as batch_op:
        batch_op.drop_column("prompt_bindings")

    with op.batch_alter_table("rag_pipeline", schema=None) as batch_op:
        batch_op.drop_constraint(_PROMPT_FK_NAME, type_="foreignkey")
        batch_op.create_foreign_key(
            _PROMPT_FK_NAME,
            "rag_prompt",
            ["prompt_id"],
            ["id"],
            ondelete="CASCADE",
        )

    op.drop_table("rag_session_prompt")

    # Restore the previous parameter-only hashes. This requires the class-aware
    # UNIQUE to be gone; two rows that shared parameters but not a class would
    # otherwise collide when the old constraint is re-added.
    with op.batch_alter_table(
        "rag_prompt",
        schema=None,
        table_kwargs={"sqlite_autoincrement": True},
    ) as batch_op:
        batch_op.drop_constraint(_UNIQUE_NAME, type_="unique")

    _recompute_hashes(class_aware=False)

    # The old constraint is parameters-only, so two rows from different prompt
    # classes can now share a hash. Merge them before re-adding the UNIQUE.
    _merge_colliding_prompt_rows(op.get_bind())

    with op.batch_alter_table(
        "rag_prompt",
        schema=None,
        table_kwargs={"sqlite_autoincrement": True},
    ) as batch_op:
        batch_op.create_unique_constraint(_UNIQUE_NAME, ["parameters_hash"])

    with op.batch_alter_table(
        "rag_prompt",
        schema=None,
        # Restore the pre-redesign table: no AUTOINCREMENT keyword.
        table_kwargs={"sqlite_autoincrement": False},
        recreate="always",
    ) as batch_op:
        batch_op.drop_column("based_on_id")
        batch_op.drop_column("is_default")

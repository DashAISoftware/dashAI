"""generative sessions get a workflow

Every generative session now names the workflow that runs it. Existing
sessions become ``InferenceWorkflow`` sessions through the column's server
default. RAG sessions, stored until now as task ``RAGTask`` with the
placeholder model ``RAGPipeline``, become text to text sessions run by
``RAGWorkflow`` whose model is their generation LLM; their parameter history
gets the generator each entry used.

A failing migration makes the startup recreate an empty database, so the data
step never raises on a malformed row: what it cannot read keeps its old value.

Revision ID: a7f3c9e2d5b8
Revises: 362bcf7193f5
Create Date: 2026-11-10
"""

import json
from typing import Optional, Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7f3c9e2d5b8"
down_revision: Union[str, None] = "362bcf7193f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INFERENCE_WORKFLOW = "InferenceWorkflow"
_RAG_WORKFLOW = "RAGWorkflow"
_RAG_TASK = "RAGTask"
_RAG_PLACEHOLDER_MODEL = "RAGPipeline"
_TEXT_TO_TEXT_TASK = "TextToTextGenerationTask"


def _load_parameters(raw) -> dict:
    """Return stored parameters as a dict, whatever the driver gave us.

    Parameters
    ----------
    raw : Any
        The stored ``parameters`` value.

    Returns
    -------
    dict
        The parameters, or an empty dict when they cannot be read.
    """
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _generator(raw) -> Optional[str]:
    """Return the generation model named by stored parameters.

    Parameters
    ----------
    raw : Any
        The stored ``parameters`` value.

    Returns
    -------
    Optional[str]
        The component of ``generation_model``, or ``None`` when absent or
        malformed.
    """
    reference = _load_parameters(raw).get("generation_model")
    if not isinstance(reference, dict):
        return None
    component = reference.get("component")
    return component if isinstance(component, str) and component else None


def upgrade() -> None:
    op.add_column(
        "generative_session",
        sa.Column(
            "workflow_name",
            sa.String(),
            nullable=False,
            server_default=_INFERENCE_WORKFLOW,
        ),
    )

    conn = op.get_bind()
    sessions = conn.execute(
        sa.text("SELECT id, parameters FROM generative_session WHERE task_name = :t"),
        {"t": _RAG_TASK},
    ).fetchall()
    for session_id, raw in sessions:
        model_name = _generator(raw) or _RAG_PLACEHOLDER_MODEL
        conn.execute(
            sa.text(
                "UPDATE generative_session SET task_name = :task, "
                "model_name = :model, workflow_name = :workflow WHERE id = :id"
            ),
            {
                "task": _TEXT_TO_TEXT_TASK,
                "model": model_name,
                "workflow": _RAG_WORKFLOW,
                "id": session_id,
            },
        )
        entries = conn.execute(
            sa.text(
                "SELECT id, parameters FROM parameter_history "
                "WHERE session_id = :id AND model_name = :placeholder"
            ),
            {"id": session_id, "placeholder": _RAG_PLACEHOLDER_MODEL},
        ).fetchall()
        for entry_id, entry_raw in entries:
            conn.execute(
                sa.text("UPDATE parameter_history SET model_name = :m WHERE id = :id"),
                {"m": _generator(entry_raw) or model_name, "id": entry_id},
            )


def downgrade() -> None:
    conn = op.get_bind()
    session_ids = [
        row[0]
        for row in conn.execute(
            sa.text("SELECT id FROM generative_session WHERE workflow_name = :w"),
            {"w": _RAG_WORKFLOW},
        ).fetchall()
    ]
    for session_id in session_ids:
        conn.execute(
            sa.text(
                "UPDATE parameter_history SET model_name = :placeholder "
                "WHERE session_id = :id AND model_name IS NOT NULL"
            ),
            {"placeholder": _RAG_PLACEHOLDER_MODEL, "id": session_id},
        )
        conn.execute(
            sa.text(
                "UPDATE generative_session SET task_name = :task, "
                "model_name = :placeholder WHERE id = :id"
            ),
            {
                "task": _RAG_TASK,
                "placeholder": _RAG_PLACEHOLDER_MODEL,
                "id": session_id,
            },
        )

    with op.batch_alter_table("generative_session") as batch_op:
        batch_op.drop_column("workflow_name")

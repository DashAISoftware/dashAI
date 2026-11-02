"""add column_roles to model_session

Revision ID: 5d2e8a1c9b47
Revises: 3ef0449e8309
Create Date: 2026-10-22 12:00:00.000000

A session will record its columns by role, as the task declares them, instead
of in ``input_columns``, ``output_columns`` and ``input_column_refs``. This
revision adds the new column and fills it for every existing row; a later
revision drops the three old ones.

Every session that exists today belongs to a task that maps inputs to
outputs, so the rows convert to the two roles of that family, named here as
they are at this point of the history:

  * ``features``: refs from ``input_column_refs``, or raw refs of
    ``input_columns`` for rows older than that column; resolved columns from
    ``input_columns``, which ``PreprocessingJob`` already overwrote with the
    resolved names.
  * ``target``: raw refs and columns from ``output_columns``, only when it is
    not empty (a clustering session has no target).
"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "5d2e8a1c9b47"
down_revision: Union[str, None] = "3ef0449e8309"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _load(value):
    """A JSON column as SQLite hands it over: text, or already decoded."""
    if value is None:
        return None
    if isinstance(value, (bytes, str)):
        return json.loads(value)
    return value


def _raw_refs(names):
    return [{"kind": "raw", "name": name} for name in names]


def column_roles(input_columns, output_columns, input_column_refs) -> dict:
    """The roles of one existing row."""
    input_columns = list(input_columns or [])
    output_columns = list(output_columns or [])
    refs = (
        list(input_column_refs)
        if input_column_refs is not None
        else _raw_refs(input_columns)
    )
    roles = {}
    if refs:
        roles["features"] = {"refs": refs, "columns": input_columns}
    if output_columns:
        roles["target"] = {
            "refs": _raw_refs(output_columns),
            "columns": output_columns,
        }
    return roles


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "model_session" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("model_session")}
    if "column_roles" not in existing:
        op.add_column(
            "model_session", sa.Column("column_roles", sa.JSON(), nullable=True)
        )

    rows = bind.execute(
        sa.text(
            "SELECT id, input_columns, output_columns, input_column_refs "
            "FROM model_session WHERE column_roles IS NULL"
        )
    ).fetchall()
    for row_id, input_columns, output_columns, input_column_refs in rows:
        roles = column_roles(
            _load(input_columns), _load(output_columns), _load(input_column_refs)
        )
        bind.execute(
            sa.text("UPDATE model_session SET column_roles = :roles WHERE id = :id"),
            {"roles": json.dumps(roles), "id": row_id},
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "model_session" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("model_session")}
    if "column_roles" in existing:
        with op.batch_alter_table("model_session") as batch:
            batch.drop_column("column_roles")

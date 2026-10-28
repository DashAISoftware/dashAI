"""drop the old column fields of model_session

Revision ID: 9b4e7c2a1f30
Revises: 5d2e8a1c9b47
Create Date: 2026-10-22 18:00:00.000000

``column_roles`` (filled by 5d2e8a1c9b47) is now the only record of a
session's columns, so it becomes required and ``input_columns``,
``output_columns`` and ``input_column_refs`` go.

The downgrade rebuilds the three fields from the roles. Every session that
can exist at this point belongs to a task that maps inputs to outputs, whose
roles are named here as they are at this point of the history: ``features``
and ``target``.
"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9b4e7c2a1f30"
down_revision: Union[str, None] = "5d2e8a1c9b47"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_COLUMNS = ("input_columns", "output_columns", "input_column_refs")


def _load(value):
    if value is None:
        return None
    if isinstance(value, (bytes, str)):
        return json.loads(value)
    return value


def _raw_refs(names):
    return [{"kind": "raw", "name": name} for name in names]


def _roles_from_old(input_columns, output_columns, input_column_refs) -> dict:
    """The same conversion as 5d2e8a1c9b47, for a row it left without roles."""
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
        roles["target"] = {"refs": _raw_refs(output_columns), "columns": output_columns}
    return roles


def _columns(bind) -> set:
    return {column["name"] for column in sa.inspect(bind).get_columns("model_session")}


def upgrade() -> None:
    bind = op.get_bind()
    if "model_session" not in sa.inspect(bind).get_table_names():
        return
    existing = _columns(bind)

    if set(_OLD_COLUMNS) <= existing:
        rows = bind.execute(
            sa.text(
                "SELECT id, input_columns, output_columns, input_column_refs "
                "FROM model_session WHERE column_roles IS NULL"
            )
        ).fetchall()
        for row_id, inputs, outputs, refs in rows:
            roles = _roles_from_old(_load(inputs), _load(outputs), _load(refs))
            bind.execute(
                sa.text(
                    "UPDATE model_session SET column_roles = :roles WHERE id = :id"
                ),
                {"roles": json.dumps(roles), "id": row_id},
            )

    with op.batch_alter_table("model_session") as batch:
        batch.alter_column("column_roles", existing_type=sa.JSON(), nullable=False)
        for name in _OLD_COLUMNS:
            if name in existing:
                batch.drop_column(name)


def downgrade() -> None:
    bind = op.get_bind()
    if "model_session" not in sa.inspect(bind).get_table_names():
        return
    existing = _columns(bind)

    with op.batch_alter_table("model_session") as batch:
        for name in _OLD_COLUMNS:
            if name not in existing:
                batch.add_column(sa.Column(name, sa.JSON(), nullable=True))
        batch.alter_column("column_roles", existing_type=sa.JSON(), nullable=True)

    rows = bind.execute(
        sa.text("SELECT id, column_roles FROM model_session")
    ).fetchall()
    for row_id, column_roles in rows:
        roles = _load(column_roles) or {}
        features = roles.get("features", {})
        target = roles.get("target", {})
        bind.execute(
            sa.text(
                "UPDATE model_session SET input_columns = :inputs, "
                "output_columns = :outputs, input_column_refs = :refs WHERE id = :id"
            ),
            {
                "inputs": json.dumps(features.get("columns", [])),
                "outputs": json.dumps(target.get("columns", [])),
                "refs": json.dumps(features.get("refs", [])),
                "id": row_id,
            },
        )

    with op.batch_alter_table("model_session") as batch:
        batch.alter_column("input_columns", existing_type=sa.JSON(), nullable=False)
        batch.alter_column("output_columns", existing_type=sa.JSON(), nullable=False)

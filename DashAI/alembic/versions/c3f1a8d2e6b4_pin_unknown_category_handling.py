"""pin how the stored encoders of model sessions treat unknown categories

Revision ID: c3f1a8d2e6b4
Revises: 9b4e7c2a1f30
Create Date: 2026-10-25 12:00:00.000000

The one-hot and ordinal encoders now treat a category unseen in fit by
default ("ignore" and -1). A step stored without ``handle_unknown`` was built
with sklearn's own default, "error". The fitted converters live in pickles
and keep it anyway, but a session is refitted from its stored steps when it
is imported without artifacts, so the old default is written into them.

The downgrade leaves the rows as they are: "error" spelled out is what the
code before this revision did with the field left out.
"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3f1a8d2e6b4"
down_revision: Union[str, None] = "9b4e7c2a1f30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ENCODERS = ("OneHotEncoder", "OrdinalEncoder")


def _load(value):
    if value is None:
        return None
    if isinstance(value, (bytes, str)):
        return json.loads(value)
    return value


def _pinned(preprocessing):
    """The steps with "error" written into encoders that left it out, or None."""
    changed = False
    # An imported package is stored as it came, so "steps" and "params" may be
    # null; they mean no steps and no params.
    for step in (preprocessing or {}).get("steps") or []:
        if step.get("converter") not in _ENCODERS:
            continue
        params = step.get("params") or {}
        if "handle_unknown" not in params:
            params["handle_unknown"] = "error"
            step["params"] = params
            changed = True
    return preprocessing if changed else None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, preprocessing FROM model_session")
    ).fetchall()
    for row_id, preprocessing in rows:
        pinned = _pinned(_load(preprocessing))
        if pinned is None:
            continue
        bind.execute(
            sa.text("UPDATE model_session SET preprocessing = :value WHERE id = :id"),
            {"value": json.dumps(pinned), "id": row_id},
        )


def downgrade() -> None:
    pass

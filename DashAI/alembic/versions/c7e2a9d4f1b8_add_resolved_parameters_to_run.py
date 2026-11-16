"""add what a run's empty parameters resolved to

Revision ID: c7e2a9d4f1b8
Revises: b5d7e9f1a3c6
Create Date: 2026-11-16 12:00:00.000000

A forecasting run keeps the parameters the user left empty as empty, so a
retrain resolves them again, and records apart what they resolved to when it
trained, and where from: ``{name: {"value", "reason": {"key", "values"}}}``.
The season left empty is the one the series' frequency implies; the reduction
model's lags left empty are one season. A run that has not trained, a run of
another task, and every run made before, stays NULL.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c7e2a9d4f1b8"
down_revision: Union[str, None] = "b5d7e9f1a3c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("run", schema=None) as batch_op:
        batch_op.add_column(sa.Column("resolved_parameters", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("run", schema=None) as batch_op:
        batch_op.drop_column("resolved_parameters")

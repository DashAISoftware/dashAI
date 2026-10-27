"""record why a metric is unavailable

Revision ID: b8e3d1f4a6c2
Revises: e7a2c5f9b1d3
Create Date: 2026-10-26 18:00:00.000000

A metric that has no value on a run's data (MAPE on a series with a zero)
is recorded with a NULL value and the reason, instead of being dropped in
silence. Rows written before all have a value.

The downgrade drops the rows without a value: the old schema cannot hold one,
and a NOT NULL constraint would refuse the table copy otherwise.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8e3d1f4a6c2"
down_revision: Union[str, None] = "e7a2c5f9b1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("metric", schema=None) as batch_op:
        batch_op.alter_column("value", existing_type=sa.Float(), nullable=True)
        batch_op.add_column(sa.Column("unavailable_reason", sa.String(), nullable=True))


def downgrade() -> None:
    op.execute("DELETE FROM metric WHERE value IS NULL")
    with op.batch_alter_table("metric", schema=None) as batch_op:
        batch_op.drop_column("unavailable_reason")
        batch_op.alter_column("value", existing_type=sa.Float(), nullable=False)

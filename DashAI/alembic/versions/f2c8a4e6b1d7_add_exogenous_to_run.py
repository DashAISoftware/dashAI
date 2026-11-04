"""add what a run did with its session's exogenous variables

Revision ID: f2c8a4e6b1d7
Revises: b5ced45240cd
Create Date: 2026-11-03 12:00:00.000000

A forecasting run records whether it read the exogenous variables of its
session, which raw columns a prediction then has to bring, and why it did not
read them when it did not: ``{"used", "columns": [{"name", "type"}],
"reason"}``. A run of a session without exogenous variables, and every run
made before, stays NULL.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2c8a4e6b1d7"
down_revision: Union[str, None] = "b5ced45240cd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("run", schema=None) as batch_op:
        batch_op.add_column(sa.Column("exogenous", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("run", schema=None) as batch_op:
        batch_op.drop_column("exogenous")

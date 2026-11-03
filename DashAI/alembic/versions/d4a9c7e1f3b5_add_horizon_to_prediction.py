"""add the horizon of a forecast to prediction

Revision ID: d4a9c7e1f3b5
Revises: b8e3d1f4a6c2
Create Date: 2026-10-27 12:00:00.000000

A task that predicts by horizon (single-series forecasting) is asked for a
number of steps past the end of its training series, not for rows. The
prediction keeps that number. Predictions of rows, all the ones made before,
stay NULL.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4a9c7e1f3b5"
down_revision: Union[str, None] = "b8e3d1f4a6c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("prediction", schema=None) as batch_op:
        batch_op.add_column(sa.Column("horizon", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("prediction", schema=None) as batch_op:
        batch_op.drop_column("horizon")

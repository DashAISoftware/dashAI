"""add the categories training never saw to prediction

Revision ID: e7a2c5f9b1d3
Revises: c3f1a8d2e6b4
Create Date: 2026-10-25 15:00:00.000000

A prediction keeps the categories of its rows that an encoder met without
having seen them in training, and treated instead of refusing. Predictions
made before stay NULL: nobody recorded them.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7a2c5f9b1d3"
down_revision: Union[str, None] = "c3f1a8d2e6b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("prediction", schema=None) as batch_op:
        batch_op.add_column(sa.Column("unseen_categories", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("prediction", schema=None) as batch_op:
        batch_op.drop_column("unseen_categories")

"""add generation metadata to generative processes

Revision ID: c4d5e6f7a8b9
Revises: d8f3b1c6e2a4
Create Date: 2026-11-18 12:00:00.000000

A chat turn keeps, apart from its text, the usage, the finish reason and the
non-text parts of the model's reply. Turns made before, and turns of models
that report none of these, stay NULL.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "d8f3b1c6e2a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("generative_process", schema=None) as batch_op:
        batch_op.add_column(sa.Column("generation_metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("generative_process", schema=None) as batch_op:
        batch_op.drop_column("generation_metadata")

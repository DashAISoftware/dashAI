"""Add total_rows and total_columns to dataset

Revision ID: a1f8e3b0c2d9
Revises: b4f9e70098e7
Create Date: 2026-05-14 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1f8e3b0c2d9"
down_revision: Union[str, None] = "b4f9e70098e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("dataset", sa.Column("total_rows", sa.Integer(), nullable=True))
    op.add_column("dataset", sa.Column("total_columns", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("dataset", "total_columns")
    op.drop_column("dataset", "total_rows")

"""Add metadata columns to datafile table

Revision ID: c3d7a1f05e8b
Revises: a1c3e5f7b9d2
Create Date: 2026-05-12 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d7a1f05e8b"
down_revision: Union[str, None] = "a1c3e5f7b9d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("datafile", sa.Column("size_bytes", sa.BigInteger(), nullable=True))
    op.add_column("datafile", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("datafile", sa.Column("tags", sa.Text(), nullable=True))
    op.add_column("datafile", sa.Column("source_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("datafile", "source_url")
    op.drop_column("datafile", "tags")
    op.drop_column("datafile", "description")
    op.drop_column("datafile", "size_bytes")

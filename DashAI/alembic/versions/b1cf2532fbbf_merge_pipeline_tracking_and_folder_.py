"""merge pipeline tracking and folder system heads

Revision ID: b1cf2532fbbf
Revises: d9c8f2a1b7e4, f1a2b3c4d5e6
Create Date: 2026-06-25 00:13:45.379060

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1cf2532fbbf'
down_revision: Union[str, None] = ('d9c8f2a1b7e4', 'f1a2b3c4d5e6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

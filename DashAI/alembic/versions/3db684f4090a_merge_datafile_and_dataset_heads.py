"""merge datafile and dataset heads

Revision ID: 3db684f4090a
Revises: a1f8e3b0c2d9, c3d7a1f05e8b
Create Date: 2026-05-27 15:49:47.570864

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3db684f4090a'
down_revision: Union[str, None] = (
    'a1f8e3b0c2d9',
    'c3d7a1f05e8b',
    'd0e5a6c7b8d1',
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

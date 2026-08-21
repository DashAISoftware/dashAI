"""merge session preprocessing and rag heads

Revision ID: b8a884fdd290
Revises: 230e0625e4b5, d033b573e63b
Create Date: 2026-08-21 18:37:16.549338

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8a884fdd290'
down_revision: Union[str, None] = ('230e0625e4b5', 'd033b573e63b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

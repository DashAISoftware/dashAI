"""merge history summary and develop heads

Revision ID: 5813038bfcc6
Revises: 83bd5b526fac, e7a9c3d5f1b2
Create Date: 2026-11-27 12:00:00.000000

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "5813038bfcc6"
down_revision: Union[str, Sequence[str], None] = ("83bd5b526fac", "e7a9c3d5f1b2")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

"""merge generation metadata and loaded model heads

Revision ID: 83bd5b526fac
Revises: c4d5e6f7a8b9, f2b4d6a8c0e1
Create Date: 2026-11-26 12:00:00.000000

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "83bd5b526fac"
down_revision: Union[str, Sequence[str], None] = ("c4d5e6f7a8b9", "f2b4d6a8c0e1")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

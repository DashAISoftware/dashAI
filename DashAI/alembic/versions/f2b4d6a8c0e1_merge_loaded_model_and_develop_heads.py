"""merge loaded model and develop heads

Revision ID: f2b4d6a8c0e1
Revises: b8c9d0e1f2a3, d8f3b1c6e2a4
Create Date: 2026-11-20 12:00:00.000000

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "f2b4d6a8c0e1"
down_revision: Union[str, Sequence[str], None] = ("b8c9d0e1f2a3", "d8f3b1c6e2a4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

"""merge run plot and document converter pipeline heads

Revision ID: e3a9c7d1f5b2
Revises: b8e4f1a6c3d2, c9e2f4a7b1d3
Create Date: 2026-11-12 11:00:00.000000

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "e3a9c7d1f5b2"
down_revision: Union[str, Sequence[str], None] = ("b8e4f1a6c3d2", "c9e2f4a7b1d3")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

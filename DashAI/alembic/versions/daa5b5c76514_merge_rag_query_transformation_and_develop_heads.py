"""merge RAG query transformation and develop heads

Revision ID: daa5b5c76514
Revises: b5ced45240cd, x1y2z3a4b5c6
Create Date: 2026-11-03 12:18:01.604999

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "daa5b5c76514"
down_revision: Union[str, Sequence[str], None] = ("b5ced45240cd", "x1y2z3a4b5c6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

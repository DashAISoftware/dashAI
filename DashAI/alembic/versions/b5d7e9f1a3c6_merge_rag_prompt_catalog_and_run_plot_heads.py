"""merge rag prompt catalog and run plot heads

Revision ID: b5d7e9f1a3c6
Revises: a4b5c6d7e8f9, e3a9c7d1f5b2
Create Date: 2026-11-12 15:00:00.000000

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "b5d7e9f1a3c6"
down_revision: Union[str, Sequence[str], None] = ("a4b5c6d7e8f9", "e3a9c7d1f5b2")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

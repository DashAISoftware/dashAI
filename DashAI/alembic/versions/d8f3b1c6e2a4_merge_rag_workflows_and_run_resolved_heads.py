"""merge rag workflows and run resolved parameters heads

Revision ID: d8f3b1c6e2a4
Revises: a7f3c9e2d5b8, c7e2a9d4f1b8
Create Date: 2026-11-17 13:00:00.000000

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "d8f3b1c6e2a4"
down_revision: Union[str, Sequence[str], None] = ("a7f3c9e2d5b8", "c7e2a9d4f1b8")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

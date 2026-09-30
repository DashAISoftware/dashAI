"""merge develop and dag-pipelines heads

Revision ID: 66a67b766b49
Revises: 50e54749a557, f4a91c62d8e7
Create Date: 2026-09-29 12:00:00.000000

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "66a67b766b49"
down_revision: Union[str, None] = ("50e54749a557", "f4a91c62d8e7")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

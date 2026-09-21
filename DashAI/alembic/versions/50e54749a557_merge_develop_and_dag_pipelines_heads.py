"""merge develop and dag-pipelines heads

Revision ID: 50e54749a557
Revises: a5f2c71e9d40, b1cf2532fbbf
Create Date: 2026-09-21 14:00:00.000000

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "50e54749a557"
down_revision: Union[str, None] = ("a5f2c71e9d40", "b1cf2532fbbf")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

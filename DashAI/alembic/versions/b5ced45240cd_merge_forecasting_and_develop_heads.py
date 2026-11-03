"""merge forecasting and develop heads

Revision ID: b5ced45240cd
Revises: 72db19a8ec8d, d4a9c7e1f3b5
Create Date: 2026-10-29 15:48:38.117567

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "b5ced45240cd"
down_revision: Union[str, Sequence[str], None] = ("72db19a8ec8d", "d4a9c7e1f3b5")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

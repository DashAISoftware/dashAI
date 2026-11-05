"""merge RAG query transformation and forecasting exogenous heads

Revision ID: 362bcf7193f5
Revises: daa5b5c76514, f2c8a4e6b1d7
Create Date: 2026-11-04 10:27:39.013218

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "362bcf7193f5"
down_revision: Union[str, Sequence[str], None] = ("daa5b5c76514", "f2c8a4e6b1d7")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

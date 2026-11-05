"""merge develop and RAG heads

``532d6079557c`` gave the RAG branch a single head after joining the
credential and retrieval branches. ``develop`` then added
``f2c8a4e6b1d7`` (the exogenous variables of a run) on top of the
forecasting head, so a pull request merged with the current ``develop``
has two heads again. This empty merge point joins them without touching
any table.

Revision ID: 2acd4dff165d
Revises: 532d6079557c, f2c8a4e6b1d7
Create Date: 2026-11-04 17:45:03.056485

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "2acd4dff165d"
down_revision: Union[str, Sequence[str], None] = (
    "532d6079557c",
    "f2c8a4e6b1d7",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

"""Add story fields to global_explainer

Revision ID: 6273b0d04af3
Revises: c4e8a1d20f3b
Create Date: 2026-08-03 23:22:57.981298

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "6273b0d04af3"
down_revision: Union[str, None] = "c4e8a1d20f3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "global_explainer",
        sa.Column("story", sa.String(), nullable=True),
    )
    op.add_column(
        "global_explainer",
        sa.Column("story_huey_id", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("global_explainer", "story_huey_id")
    op.drop_column("global_explainer", "story")

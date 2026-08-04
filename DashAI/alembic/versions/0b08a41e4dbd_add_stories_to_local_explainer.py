"""Add stories to local_explainer

Revision ID: 0b08a41e4dbd
Revises: 6273b0d04af3
Create Date: 2026-08-04 10:46:18.347215

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0b08a41e4dbd"
down_revision: Union[str, None] = "6273b0d04af3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("local_explainer", sa.Column("stories", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("local_explainer", "stories")

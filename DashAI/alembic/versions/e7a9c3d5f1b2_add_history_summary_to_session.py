"""add history summary to generative session

Revision ID: e7a9c3d5f1b2
Revises: d8f3b1c6e2a4
Create Date: 2026-11-19 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7a9c3d5f1b2"
down_revision: Union[str, Sequence[str], None] = "d8f3b1c6e2a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("generative_session") as batch_op:
        batch_op.add_column(sa.Column("history_summary", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("history_summary_until", sa.Integer(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("generative_session") as batch_op:
        batch_op.drop_column("history_summary_until")
        batch_op.drop_column("history_summary")

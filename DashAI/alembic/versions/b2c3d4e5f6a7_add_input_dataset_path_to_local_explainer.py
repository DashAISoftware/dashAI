"""Add input_dataset_path to local_explainer

Revision ID: b2c3d4e5f6a7
Revises: 9a1b2c3d4e5f
Create Date: 2026-07-15 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "9a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "local_explainer",
        sa.Column("input_dataset_path", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("local_explainer", "input_dataset_path")

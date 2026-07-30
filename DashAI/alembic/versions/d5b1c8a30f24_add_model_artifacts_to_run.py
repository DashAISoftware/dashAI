"""add model artifacts columns to run

Revision ID: d5b1c8a30f24
Revises: c4e8a1d20f3b
Create Date: 2026-07-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5b1c8a30f24"
down_revision: Union[str, None] = "c4e8a1d20f3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the model artifacts path and status columns to the run table."""
    with op.batch_alter_table("run") as batch_op:
        batch_op.add_column(
            sa.Column("model_artifacts_path", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "model_artifacts_status",
                sa.Enum(
                    "NOT_STARTED",
                    "DELIVERED",
                    "STARTED",
                    "FINISHED",
                    "ERROR",
                    name="runstatus",
                ),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Drop the model artifacts columns from the run table."""
    with op.batch_alter_table("run") as batch_op:
        batch_op.drop_column("model_artifacts_status")
        batch_op.drop_column("model_artifacts_path")

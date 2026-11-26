"""add the loaded_model table

The job worker keeps generative models loaded between chat messages and
publishes them in this table so the API can list them and request unloads.

Revision ID: b8c9d0e1f2a3
Revises: a7f3c9e2d5b8
Create Date: 2026-11-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7f3c9e2d5b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "loaded_model",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("worker_pid", sa.Integer(), nullable=False),
        sa.Column("slot", sa.String(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("load_params", sa.JSON(), nullable=False),
        sa.Column("ram_bytes", sa.BigInteger(), nullable=True),
        sa.Column("gpu_bytes", sa.BigInteger(), nullable=True),
        sa.Column("loaded_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=False),
        sa.Column("in_use", sa.Boolean(), nullable=False),
        sa.Column("unload_requested", sa.Boolean(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("loaded_model")

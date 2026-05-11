"""Add datafile table

Revision ID: a1c3e5f7b9d2
Revises: b4f9e70098e7
Create Date: 2026-05-08 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c3e5f7b9d2"
down_revision: Union[str, None] = "b4f9e70098e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "datafile",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(), nullable=False),
        sa.Column("dataset_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("local_path", sa.String(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("downloading", "ready", "error", name="hubdownloadstatus"),
            nullable=False,
        ),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("last_modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_datafile")),
        sa.UniqueConstraint(
            "source_name",
            "dataset_id",
            name="uq_datafile_source_dataset",
        ),
    )


def downgrade() -> None:
    op.drop_table("datafile")
    op.execute("DROP TYPE IF EXISTS hubdownloadstatus")

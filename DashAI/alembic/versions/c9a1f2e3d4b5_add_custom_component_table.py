"""Add custom_component table

Revision ID: c9a1f2e3d4b5
Revises: b4f9e70098e7
Create Date: 2026-04-17 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9a1f2e3d4b5"
down_revision: Union[str, None] = "b4f9e70098e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "custom_component",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("class_name", sa.String(), nullable=False),
        sa.Column("base_type", sa.String(), nullable=False),
        sa.Column("base_class", sa.String(), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("last_modified", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_custom_component")),
        sa.UniqueConstraint("class_name", name=op.f("uq_custom_component_class_name")),
    )


def downgrade() -> None:
    op.drop_table("custom_component")

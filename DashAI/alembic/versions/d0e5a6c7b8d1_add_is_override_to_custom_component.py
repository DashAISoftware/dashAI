"""Add is_override flag to custom_component

Revision ID: d0e5a6c7b8d1
Revises: c9a1f2e3d4b5
Create Date: 2026-04-17 11:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d0e5a6c7b8d1"
down_revision: Union[str, None] = "c9a1f2e3d4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("custom_component") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_override",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("custom_component") as batch_op:
        batch_op.drop_column("is_override")

"""add is_system to user

Marks the administration account created on the first start. That account
cannot be deleted, deactivated or lose its role, so the instance always keeps
an administrator.

Revision ID: f2b8d4e6a913
Revises: e5a9c3d7b2f4
Create Date: 2026-11-26 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2b8d4e6a913"
down_revision: Union[str, None] = "e5a9c3d7b2f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Accounts that already exist are regular ones; the system account is
    # created on the next start
    with op.batch_alter_table("user") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_system", sa.Boolean(), server_default=sa.false(), nullable=False
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_column("is_system")

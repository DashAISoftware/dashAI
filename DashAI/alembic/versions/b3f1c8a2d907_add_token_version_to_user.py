"""add token_version to user

Session tokens (JWT) carry the user's token_version; increasing the column
invalidates every token issued before, which gives "log out everywhere",
password changes and deactivations an immediate effect.

Revision ID: b3f1c8a2d907
Revises: 4420b1acc4f4
Create Date: 2026-10-28 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3f1c8a2d907"
down_revision: Union[str, None] = "4420b1acc4f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The server default fills the column for users that already exist
    with op.batch_alter_table("user") as batch_op:
        batch_op.add_column(
            sa.Column("token_version", sa.Integer(), server_default="0", nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_column("token_version")

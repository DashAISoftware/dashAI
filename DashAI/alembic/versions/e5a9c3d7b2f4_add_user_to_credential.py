"""add user to credential

Credentials now belong to a user instead of the whole instance. The keys that
were already stored have no known owner, so they are deleted: each user enters
their own again.

Revision ID: e5a9c3d7b2f4
Revises: c7d2e9f4a1b3
Create Date: 2026-11-13 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5a9c3d7b2f4"
down_revision: Union[str, None] = "c7d2e9f4a1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM credential")

    with op.batch_alter_table("credential") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=False))
        batch_op.create_foreign_key(
            "fk_credential_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.drop_constraint("uq_credential_name", type_="unique")
        batch_op.create_unique_constraint(
            "uq_credential_user_id_name", ["user_id", "name"]
        )


def downgrade() -> None:
    # Several users may have a key for the same platform, which the old
    # instance-wide constraint does not allow, so the keys are deleted again
    op.execute("DELETE FROM credential")

    with op.batch_alter_table("credential") as batch_op:
        batch_op.drop_constraint("uq_credential_user_id_name", type_="unique")
        batch_op.drop_constraint("fk_credential_user_id_user", type_="foreignkey")
        batch_op.drop_column("user_id")
        batch_op.create_unique_constraint("uq_credential_name", ["name"])

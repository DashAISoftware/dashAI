"""Ensure the credential table exists

Revision ID: 72db19a8ec8d
Revises: e7a2c5f9b1d3
Create Date: 2026-10-27 12:00:00.000000

Databases created on v0.9.7.post1 or v0.9.7.post2, or on develop between
2026-07-02 and 2026-08-14, applied a7d2c9e4f1b0 while its parent was
f1a2b3c4d5e6. The merge of feat/base-credential (3f7083c5d) then rewrote that
parent to d4e8a2c6f0b1, the revision that creates ``credential``. On those
databases Alembic walks from a revision above d4e8a2c6f0b1, treats it as
applied and never creates the table, so every credential request fails with
"no such table: credential".

This revision creates the table with the same DDL when it is missing and does
nothing otherwise.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "72db19a8ec8d"
down_revision: Union[str, None] = "e7a2c5f9b1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("credential"):
        return

    op.create_table(
        "credential",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("encrypted_key", sa.Text(), nullable=False),
        sa.Column(
            "verified",
            sa.Boolean(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("last_modified", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_credential"),
        sa.UniqueConstraint("name", name="uq_credential_name"),
    )


def downgrade() -> None:
    # The table belongs to d4e8a2c6f0b1, whose downgrade drops it. Dropping it
    # here would break every revision between the two that expects it.
    pass

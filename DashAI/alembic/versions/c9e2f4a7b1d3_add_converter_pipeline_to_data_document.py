"""add converter pipeline to data document

Revision ID: c9e2f4a7b1d3
Revises: 362bcf7193f5
Create Date: 2026-11-09 12:00:00.000000

Stores the batch-level converter pipeline a document was created with, so the
parse job can apply it after loading the file. Existing rows keep a NULL
pipeline and are parsed exactly as before.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9e2f4a7b1d3"
down_revision: Union[str, None] = "362bcf7193f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("data_document", schema=None) as batch_op:
        batch_op.add_column(sa.Column("converter_pipeline", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("data_document", schema=None) as batch_op:
        batch_op.drop_column("converter_pipeline")

"""make model_session input output columns nullable

Revision ID: 4c555c310e8d
Revises: b8a884fdd290
Create Date: 2026-08-25 18:11:32.335532

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c555c310e8d'
down_revision: Union[str, None] = 'b8a884fdd290'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("model_session") as batch_op:
        batch_op.alter_column("input_columns", nullable=True)
        batch_op.alter_column("output_columns", nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("model_session") as batch_op:
        batch_op.alter_column("input_columns", nullable=False)
        batch_op.alter_column("output_columns", nullable=False)

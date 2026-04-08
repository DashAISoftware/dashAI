"""Change ConverterList to Converter

Revision ID: b4f9e70098e7
Revises: 98791b9df4f0
Create Date: 2026-03-30 16:50:49.118389

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4f9e70098e7"
down_revision: Union[str, None] = "98791b9df4f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("converter_list", "converter")


def downgrade() -> None:
    op.rename_table("converter", "converter_list")

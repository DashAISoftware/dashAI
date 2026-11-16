"""add the prompt-library flag to rag_prompt

Revision ID: a7c1e2f3b4d5
Revises: 362bcf7193f5
Create Date: 2026-11-05 00:00:00

Rows created from the prompt library need to be distinguishable from the
internal, hash-deduplicated rows ``get_or_create`` writes for a session's
pipeline. Only the former may be deleted from the library UI.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c1e2f3b4d5"
down_revision: Union[str, Sequence[str], None] = "362bcf7193f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("rag_prompt", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_library",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
    # Backfill the custom prompts that already exist: internal pipeline rows
    # are named ``pipeline_<session>_<component>`` by SetupService.
    op.execute(
        "UPDATE rag_prompt "
        "SET is_library = 1 "
        "WHERE class_name = 'CustomRAGGenerationPrompt' "
        "AND (name IS NULL OR name NOT LIKE 'pipeline\\_%' ESCAPE '\\')"
    )


def downgrade() -> None:
    with op.batch_alter_table("rag_prompt", schema=None) as batch_op:
        batch_op.drop_column("is_library")

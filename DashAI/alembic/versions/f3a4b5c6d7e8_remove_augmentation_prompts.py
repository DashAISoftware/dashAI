"""remove the unused augmentation prompt family

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-11-10 00:00:00

Augmentation prompts were never wired into the RAG pipeline; query
transformation superseded them. Drop their catalog rows and any references
that older databases may still hold.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, Sequence[str], None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_AUGMENTATION_CLASSES = (
    "AugmentationPrompt",
    "CustomAugmentationPrompt",
    "DefaultAugmentationPrompt",
)

_CLASS_FILTER = (
    "class_name IN ('AugmentationPrompt', 'CustomAugmentationPrompt', "
    "'DefaultAugmentationPrompt')"
)


def upgrade() -> None:
    connection = op.get_bind()

    connection.execute(
        sa.text(
            "DELETE FROM rag_session_prompt WHERE prompt_id IN "
            f"(SELECT id FROM rag_prompt WHERE {_CLASS_FILTER})"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE rag_pipeline SET prompt_id = NULL WHERE prompt_id IN "
            f"(SELECT id FROM rag_prompt WHERE {_CLASS_FILTER})"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE rag_prompt SET based_on_id = NULL WHERE based_on_id IN "
            f"(SELECT id FROM rag_prompt WHERE {_CLASS_FILTER})"
        )
    )
    connection.execute(sa.text(f"DELETE FROM rag_prompt WHERE {_CLASS_FILTER}"))


def downgrade() -> None:
    """No-op: the removed prompt family is not recoverable."""

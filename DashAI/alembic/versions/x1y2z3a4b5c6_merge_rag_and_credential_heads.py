"""merge the RAG feature heads with develop's credential-table head

``feat/rag-query-transformation`` added ``rag_retrieval_model`` and
``generative_process.progress`` (merged again by ``p9q0r1s2t3u4``), while
``develop`` added ``72db19a8ec8d`` to recreate the credential table. Both
lineages descend from ``c5d1a9e74f28`` and touch unrelated tables, so this
empty merge point gives Alembic a single head again.

Revision ID: x1y2z3a4b5c6
Revises: 72db19a8ec8d, p9q0r1s2t3u4
Create Date: 2026-10-28
"""

from typing import Sequence, Union

revision: str = "x1y2z3a4b5c6"
down_revision: Union[str, Sequence[str], None] = ("72db19a8ec8d", "p9q0r1s2t3u4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

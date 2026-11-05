"""merge forecasting and RAG heads

The forecasting branch already merged ``develop``'s credential-table head
(``b5ced45240cd`` merges ``72db19a8ec8d`` and ``d4a9c7e1f3b5``), while the RAG
branch merged the same ``develop`` head with its own retrieval/progress head
(``x1y2z3a4b5c6`` merges ``72db19a8ec8d`` and ``p9q0r1s2t3u4``). Both merge
points descend from ``72db19a8ec8d`` and touch unrelated tables, so this empty
merge point gives Alembic a single head again.

Revision ID: 532d6079557c
Revises: b5ced45240cd, x1y2z3a4b5c6
Create Date: 2026-11-04 10:20:07.015487

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "532d6079557c"
down_revision: Union[str, Sequence[str], None] = ("b5ced45240cd", "x1y2z3a4b5c6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

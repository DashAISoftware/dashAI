"""merge dag-pipelines and develop heads

Revision ID: 0dc6fd4637a3
Revises: b4f9e70098e7, c4f7a8b2d1e3
Create Date: 2026-04-02 19:32:55.182155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0dc6fd4637a3'
down_revision: Union[str, None] = ('b4f9e70098e7', 'c4f7a8b2d1e3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

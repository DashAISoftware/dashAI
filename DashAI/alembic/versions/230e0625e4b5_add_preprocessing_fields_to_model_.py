"""add preprocessing fields to model_session

Revision ID: 230e0625e4b5
Revises: 21b1178f2d9d
Create Date: 2026-08-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '230e0625e4b5'
down_revision: Union[str, None] = '21b1178f2d9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('model_session', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'preprocessing_status',
                sa.Enum(
                    'NOT_STARTED', 'DELIVERED', 'STARTED', 'FINISHED', 'ERROR',
                    name='sessionpreprocessingstatus',
                ),
                nullable=False,
                server_default="NOT_STARTED",
            )
        )
        batch_op.add_column(sa.Column('preprocessing_huey_id', sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column('preprocessing_delivery_time', sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('preprocessing_start_time', sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('preprocessing_end_time', sa.DateTime(), nullable=True)
        )
        batch_op.add_column(sa.Column('preprocessed_path', sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('model_session', schema=None) as batch_op:
        batch_op.drop_column('preprocessed_path')
        batch_op.drop_column('preprocessing_end_time')
        batch_op.drop_column('preprocessing_start_time')
        batch_op.drop_column('preprocessing_delivery_time')
        batch_op.drop_column('preprocessing_huey_id')
        batch_op.drop_column('preprocessing_status')

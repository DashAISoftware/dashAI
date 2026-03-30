"""Atomize train node into split/task/metrics tables.

Revision ID: c4f7a8b2d1e3
Revises: 98791b9df4f0
Create Date: 2026-03-25 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4f7a8b2d1e3"
down_revision: Union[str, None] = "98791b9df4f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(
        column["name"] == column_name
        for column in inspector.get_columns(table_name)
    )


def upgrade() -> None:
    if _table_exists("pipeline"):
        if not _column_exists("pipeline", "split_data"):
            op.add_column("pipeline", sa.Column("split_data", sa.JSON(), nullable=True))
        if not _column_exists("pipeline", "task_and_model"):
            op.add_column(
                "pipeline", sa.Column("task_and_model", sa.JSON(), nullable=True)
            )
        if not _column_exists("pipeline", "metrics_result"):
            op.add_column(
                "pipeline", sa.Column("metrics_result", sa.JSON(), nullable=True)
            )

    if not _table_exists("split_data_node"):
        op.create_table(
            "split_data_node",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("pipeline_id", sa.Integer(), nullable=False),
            sa.Column("input_columns", sa.JSON(), nullable=False),
            sa.Column("output_columns", sa.JSON(), nullable=False),
            sa.Column("splits", sa.JSON(), nullable=False),
            sa.Column("created", sa.DateTime(), nullable=True),
            sa.Column("last_modified", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["pipeline_id"], ["pipeline.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists("task_and_model_node"):
        op.create_table(
            "task_and_model_node",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("pipeline_id", sa.Integer(), nullable=False),
            sa.Column("task_name", sa.String(), nullable=False),
            sa.Column("model_name", sa.String(), nullable=False),
            sa.Column("parameters", sa.JSON(), nullable=True),
            sa.Column("model_path", sa.String(), nullable=True),
            sa.Column("created", sa.DateTime(), nullable=True),
            sa.Column("last_modified", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["pipeline_id"], ["pipeline.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists("metrics_node"):
        op.create_table(
            "metrics_node",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("pipeline_id", sa.Integer(), nullable=False),
            sa.Column("metric_names", sa.JSON(), nullable=False),
            sa.Column("results", sa.JSON(), nullable=True),
            sa.Column("created", sa.DateTime(), nullable=True),
            sa.Column("last_modified", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["pipeline_id"], ["pipeline.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    if _table_exists("metrics_node"):
        op.drop_table("metrics_node")

    if _table_exists("task_and_model_node"):
        op.drop_table("task_and_model_node")

    if _table_exists("split_data_node"):
        op.drop_table("split_data_node")

    if _table_exists("pipeline"):
        with op.batch_alter_table("pipeline", schema=None) as batch_op:
            if _column_exists("pipeline", "metrics_result"):
                batch_op.drop_column("metrics_result")
            if _column_exists("pipeline", "task_and_model"):
                batch_op.drop_column("task_and_model")
            if _column_exists("pipeline", "split_data"):
                batch_op.drop_column("split_data")

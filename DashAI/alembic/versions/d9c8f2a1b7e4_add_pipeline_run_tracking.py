"""Add pipeline run tracking tables.

Revision ID: d9c8f2a1b7e4
Revises: 0dc6fd4637a3
Create Date: 2026-04-10 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d9c8f2a1b7e4"
down_revision: Union[str, None] = "0dc6fd4637a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def _table_exists(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()

def upgrade() -> None:
    if not _table_exists("pipeline_run"):
        op.create_table(
            "pipeline_run",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("pipeline_id", sa.Integer(), nullable=False),
            sa.Column("steps", sa.JSON(), nullable=True),
            sa.Column("edges", sa.JSON(), nullable=True),
            sa.Column("created", sa.DateTime(), nullable=False),
            sa.Column("last_modified", sa.DateTime(), nullable=False),
            sa.Column("delivery_time", sa.DateTime(), nullable=True),
            sa.Column("start_time", sa.DateTime(), nullable=True),
            sa.Column("end_time", sa.DateTime(), nullable=True),
            sa.Column(
                "status",
                sa.Enum(
                    "NOT_STARTED",
                    "DELIVERED",
                    "STARTED",
                    "FINISHED",
                    "ERROR",
                    name="pipelinerunstatus",
                ),
                nullable=False,
            ),
            sa.Column("error_message", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(["pipeline_id"], ["pipeline.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists("pipeline_node_run"):
        op.create_table(
            "pipeline_node_run",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("pipeline_run_id", sa.Integer(), nullable=False),
            sa.Column("node_id", sa.String(), nullable=False),
            sa.Column("node_type", sa.String(), nullable=False),
            sa.Column("config", sa.JSON(), nullable=True),
            sa.Column("input", sa.JSON(), nullable=True),
            sa.Column("output", sa.JSON(), nullable=True),
            sa.Column("created", sa.DateTime(), nullable=False),
            sa.Column("last_modified", sa.DateTime(), nullable=False),
            sa.Column("delivery_time", sa.DateTime(), nullable=True),
            sa.Column("start_time", sa.DateTime(), nullable=True),
            sa.Column("end_time", sa.DateTime(), nullable=True),
            sa.Column(
                "status",
                sa.Enum(
                    "NOT_STARTED",
                    "DELIVERED",
                    "STARTED",
                    "FINISHED",
                    "ERROR",
                    name="noderunstatus",
                ),
                nullable=False,
            ),
            sa.Column("error_message", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(
                ["pipeline_run_id"], ["pipeline_run.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists("pipeline_node_artifact"):
        op.create_table(
            "pipeline_node_artifact",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("node_run_id", sa.Integer(), nullable=False),
            sa.Column("key", sa.String(), nullable=False),
            sa.Column("value", sa.JSON(), nullable=True),
            sa.Column("created", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["node_run_id"], ["pipeline_node_run.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )

def downgrade() -> None:
    if _table_exists("pipeline_node_artifact"):
        op.drop_table("pipeline_node_artifact")

    if _table_exists("pipeline_node_run"):
        op.drop_table("pipeline_node_run")

    if _table_exists("pipeline_run"):
        op.drop_table("pipeline_run")
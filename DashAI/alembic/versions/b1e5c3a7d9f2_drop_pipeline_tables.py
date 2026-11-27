"""Drop the pipeline tables.

The pipelines feature is removed, so its four tables go with it: the graph
definitions in ``pipeline`` and the execution tracking in ``pipeline_run``,
``pipeline_node_run`` and ``pipeline_node_artifact``. No other feature reads
or writes them. The downgrade recreates them empty.

Revision ID: b1e5c3a7d9f2
Revises: 83bd5b526fac
Create Date: 2026-11-24 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b1e5c3a7d9f2"
down_revision: Union[str, None] = "83bd5b526fac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = (
    "pipeline_node_artifact",
    "pipeline_node_run",
    "pipeline_run",
    "pipeline",
)


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    for table in TABLES:
        if table in existing:
            op.drop_table(table)


def downgrade() -> None:
    op.create_table(
        "pipeline",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=True),
        sa.Column("edges", sa.JSON(), nullable=True),
        sa.Column("exploration", sa.JSON(), nullable=True),
        sa.Column("train", sa.JSON(), nullable=True),
        sa.Column("prediction", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

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
        sa.ForeignKeyConstraint(
            ["pipeline_id"],
            ["pipeline.id"],
            name=op.f("fk_pipeline_run_pipeline_id_pipeline"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pipeline_run")),
    )

    op.create_table(
        "pipeline_node_run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.String(), nullable=False),
        sa.Column("block_id", sa.String(), nullable=False),
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
                "CANCELLED",
                name="noderunstatus",
            ),
            nullable=False,
        ),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_run.id"],
            name=op.f("fk_pipeline_node_run_pipeline_run_id_pipeline_run"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pipeline_node_run")),
    )

    op.create_table(
        "pipeline_node_artifact",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("node_run_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.JSON(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["node_run_id"],
            ["pipeline_node_run.id"],
            name=op.f("fk_pipeline_node_artifact_node_run_id_pipeline_node_run"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pipeline_node_artifact")),
    )

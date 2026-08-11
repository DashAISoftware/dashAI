"""Add insight_result table

Stores the result of one AI-generated insight request (the text a
generative model produced when analyzing an already-computed result, e.g.
a partial dependence curve). ``consumer_type``/``consumer_id``/
``consumer_ref`` reference the domain row the insight is about
polymorphically, so future consumers (run comparison, task suggestion,
...) never require another migration.

Revision ID: 699f0e7cf398
Revises: c4e8a1d20f3b
Create Date: 2026-08-11 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "699f0e7cf398"
down_revision: Union[str, None] = "c4e8a1d20f3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "insight_result",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("consumer_type", sa.String(), nullable=False),
        sa.Column("consumer_id", sa.Integer(), nullable=False),
        sa.Column("consumer_ref", sa.String(), nullable=True),
        sa.Column("context_data", sa.JSON(), nullable=False),
        sa.Column("context_metadata", sa.JSON(), nullable=True),
        sa.Column("analyzer_path", sa.String(), nullable=False),
        sa.Column("provider_kind", sa.String(), nullable=False),
        sa.Column("provider_params", sa.JSON(), nullable=True),
        sa.Column("prompt", sa.JSON(), nullable=True),
        sa.Column("result_text", sa.Text(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("huey_id", sa.String(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=False),
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
                name="insightstatus",
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_insight_result")),
    )


def downgrade() -> None:
    op.drop_table("insight_result")

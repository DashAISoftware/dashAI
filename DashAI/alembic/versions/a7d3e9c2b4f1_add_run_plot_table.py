"""add the run_plot table

Revision ID: a7d3e9c2b4f1
Revises: 362bcf7193f5
Create Date: 2026-11-09 12:00:00.000000

A run keeps the plots of each of its views (the hyperparameter search and,
for a forecasting run, its forecasts) in a file, and the user's edits to
them in ``plot_overrides``, one row per run and view.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7d3e9c2b4f1"
down_revision: Union[str, None] = "362bcf7193f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "run_plot",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("view", sa.String(), nullable=False),
        sa.Column("artifacts_path", sa.String(), nullable=False),
        sa.Column("plot_overrides", sa.JSON(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["run.id"],
            name=op.f("fk_run_plot_run_id_run"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_run_plot")),
        sa.UniqueConstraint("run_id", "view", name="uq_run_plot_view"),
    )


def downgrade() -> None:
    op.drop_table("run_plot")

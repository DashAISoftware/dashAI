"""Drop the plugin and tag tables

Revision ID: f3b8d1c6a920
Revises: 49d7035ce11f
Create Date: 2026-10-15 00:00:00.000000

Installed plugins are described by their folder (``plugins/installed/<id>/``
and its ``.source``), not by the database. ``plugin`` and ``tag`` belonged to
the PyPI catalog. Downgrading recreates both empty, as they were.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3b8d1c6a920"
down_revision: Union[str, None] = "49d7035ce11f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("tag")
    op.drop_table("plugin")


def downgrade() -> None:
    op.create_table(
        "plugin",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("installed_version", sa.String(), nullable=False),
        sa.Column("lastest_version", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("REGISTERED", "INSTALLED", "ERROR", name="pluginstatus"),
            nullable=False,
        ),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("description_content_type", sa.String(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("last_modified", sa.DateTime(), nullable=False),
        sa.Column("verified", sa.Boolean(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "tag",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plugin_id", sa.Integer(), nullable=False),
        sa.Column(
            "name",
            sa.Enum(
                "DashAI",
                "Package",
                "Task",
                "Model",
                "Metric",
                "Dataloader",
                "Converter",
                "Explainer",
                name="plugintag",
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["plugin_id"], ["plugin.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

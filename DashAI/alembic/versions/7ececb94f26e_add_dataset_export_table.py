"""Add dataset_export table

Revision ID: 7ececb94f26e
Revises: 72db19a8ec8d
Create Date: 2026-11-09 18:55:11.850845

Records every attempt to publish a DashAI dataset to an external platform
(OpenML for now): its parameters, status and, once published, the id and link
the platform assigned. ``dataset_id`` is nullable so the record survives the
deletion of the dataset, since the published copy stays on the platform.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7ececb94f26e"
down_revision: Union[str, None] = "72db19a8ec8d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dataset_export",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("dataset_name", sa.String(), nullable=False),
        sa.Column("exporter_name", sa.String(), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "PREPARING",
                "UPLOADING",
                "PUBLISHED",
                "ERROR",
                name="datasetexportstatus",
            ),
            nullable=False,
        ),
        sa.Column("remote_id", sa.String(), nullable=True),
        sa.Column("remote_url", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("huey_id", sa.String(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("last_modified", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["dataset.id"],
            name=op.f("fk_dataset_export_dataset_id_dataset"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dataset_export")),
    )
    with op.batch_alter_table("dataset_export", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_dataset_export_dataset_id"), ["dataset_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("dataset_export", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_dataset_export_dataset_id"))

    op.drop_table("dataset_export")

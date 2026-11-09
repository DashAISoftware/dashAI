"""add project to dataset

Datasets now belong to a project and their name is unique inside it, instead
of across the whole instance. Existing datasets keep no project: they become
"universal", visible to every user, and their names stay unique among them.

Revision ID: c7d2e9f4a1b3
Revises: b3f1c8a2d907
Create Date: 2026-11-09 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7d2e9f4a1b3"
down_revision: Union[str, None] = "b3f1c8a2d907"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The initial migration created the unique constraint on the name without a
# name, so the batch operation needs this convention to find and drop it
NAMING_CONVENTION = {"uq": "uq_%(table_name)s_%(column_0_name)s"}


def upgrade() -> None:
    with op.batch_alter_table(
        "dataset", naming_convention=NAMING_CONVENTION
    ) as batch_op:
        batch_op.add_column(sa.Column("project_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_dataset_project_id_project",
            "project",
            ["project_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.drop_constraint("uq_dataset_name", type_="unique")
        batch_op.create_unique_constraint(
            "uq_dataset_project_id_name", ["project_id", "name"]
        )

    op.create_index(
        "uq_dataset_universal_name",
        "dataset",
        ["name"],
        unique=True,
        sqlite_where=sa.text("project_id IS NULL"),
    )


def downgrade() -> None:
    # Fails if two projects have a dataset with the same name, since the old
    # constraint made names unique across the instance
    op.drop_index("uq_dataset_universal_name", table_name="dataset")

    with op.batch_alter_table("dataset") as batch_op:
        batch_op.drop_constraint("uq_dataset_project_id_name", type_="unique")
        batch_op.drop_constraint("fk_dataset_project_id_project", type_="foreignkey")
        batch_op.drop_column("project_id")
        batch_op.create_unique_constraint("uq_dataset_name", ["name"])

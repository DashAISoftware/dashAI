"""rebuild rbac tables

Moves the global role from user_role_project (where project_id = NULL was
part of the primary key, which PostgreSQL rejects) to user.global_role_id,
keeps user_role_project for project roles only and adds the profile, access
and audit columns used by the multi-user views.

The RBAC tables hold no real data yet, so they are dropped and recreated
instead of being altered column by column.

Revision ID: 4420b1acc4f4
Revises: 341ba60c36de
Create Date: 2026-10-27 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4420b1acc4f4"
down_revision: Union[str, None] = "341ba60c36de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the previous RBAC tables, children before parents
    op.drop_table("user_role_project")
    op.drop_table("role_permission")
    op.drop_table("user")
    op.drop_table("role")
    op.drop_table("project")
    op.drop_table("permission")

    # Recreate them, parents before children
    op.create_table(
        "role",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uid", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.CheckConstraint(
            "scope IN ('global', 'project')", name=op.f("ck_role_scope")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role")),
        sa.UniqueConstraint("name", name=op.f("uq_role_name")),
        sa.UniqueConstraint("uid", name=op.f("uq_role_uid")),
    )
    op.create_table(
        "permission",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uid", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_permission")),
        sa.UniqueConstraint("name", name=op.f("uq_permission_name")),
        sa.UniqueConstraint("uid", name=op.f("uq_permission_uid")),
    )
    op.create_table(
        "role_permission",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permission.id"],
            name=op.f("fk_role_permission_permission_id_permission"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["role.id"],
            name=op.f("fk_role_permission_role_id_role"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "role_id", "permission_id", name=op.f("pk_role_permission")
        ),
    )
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("social_name", sa.String(length=100), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("github", sa.String(length=255), nullable=True),
        sa.Column("linkedin", sa.String(length=255), nullable=True),
        sa.Column("legal_name", sa.String(length=150), nullable=True),
        sa.Column("organization", sa.String(length=150), nullable=True),
        sa.Column("position", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("global_role_id", sa.Integer(), nullable=False),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("last_modified", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["global_role_id"],
            ["role.id"],
            name=op.f("fk_user_global_role_id_role"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user")),
        sa.UniqueConstraint("email", name=op.f("uq_user_email")),
        sa.UniqueConstraint("username", name=op.f("uq_user_username")),
    )
    op.create_table(
        "project",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_archived", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("last_modified", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["user.id"],
            name=op.f("fk_project_created_by_id_user"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project")),
    )
    op.create_table(
        "user_role_project",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.id"],
            name=op.f("fk_user_role_project_project_id_project"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["role.id"],
            name=op.f("fk_user_role_project_role_id_role"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name=op.f("fk_user_role_project_user_id_user"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "user_id", "project_id", name=op.f("pk_user_role_project")
        ),
    )


def downgrade() -> None:
    # Drop the rebuilt tables, children before parents
    op.drop_table("user_role_project")
    op.drop_table("project")
    op.drop_table("role_permission")
    op.drop_table("user")
    op.drop_table("permission")
    op.drop_table("role")

    # Restore the tables exactly as migrations ec2c95318ffb and 508c9f7db00a
    # left them
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("last_modified", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user")),
        sa.UniqueConstraint("email", name=op.f("uq_user_email")),
        sa.UniqueConstraint("username", name=op.f("uq_user_username")),
    )
    op.create_table(
        "permission",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("uid", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_permission")),
        sa.UniqueConstraint("name", name=op.f("uq_permission_name")),
        sa.UniqueConstraint("uid", name=op.f("uq_permission_uid")),
    )
    op.create_table(
        "project",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project")),
    )
    op.create_table(
        "role",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("uid", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role")),
        sa.UniqueConstraint("name", name=op.f("uq_role_name")),
        sa.UniqueConstraint("uid", name=op.f("uq_role_uid")),
    )
    op.create_table(
        "role_permission",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permission.id"],
            name=op.f("fk_role_permission_permission_id_permission"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["role.id"],
            name=op.f("fk_role_permission_role_id_role"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "role_id", "permission_id", name=op.f("pk_role_permission")
        ),
    )
    op.create_table(
        "user_role_project",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.id"],
            name=op.f("fk_user_role_project_project_id_project"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["role.id"],
            name=op.f("fk_user_role_project_role_id_role"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name=op.f("fk_user_role_project_user_id_user"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "user_id", "role_id", "project_id", name=op.f("pk_user_role_project")
        ),
    )

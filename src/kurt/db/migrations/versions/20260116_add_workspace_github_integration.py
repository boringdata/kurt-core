"""add_workspace_github_integration

Revision ID: 58703e7a5ec5
Revises: 84688a81b9ab
Create Date: 2026-01-16 09:09:12.617414+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "58703e7a5ec5"
down_revision: Union[str, None] = "84688a81b9ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create workspaces table
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("github_owner", sa.String(), nullable=False),
        sa.Column("github_repo", sa.String(), nullable=False),
        sa.Column("github_default_branch", sa.String(), nullable=False, server_default="main"),
        sa.Column("github_installation_id", sa.Integer(), nullable=True),
        sa.Column("github_installation_token", sa.String(), nullable=True),
        sa.Column("github_installation_token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("auto_commit_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("auto_commit_interval", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("owner_user_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_workspaces_slug", "workspaces", ["slug"])
    op.create_index("ix_workspaces_owner_user_id", "workspaces", ["owner_user_id"])

    # Create workspace_members table
    op.create_table(
        "workspace_members",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("github_username", sa.String(), nullable=False),
        sa.Column("github_access_token", sa.String(), nullable=True),
        sa.Column("github_token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("role", sa.String(), nullable=False, server_default="editor"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("invited_by", sa.String(), nullable=True),
        sa.Column("invited_at", sa.DateTime(), nullable=True),
        sa.Column("joined_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_workspace_members_workspace_id", "workspace_members", ["workspace_id"])
    op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_workspace_members_user_id", "workspace_members")
    op.drop_index("ix_workspace_members_workspace_id", "workspace_members")
    op.drop_table("workspace_members")

    op.drop_index("ix_workspaces_owner_user_id", "workspaces")
    op.drop_index("ix_workspaces_slug", "workspaces")
    op.drop_table("workspaces")

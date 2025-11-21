"""Add workspaces and workspace_members tables.

Revision ID: 20251121_0012
Revises: 20251120_0011
Create Date: 2025-11-21

This migration adds workspace management tables for multi-tenant cloud deployments:

1. workspaces table: Contains workspace/tenant definitions
   - id: UUID primary key
   - name: Workspace display name
   - slug: URL-friendly unique identifier
   - owner_email: Email of workspace owner
   - organization: Optional organization name
   - plan: Subscription plan (free, pro, enterprise)
   - max_documents: Optional limit on document count
   - max_users: Optional limit on user count
   - settings: JSON settings object
   - is_active: Workspace activation status
   - created_at, updated_at: Timestamps

2. workspace_members table: Contains workspace membership and access control
   - id: UUID primary key
   - workspace_id: Foreign key to workspaces table
   - user_email: User's email address
   - user_id: Optional external auth provider ID
   - role: User role (owner, admin, member, viewer)
   - is_active: Member activation status
   - invited_at, joined_at: Invitation and join timestamps
   - invited_by: Email of inviter
   - created_at, updated_at: Timestamps

Note: In local SQLite mode, workspace features are not used (tenant_id defaults
to '00000000-0000-0000-0000-000000000000'). These tables are primarily for
cloud PostgreSQL deployments.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251121_0012"
down_revision = "20251120_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add workspaces and workspace_members tables."""

    # Check if we're using SQLite or PostgreSQL
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # Create workspaces table
    if is_sqlite:
        # SQLite: Use String(36) for UUIDs
        op.create_table(
            "workspaces",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("slug", sa.String(), nullable=False),
            sa.Column("owner_email", sa.String(), nullable=True),
            sa.Column("organization", sa.String(), nullable=True),
            sa.Column("plan", sa.String(), nullable=False, server_default="free"),
            sa.Column("max_documents", sa.Integer(), nullable=True),
            sa.Column("max_users", sa.Integer(), nullable=True),
            sa.Column("settings", sa.JSON(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        # PostgreSQL: Use UUID type
        op.create_table(
            "workspaces",
            sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("slug", sa.String(), nullable=False),
            sa.Column("owner_email", sa.String(), nullable=True),
            sa.Column("organization", sa.String(), nullable=True),
            sa.Column("plan", sa.String(), nullable=False, server_default="free"),
            sa.Column("max_documents", sa.Integer(), nullable=True),
            sa.Column("max_users", sa.Integer(), nullable=True),
            sa.Column("settings", sa.dialects.postgresql.JSONB(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    # Create indexes on workspaces
    op.create_index(op.f("ix_workspaces_name"), "workspaces", ["name"], unique=False)
    op.create_index(op.f("ix_workspaces_slug"), "workspaces", ["slug"], unique=True)
    op.create_index(op.f("ix_workspaces_owner_email"), "workspaces", ["owner_email"], unique=False)

    # Create workspace_members table
    if is_sqlite:
        # SQLite: Use String(36) for UUIDs
        op.create_table(
            "workspace_members",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("workspace_id", sa.String(36), nullable=False),
            sa.Column("user_email", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=True),
            sa.Column("role", sa.String(), nullable=False, server_default="member"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column(
                "invited_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("joined_at", sa.DateTime(), nullable=True),
            sa.Column("invited_by", sa.String(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        )
    else:
        # PostgreSQL: Use UUID type
        op.create_table(
            "workspace_members",
            sa.Column("id", sa.dialects.postgresql.UUID(), nullable=False),
            sa.Column("workspace_id", sa.dialects.postgresql.UUID(), nullable=False),
            sa.Column("user_email", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=True),
            sa.Column("role", sa.String(), nullable=False, server_default="member"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column(
                "invited_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("joined_at", sa.DateTime(), nullable=True),
            sa.Column("invited_by", sa.String(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        )

    # Create indexes on workspace_members
    op.create_index(
        op.f("ix_workspace_members_workspace_id"),
        "workspace_members",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workspace_members_user_email"),
        "workspace_members",
        ["user_email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workspace_members_user_id"), "workspace_members", ["user_id"], unique=False
    )


def downgrade() -> None:
    """Remove workspaces and workspace_members tables."""

    # Drop workspace_members table and its indexes
    op.drop_index(op.f("ix_workspace_members_user_id"), table_name="workspace_members")
    op.drop_index(op.f("ix_workspace_members_user_email"), table_name="workspace_members")
    op.drop_index(op.f("ix_workspace_members_workspace_id"), table_name="workspace_members")
    op.drop_table("workspace_members")

    # Drop workspaces table and its indexes
    op.drop_index(op.f("ix_workspaces_owner_email"), table_name="workspaces")
    op.drop_index(op.f("ix_workspaces_slug"), table_name="workspaces")
    op.drop_index(op.f("ix_workspaces_name"), table_name="workspaces")
    op.drop_table("workspaces")

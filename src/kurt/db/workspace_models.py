"""
Workspace and team models for multi-tenant collaboration.

These models enable:
- Workspace → GitHub repository binding
- Team member management with GitHub OAuth
- GitHub App installation tracking
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel

from kurt.db.models import TimestampMixin


class Workspace(TimestampMixin, SQLModel, table=True):
    """
    Multi-tenant workspace linked to a GitHub repository.

    Each workspace represents a team collaborating on one GitHub repo.
    All documents in the workspace are files within that repo.
    """

    __tablename__ = "workspaces"

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        primary_key=True,
        description="Unique workspace identifier",
    )

    name: str = Field(description="Human-readable workspace name")
    slug: str = Field(
        unique=True,
        index=True,
        description="URL-friendly workspace identifier (e.g., 'acme-docs')",
    )

    # GitHub Integration
    github_owner: str = Field(description="GitHub organization or user (e.g., 'acme-corp')")
    github_repo: str = Field(description="GitHub repository name (e.g., 'documentation')")
    github_default_branch: str = Field(
        default="main",
        description="Default branch for new documents",
    )

    # GitHub App Installation
    github_installation_id: Optional[int] = Field(
        default=None,
        description="GitHub App installation ID (set when user installs the app)",
    )
    github_installation_token: Optional[str] = Field(
        default=None,
        description="Installation access token (auto-refreshed, encrypted in production)",
    )
    github_installation_token_expires_at: Optional[datetime] = Field(
        default=None,
        description="Token expiration time (typically 1 hour from issue)",
    )

    # Auto-commit Settings
    auto_commit_enabled: bool = Field(
        default=True,
        description="Enable automatic commits every N seconds",
    )
    auto_commit_interval: int = Field(
        default=300,
        description="Auto-commit interval in seconds (default: 5 minutes)",
    )

    # Owner
    owner_user_id: str = Field(
        index=True,
        description="User ID of the workspace creator/owner",
    )


class WorkspaceMember(TimestampMixin, SQLModel, table=True):
    """
    Team member with access to a workspace.

    Each member authenticates via GitHub OAuth to access the workspace's repo.
    """

    __tablename__ = "workspace_members"

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        primary_key=True,
    )

    workspace_id: str = Field(
        foreign_key="workspaces.id",
        index=True,
        description="Workspace this member belongs to",
    )

    user_id: str = Field(
        index=True,
        description="Kurt user ID (from auth system)",
    )

    # GitHub OAuth Credentials (scoped to workspace repo)
    github_username: str = Field(description="Member's GitHub username")
    github_access_token: Optional[str] = Field(
        default=None,
        description="GitHub OAuth token (encrypted, for user actions)",
    )
    github_token_expires_at: Optional[datetime] = Field(
        default=None,
        description="Token expiration (if using GitHub App user-to-server tokens)",
    )

    # Role
    role: str = Field(
        default="editor",
        description="Member role: viewer, editor, admin",
    )

    # Status
    is_active: bool = Field(
        default=True,
        description="False if member was removed from workspace",
    )

    # Invitation tracking
    invited_by: Optional[str] = Field(
        default=None,
        description="User ID of the inviter",
    )
    invited_at: Optional[datetime] = Field(default=None)
    joined_at: Optional[datetime] = Field(default=None)

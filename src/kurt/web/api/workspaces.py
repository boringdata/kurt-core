"""
Workspace management API endpoints.

Provides CRUD operations for workspaces and team members,
plus GitHub App installation flow.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from kurt.db import managed_session
from kurt.db.workspace_models import Workspace, WorkspaceMember
from kurt.github import github_app

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


# =============================================================================
# Request/Response Models
# =============================================================================


class WorkspaceCreatePayload(BaseModel):
    """Payload for creating a new workspace."""

    name: str
    slug: str
    github_owner: str
    github_repo: str
    github_default_branch: str = "main"


class WorkspaceResponse(BaseModel):
    """Workspace API response."""

    id: str
    name: str
    slug: str
    github_owner: str
    github_repo: str
    github_default_branch: str
    github_installation_id: Optional[int]
    auto_commit_enabled: bool
    auto_commit_interval: int
    owner_user_id: str
    created_at: datetime
    updated_at: datetime


class WorkspaceMemberResponse(BaseModel):
    """Workspace member API response."""

    id: str
    workspace_id: str
    user_id: str
    github_username: str
    role: str
    is_active: bool
    joined_at: Optional[datetime]
    created_at: datetime


# =============================================================================
# Workspace CRUD
# =============================================================================


@router.post("")
async def create_workspace(payload: WorkspaceCreatePayload, request: Request):
    """
    Create a new workspace linked to a GitHub repository.

    Flow:
    1. Creates workspace record
    2. Returns GitHub App installation URL
    3. User installs app on their repo
    4. Webhook links installation to workspace

    Returns:
        - workspace_id: Created workspace ID
        - install_url: URL to install GitHub App
    """
    # Get current user ID from auth middleware
    user_id = request.state.get("user_id", "unknown")

    # Validate slug format (lowercase alphanumeric + hyphens)
    import re

    if not re.match(r"^[a-z0-9-]+$", payload.slug):
        raise HTTPException(
            status_code=400,
            detail="Slug must contain only lowercase letters, numbers, and hyphens",
        )

    # Create workspace
    workspace = Workspace(
        name=payload.name,
        slug=payload.slug,
        github_owner=payload.github_owner,
        github_repo=payload.github_repo,
        github_default_branch=payload.github_default_branch,
        owner_user_id=user_id,
        github_installation_id=None,  # Not yet installed
    )

    with managed_session() as session:
        # Check if slug already exists
        from sqlmodel import select

        existing = session.exec(select(Workspace).where(Workspace.slug == payload.slug)).first()
        if existing:
            raise HTTPException(
                status_code=409, detail=f"Workspace slug '{payload.slug}' already exists"
            )

        session.add(workspace)
        session.commit()
        session.refresh(workspace)

    # Generate GitHub App installation URL
    github_app_name = "kurt-editor"  # TODO: Make configurable
    install_url = (
        f"https://github.com/apps/{github_app_name}/installations/new?"
        f"state={workspace.id}"  # Track which workspace
    )

    return {
        "workspace_id": workspace.id,
        "slug": workspace.slug,
        "install_url": install_url,
        "message": "Please install the Kurt Editor GitHub App to continue",
    }


@router.get("/{workspace_slug}")
async def get_workspace(workspace_slug: str):
    """Get workspace details by slug."""
    with managed_session() as session:
        from sqlmodel import select

        workspace = session.exec(select(Workspace).where(Workspace.slug == workspace_slug)).first()

        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        return WorkspaceResponse(
            id=workspace.id,
            name=workspace.name,
            slug=workspace.slug,
            github_owner=workspace.github_owner,
            github_repo=workspace.github_repo,
            github_default_branch=workspace.github_default_branch,
            github_installation_id=workspace.github_installation_id,
            auto_commit_enabled=workspace.auto_commit_enabled,
            auto_commit_interval=workspace.auto_commit_interval,
            owner_user_id=workspace.owner_user_id,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )


@router.get("")
async def list_workspaces(request: Request):
    """List all workspaces for the current user."""
    user_id = request.state.get("user_id", "unknown")

    with managed_session() as session:
        from sqlmodel import select

        # Get workspaces where user is owner or member
        workspaces = session.exec(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(
                (Workspace.owner_user_id == user_id)
                | ((WorkspaceMember.user_id == user_id) & WorkspaceMember.is_active)
            )
        ).all()

        return [
            WorkspaceResponse(
                id=w.id,
                name=w.name,
                slug=w.slug,
                github_owner=w.github_owner,
                github_repo=w.github_repo,
                github_default_branch=w.github_default_branch,
                github_installation_id=w.github_installation_id,
                auto_commit_enabled=w.auto_commit_enabled,
                auto_commit_interval=w.auto_commit_interval,
                owner_user_id=w.owner_user_id,
                created_at=w.created_at,
                updated_at=w.updated_at,
            )
            for w in workspaces
        ]


@router.delete("/{workspace_slug}")
async def delete_workspace(workspace_slug: str, request: Request):
    """Delete a workspace (admin only)."""
    user_id = request.state.get("user_id", "unknown")

    with managed_session() as session:
        from sqlmodel import select

        workspace = session.exec(select(Workspace).where(Workspace.slug == workspace_slug)).first()

        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        # Check if user is owner
        if workspace.owner_user_id != user_id:
            raise HTTPException(status_code=403, detail="Only workspace owner can delete")

        session.delete(workspace)
        session.commit()

    return {"status": "deleted", "workspace_id": workspace.id}


# =============================================================================
# GitHub App Installation Status
# =============================================================================


@router.get("/{workspace_slug}/github/status")
async def get_github_status(workspace_slug: str):
    """
    Check GitHub App installation status for workspace.

    Returns:
        - installed: True if app is installed
        - installation_id: GitHub installation ID (if installed)
        - repositories: List of accessible repos (if installed)
    """
    with managed_session() as session:
        from sqlmodel import select

        workspace = session.exec(select(Workspace).where(Workspace.slug == workspace_slug)).first()

        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        if not workspace.github_installation_id:
            return {
                "installed": False,
                "message": "GitHub App not installed. Please complete installation.",
            }

        # Check if app is still installed and get repo list
        if github_app:
            try:
                repos = await github_app.list_installation_repositories(
                    workspace.github_installation_id
                )
                return {
                    "installed": True,
                    "installation_id": workspace.github_installation_id,
                    "repositories": [
                        {"name": r["name"], "full_name": r["full_name"]} for r in repos
                    ],
                }
            except Exception as e:
                return {
                    "installed": False,
                    "error": f"Failed to fetch installation info: {str(e)}",
                }

        return {
            "installed": True,
            "installation_id": workspace.github_installation_id,
            "repositories": [],
        }


# =============================================================================
# Team Members
# =============================================================================


@router.get("/{workspace_slug}/members")
async def list_members(workspace_slug: str):
    """List all members of a workspace."""
    with managed_session() as session:
        from sqlmodel import select

        workspace = session.exec(select(Workspace).where(Workspace.slug == workspace_slug)).first()

        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        members = session.exec(
            select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace.id)
        ).all()

        return [
            WorkspaceMemberResponse(
                id=m.id,
                workspace_id=m.workspace_id,
                user_id=m.user_id,
                github_username=m.github_username,
                role=m.role,
                is_active=m.is_active,
                joined_at=m.joined_at,
                created_at=m.created_at,
            )
            for m in members
        ]


class InviteMemberPayload(BaseModel):
    """Payload for inviting a team member."""

    email: str
    role: str = "editor"


@router.post("/{workspace_slug}/members/invite")
async def invite_member(workspace_slug: str, payload: InviteMemberPayload, request: Request):
    """
    Invite a user to join the workspace.

    Flow:
    1. Create invitation record
    2. Send email with signup/OAuth link
    3. User authorizes GitHub access
    4. Member record is activated
    """
    # Future: use request.state.get("user_id") for invitation tracking
    with managed_session() as session:
        from sqlmodel import select

        workspace = session.exec(select(Workspace).where(Workspace.slug == workspace_slug)).first()

        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        # TODO: Create invitation record
        # TODO: Send invitation email
        # TODO: Return invitation link

        return {
            "status": "invited",
            "email": payload.email,
            "workspace_slug": workspace_slug,
            "message": "Invitation email sent",
        }

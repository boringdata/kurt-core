"""Workspace management commands for multi-tenant deployments."""

import click
from rich.console import Console
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command

console = Console()


@click.group()
def workspace():
    """Manage workspaces (multi-tenant cloud mode)."""
    pass


@workspace.command("list")
@track_command()
def list_workspaces():
    """List all workspaces you have access to."""
    from sqlmodel import select

    from kurt.db.base import get_database_client
    from kurt.db.models import Workspace

    client = get_database_client()

    # Check if in cloud mode
    from kurt.config import get_config_or_default

    config = get_config_or_default()

    if not config.DATABASE_URL:
        console.print("[yellow]⚠[/yellow] Workspaces are only available in cloud mode (PostgreSQL)")
        console.print("[dim]Set DATABASE_URL environment variable to use cloud mode[/dim]")
        return

    with client.get_session() as session:
        workspaces = session.exec(select(Workspace).where(Workspace.is_active)).all()

        if not workspaces:
            console.print("[yellow]No workspaces found[/yellow]")
            return

        # Create table
        table = Table(title="Workspaces")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Slug", style="blue")
        table.add_column("Plan", style="magenta")
        table.add_column("Owner", style="dim")

        for ws in workspaces:
            table.add_row(str(ws.id)[:8] + "...", ws.name, ws.slug, ws.plan, ws.owner_email or "-")

        console.print(table)
        console.print(f"\n[dim]Total: {len(workspaces)} workspace(s)[/dim]")


@workspace.command("create")
@click.argument("name")
@click.option("--slug", help="URL-friendly identifier (auto-generated if not provided)")
@click.option("--plan", default="free", type=click.Choice(["free", "pro", "enterprise"]))
@click.option("--owner-email", help="Owner email address")
@track_command()
def create_workspace(name: str, slug: str, plan: str, owner_email: str):
    """Create a new workspace."""
    import re

    from sqlmodel import select

    from kurt.db.base import get_database_client
    from kurt.db.models import Workspace

    client = get_database_client()

    # Check if in cloud mode
    from kurt.config import get_config_or_default

    config = get_config_or_default()

    if not config.DATABASE_URL:
        console.print("[yellow]⚠[/yellow] Workspaces are only available in cloud mode (PostgreSQL)")
        return

    # Auto-generate slug if not provided
    if not slug:
        slug = re.sub(r"[^a-z0-9-]", "-", name.lower())
        slug = re.sub(r"-+", "-", slug).strip("-")

    with client.get_session() as session:
        # Check if slug already exists
        existing = session.exec(select(Workspace).where(Workspace.slug == slug)).first()
        if existing:
            console.print(f"[red]✗[/red] Workspace with slug '{slug}' already exists")
            return

        # Create workspace
        workspace = Workspace(name=name, slug=slug, plan=plan, owner_email=owner_email)
        session.add(workspace)
        session.commit()
        session.refresh(workspace)

        console.print(f"[green]✓[/green] Created workspace: {name}")
        console.print(f"[dim]ID: {workspace.id}[/dim]")
        console.print(f"[dim]Slug: {workspace.slug}[/dim]")
        console.print(f"[dim]Plan: {workspace.plan}[/dim]")


@workspace.command("info")
@click.argument("workspace_id", required=False)
@track_command()
def workspace_info(workspace_id: str):
    """Show detailed workspace information.

    If no workspace_id is provided, shows current workspace (from WORKSPACE_ID env var).
    """
    from uuid import UUID

    from sqlmodel import select

    from kurt.db.base import get_database_client
    from kurt.db.models import Workspace

    client = get_database_client()

    # Check if in cloud mode
    from kurt.config import get_config_or_default

    config = get_config_or_default()

    if not config.DATABASE_URL:
        console.print("[yellow]⚠[/yellow] Workspaces are only available in cloud mode (PostgreSQL)")
        return

    # Use WORKSPACE_ID from config if not provided
    if not workspace_id:
        workspace_id = config.WORKSPACE_ID
        if not workspace_id:
            console.print("[red]✗[/red] No workspace specified and WORKSPACE_ID not set")
            return

    with client.get_session() as session:
        workspace = session.exec(
            select(Workspace).where(Workspace.id == UUID(workspace_id))
        ).first()

        if not workspace:
            console.print(f"[red]✗[/red] Workspace not found: {workspace_id}")
            return

        # Display workspace info
        console.print(f"\n[bold]{workspace.name}[/bold]")
        console.print(f"[dim]{'─' * 50}[/dim]")
        console.print(f"ID:           {workspace.id}")
        console.print(f"Slug:         {workspace.slug}")
        console.print(f"Plan:         {workspace.plan}")
        console.print(f"Owner:        {workspace.owner_email or '-'}")
        console.print(f"Organization: {workspace.organization or '-'}")
        console.print(f"Active:       {'Yes' if workspace.is_active else 'No'}")
        console.print(f"Created:      {workspace.created_at}")
        console.print(f"Updated:      {workspace.updated_at}")

        if workspace.max_documents:
            console.print(f"Max Documents: {workspace.max_documents}")
        if workspace.max_users:
            console.print(f"Max Users:     {workspace.max_users}")


@workspace.command("add-user")
@click.argument("email")
@click.option("--workspace-id", help="Workspace ID (defaults to WORKSPACE_ID env var)")
@click.option("--role", type=click.Choice(["owner", "admin", "member", "viewer"]), default="member")
@track_command()
def add_user(email: str, workspace_id: str, role: str):
    """Add a user to a workspace with specified role.

    Roles:
    - owner: Full control over workspace
    - admin: Can manage users and content
    - member: Can view and edit content
    - viewer: Read-only access
    """
    from uuid import UUID

    from sqlmodel import select

    from kurt.db.base import get_database_client
    from kurt.db.models import Workspace, WorkspaceMember, WorkspaceRole

    client = get_database_client()

    from kurt.config import get_config_or_default

    config = get_config_or_default()

    if not config.DATABASE_URL:
        console.print("[yellow]⚠[/yellow] User management is only available in cloud mode")
        return

    if not workspace_id:
        workspace_id = config.WORKSPACE_ID
        if not workspace_id:
            console.print("[red]✗[/red] No workspace specified")
            return

    with client.get_session() as session:
        workspace = session.exec(
            select(Workspace).where(Workspace.id == UUID(workspace_id))
        ).first()

        if not workspace:
            console.print("[red]✗[/red] Workspace not found")
            return

        existing = session.exec(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == UUID(workspace_id),
                WorkspaceMember.user_email == email,
            )
        ).first()

        if existing:
            console.print(f"[yellow]⚠[/yellow] User already exists (role: {existing.role})")
            return

        member = WorkspaceMember(
            workspace_id=UUID(workspace_id), user_email=email, role=WorkspaceRole(role)
        )
        session.add(member)
        session.commit()

        console.print(f"[green]✓[/green] Added {email} with role: {role}")


@workspace.command("list-users")
@click.option("--workspace-id", help="Workspace ID (defaults to WORKSPACE_ID env var)")
@track_command()
def list_users(workspace_id: str):
    """List all users in a workspace."""
    from uuid import UUID

    from sqlmodel import select

    from kurt.db.base import get_database_client
    from kurt.db.models import Workspace, WorkspaceMember

    client = get_database_client()

    from kurt.config import get_config_or_default

    config = get_config_or_default()

    if not config.DATABASE_URL:
        console.print("[yellow]⚠[/yellow] User management is only available in cloud mode")
        return

    if not workspace_id:
        workspace_id = config.WORKSPACE_ID
        if not workspace_id:
            console.print("[red]✗[/red] No workspace specified")
            return

    with client.get_session() as session:
        workspace = session.exec(
            select(Workspace).where(Workspace.id == UUID(workspace_id))
        ).first()

        if not workspace:
            console.print("[red]✗[/red] Workspace not found")
            return

        members = session.exec(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == UUID(workspace_id),
                WorkspaceMember.is_active,
            )
        ).all()

        if not members:
            console.print("[yellow]No users found[/yellow]")
            return

        table = Table(title=f"Users in '{workspace.name}'")
        table.add_column("Email", style="cyan")
        table.add_column("Role", style="green")
        table.add_column("Status", style="blue")

        for member in members:
            status = "Active" if member.joined_at else "Pending"
            table.add_row(member.user_email, member.role.value, status)

        console.print(table)
        console.print(f"\n[dim]Total: {len(members)} user(s)[/dim]")

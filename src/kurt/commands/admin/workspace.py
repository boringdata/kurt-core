"""Kurt CLI - Workspace management commands."""

import click
from rich.console import Console
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command
from kurt.config import get_config_or_default, load_config, update_config
from kurt.db.database import get_database_client

console = Console()


@click.group()
def workspace():
    """Workspace management for multi-tenant PostgreSQL setups."""
    pass


@workspace.command()
@track_command
def current():
    """
    Show current workspace configuration.

    Example:
        kurt admin workspace current
    """
    config = get_config_or_default()

    console.print("\n[bold]Current Workspace Configuration[/bold]\n")

    table = Table(show_header=False)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    if config.DATABASE_URL:
        # Mask password
        masked_url = _mask_password(config.DATABASE_URL)
        table.add_row("Database Type", "PostgreSQL")
        table.add_row("Connection", masked_url)

        if config.WORKSPACE_ID:
            table.add_row("Workspace ID", config.WORKSPACE_ID)
        else:
            table.add_row("Workspace ID", "[dim](not set)[/dim]")
    else:
        table.add_row("Database Type", "SQLite (local)")
        table.add_row("Database Path", config.PATH_DB)
        table.add_row("Workspace ID", "[dim](not applicable)[/dim]")

    console.print(table)

    # Show database connection status
    console.print()
    db = get_database_client()

    if db.check_database_exists():
        console.print(f"[green]✓[/green] Connected to database ({db.get_mode_name()} mode)")
    else:
        console.print("[red]✗[/red] Cannot connect to database")


@workspace.command()
@click.argument("workspace_id")
@track_command
def set(workspace_id: str):
    """
    Set active workspace ID.

    This updates the WORKSPACE_ID in kurt.config to filter queries
    by workspace in multi-tenant PostgreSQL setups.

    Example:
        kurt admin workspace set workspace-uuid-123
    """
    config = load_config()

    if not config.DATABASE_URL:
        console.print("[yellow]Warning: Not using PostgreSQL.[/yellow]")
        console.print(
            "[dim]Workspace ID is only relevant for PostgreSQL multi-tenant setups.[/dim]"
        )

    config.WORKSPACE_ID = workspace_id
    update_config(config)

    console.print(f"[green]✓[/green] Set workspace ID: [cyan]{workspace_id}[/cyan]")


@workspace.command()
@track_command
def unset():
    """
    Remove workspace ID from configuration.

    This removes the WORKSPACE_ID from kurt.config, allowing access
    to all workspaces (requires appropriate database permissions).

    Example:
        kurt admin workspace unset
    """
    config = load_config()
    config.WORKSPACE_ID = None
    update_config(config)

    console.print("[green]✓[/green] Removed workspace ID")
    console.print("[dim]You now have access to all workspaces (if permitted by database)[/dim]")


@workspace.command()
@click.option("--limit", default=10, help="Maximum workspaces to show")
@track_command
def list(limit: int):
    """
    List available workspaces.

    Queries the database for workspace information.
    Requires PostgreSQL with a 'workspaces' or 'tenants' table.

    Example:
        kurt admin workspace list
        kurt admin workspace list --limit 20
    """
    config = get_config_or_default()

    if not config.DATABASE_URL:
        console.print("[yellow]Workspace listing is only available for PostgreSQL.[/yellow]")
        console.print("[dim]You are using SQLite (local mode).[/dim]")
        return

    db = get_database_client()
    session = db.get_session()

    try:
        from sqlmodel import text

        # Try to query workspaces/tenants table
        # This assumes the table exists - adjust query based on your schema
        result = session.exec(
            text(
                f"""
            SELECT id, name, created_at
            FROM tenants
            ORDER BY created_at DESC
            LIMIT {limit}
            """
            )
        )

        workspaces = list(result)

        if not workspaces:
            console.print("[dim]No workspaces found.[/dim]")
            return

        console.print(f"\n[bold]Available Workspaces[/bold] (showing {len(workspaces)})\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan")
        table.add_column("Name")
        table.add_column("Created", style="dim")

        for workspace in workspaces:
            ws_id, ws_name, ws_created = workspace
            created_str = ws_created.strftime("%Y-%m-%d") if ws_created else "—"
            table.add_row(str(ws_id), ws_name, created_str)

        console.print(table)

        console.print("\n[dim]To switch workspace: kurt admin workspace set <workspace-id>[/dim]")

    except Exception as e:
        console.print(f"[red]Error querying workspaces: {e}[/red]")
        console.print("[dim]Make sure your database has a 'tenants' table.[/dim]")
    finally:
        session.close()


@workspace.command()
@click.argument("workspace_name")
@click.option("--set-active", is_flag=True, help="Set as active workspace after creation")
@track_command
def create(workspace_name: str, set_active: bool):
    """
    Create a new workspace.

    Creates a new workspace/tenant in the PostgreSQL database.
    Requires appropriate database permissions.

    Example:
        kurt admin workspace create "My Team Workspace"
        kurt admin workspace create "Acme Corp" --set-active
    """
    config = get_config_or_default()

    if not config.DATABASE_URL:
        console.print("[yellow]Workspace creation is only available for PostgreSQL.[/yellow]")
        console.print("[dim]You are using SQLite (local mode).[/dim]")
        return

    db = get_database_client()
    session = db.get_session()

    try:
        from uuid import uuid4

        from sqlmodel import text

        # Generate workspace ID
        workspace_id = str(uuid4())
        workspace_slug = workspace_name.lower().replace(" ", "-")

        # Insert workspace
        session.exec(
            text(
                """
            INSERT INTO tenants (id, name, slug, plan_type, created_at)
            VALUES (:id, :name, :slug, 'free', NOW())
            """
            ),
            {"id": workspace_id, "name": workspace_name, "slug": workspace_slug},
        )
        session.commit()

        console.print(f"[green]✓[/green] Created workspace: [cyan]{workspace_name}[/cyan]")
        console.print(f"[dim]Workspace ID: {workspace_id}[/dim]")

        if set_active:
            config.WORKSPACE_ID = workspace_id
            update_config(config)
            console.print("[green]✓[/green] Set as active workspace")

    except Exception as e:
        console.print(f"[red]Error creating workspace: {e}[/red]")
        session.rollback()
    finally:
        session.close()


def _mask_password(url: str) -> str:
    """Mask password in connection string for display."""
    try:
        if "://" in url and "@" in url:
            protocol, rest = url.split("://", 1)
            if ":" in rest and "@" in rest:
                user_part, host_part = rest.split("@", 1)
                user, _ = user_part.split(":", 1)
                return f"{protocol}://{user}:***@{host_part}"
    except Exception:
        pass
    return url

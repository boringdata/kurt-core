"""Database migration commands."""

from __future__ import annotations

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command

console = Console()


def _check_not_cloud_mode():
    """Check that we're not in cloud mode - migrations are admin-only there."""
    from kurt.db import is_cloud_mode

    if is_cloud_mode():
        console.print("[red]Error: Migrations are not allowed in cloud mode[/red]")
        console.print()
        console.print("[dim]Kurt Cloud manages database schema automatically.[/dim]")
        console.print("[dim]Contact support if you need schema changes.[/dim]")
        raise click.Abort()


@click.group()
def migrate():
    """Database schema migration commands."""
    pass


@migrate.command()
@click.option("--auto-confirm", "-y", is_flag=True, help="Skip confirmation prompt")
@track_command
def apply(auto_confirm: bool):
    """
    Apply pending database migrations.

    Creates a backup and applies all pending schema migrations.
    Not available in cloud mode (schema managed by Kurt Cloud).

    Example:
        kurt admin migrate apply
        kurt admin migrate apply -y
    """
    _check_not_cloud_mode()

    from kurt.db.migrations.utils import apply_migrations

    result = apply_migrations(auto_confirm=auto_confirm)

    if result["success"]:
        if result.get("applied"):
            console.print(f"[green]Applied {result['count']} migration(s)[/green]")
        else:
            console.print("[green]No migrations to apply[/green]")
    else:
        console.print(f"[red]Migration failed: {result.get('error')}[/red]")
        raise click.Abort()


@migrate.command()
@track_command
def status():
    """
    Show current database migration status.

    Displays current schema version and pending migrations.

    Example:
        kurt admin migrate status
    """
    from kurt.db.migrations.utils import show_migration_status

    show_migration_status()


@migrate.command()
@track_command
def init():
    """
    Initialize Alembic for an existing database.

    Use this when you have an existing database that was created
    before migrations were added.
    Not available in cloud mode (schema managed by Kurt Cloud).

    Example:
        kurt admin migrate init
    """
    _check_not_cloud_mode()

    from kurt.db.migrations.utils import initialize_alembic

    initialize_alembic()

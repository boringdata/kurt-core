"""Database migration commands."""

from __future__ import annotations

import click
from rich.console import Console

console = Console()


@click.group()
def migrate():
    """Database schema migration commands."""
    pass


@migrate.command()
@click.option("--auto-confirm", "-y", is_flag=True, help="Skip confirmation prompt")
def apply(auto_confirm: bool):
    """
    Apply pending database migrations.

    Creates a backup and applies all pending schema migrations.

    Example:
        kurt admin migrate apply
        kurt admin migrate apply -y
    """
    from kurt_new.db.migrations.utils import apply_migrations

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
def status():
    """
    Show current database migration status.

    Displays current schema version and pending migrations.

    Example:
        kurt admin migrate status
    """
    from kurt_new.db.migrations.utils import show_migration_status

    show_migration_status()


@migrate.command()
def init():
    """
    Initialize Alembic for an existing database.

    Use this when you have an existing database that was created
    before migrations were added.

    Example:
        kurt admin migrate init
    """
    from kurt_new.db.migrations.utils import initialize_alembic

    initialize_alembic()

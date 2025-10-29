"""Kurt CLI - Database migration commands."""

import click
from rich.console import Console

from kurt.db.migrations.utils import apply_migrations, show_migration_status

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

    This command will:
    - Create a backup of your database
    - Apply all pending schema migrations
    - Update the schema version in kurt.config

    Example:
        kurt migrate apply
        kurt migrate apply --auto-confirm
    """
    apply_migrations(auto_confirm=auto_confirm)


@migrate.command()
def status():
    """
    Show current database migration status.

    Displays:
    - Current schema version
    - Pending migrations (if any)
    - Applied migration history

    Example:
        kurt migrate status
    """
    show_migration_status()

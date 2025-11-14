"""Kurt CLI - Database migration commands."""

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command
from kurt.db.migrations.utils import apply_migrations, show_migration_status

console = Console()


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
@track_command
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


@migrate.command()
@track_command
def init():
    """
    Initialize Alembic for an existing database.

    Use this command when you have an existing database that was created
    before migrations were added. This will mark the database as being
    at the current schema version without running migrations.

    Example:
        kurt migrate init
    """
    from kurt.db.migrations.utils import initialize_alembic

    initialize_alembic()

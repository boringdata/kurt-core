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


@migrate.command("migrate-db")
@click.option("--target-url", required=True, help="Target PostgreSQL connection string")
@click.option("--workspace-id", help="Workspace ID for multi-tenant setup")
@click.option("--auto-confirm", "-y", is_flag=True, help="Skip confirmation prompts")
@track_command
def migrate_db(target_url: str, workspace_id: str, auto_confirm: bool):
    """
    Migrate local SQLite database to PostgreSQL (e.g., Supabase).

    This command will:
    - Copy all documents, entities, and relationships from SQLite to PostgreSQL
    - Preserve UUIDs and timestamps
    - Content files stay local (only metadata is migrated)
    - Update kurt.config to point to PostgreSQL

    Example:
        kurt admin migrate migrate-db \\
            --target-url "postgresql://user:pass@db.supabase.co:5432/postgres" \\
            --workspace-id "workspace-uuid"
    """
    from kurt.db.migrate_to_postgres import migrate_sqlite_to_postgres

    migrate_sqlite_to_postgres(
        target_url=target_url,
        workspace_id=workspace_id,
        auto_confirm=auto_confirm,
    )

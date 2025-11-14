"""Migration utilities with Rich UI for Kurt database management."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from alembic import command
from alembic.config import Config as AlembicConfig
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.table import Table
from sqlalchemy import create_engine

from kurt import __version__
from kurt.config import load_config

console = Console()


def get_alembic_config() -> AlembicConfig:
    """Get Alembic configuration object."""
    # Get path to alembic.ini relative to this file
    migrations_dir = Path(__file__).parent
    ini_path = migrations_dir / "alembic.ini"

    if not ini_path.exists():
        raise FileNotFoundError(f"Alembic configuration not found: {ini_path}")

    config = AlembicConfig(str(ini_path))
    config.set_main_option("script_location", str(migrations_dir))
    return config


def get_database_engine():
    """Get SQLAlchemy engine for the current project's database."""
    kurt_config = load_config()
    db_path = kurt_config.get_absolute_db_path()
    db_url = f"sqlite:///{db_path}"
    return create_engine(db_url)


def get_current_version() -> Optional[str]:
    """
    Get the current database schema version (from alembic_version table).

    Returns:
        Current revision ID or None if database is not initialized
    """
    try:
        engine = get_database_engine()
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            return context.get_current_revision()
    except Exception:
        # Database might not exist or alembic_version table not created yet
        return None


def get_pending_migrations() -> List[Tuple[str, str]]:
    """
    Get list of pending migrations.

    Returns:
        List of tuples: (revision_id, description)
    """
    config = get_alembic_config()
    script = ScriptDirectory.from_config(config)

    current_rev = get_current_version()

    # Get all revisions from current to head
    pending = []

    if current_rev is None:
        # No migrations applied yet - get all migrations from base to head
        for rev in script.walk_revisions(base="base", head="heads"):
            pending.append((rev.revision, rev.doc or "No description"))
    else:
        # Get migrations between current and head
        try:
            for rev in script.iterate_revisions(current_rev, "heads"):
                if rev.revision != current_rev:
                    pending.append((rev.revision, rev.doc or "No description"))
        except Exception:
            # If iterate_revisions fails, fall back to walking all revisions
            # and filtering out the current one
            for rev in script.walk_revisions(base="base", head="heads"):
                if rev.revision != current_rev:
                    pending.append((rev.revision, rev.doc or "No description"))

    # Reverse to show in chronological order
    return list(reversed(pending))


def get_migration_history() -> List[Tuple[str, str, Optional[str]]]:
    """
    Get migration history from the database.

    Returns:
        List of tuples: (revision_id, description, applied_at)
    """
    config = get_alembic_config()
    script = ScriptDirectory.from_config(config)

    current_rev = get_current_version()
    if not current_rev:
        return []

    history = []
    # Walk all revisions and collect those up to current_rev
    for rev in script.walk_revisions(base="base", head="heads"):
        if rev.revision:
            # We don't track applied_at in standard Alembic, so it's None
            # You could add a custom table to track this if needed
            history.append((rev.revision, rev.doc or "No description", None))
            # Stop when we reach the current revision
            if rev.revision == current_rev:
                break

    return list(reversed(history))


def backup_database() -> Optional[Path]:
    """
    Create a timestamped backup of the database before migration.

    Returns:
        Path to backup file or None if backup failed
    """
    try:
        kurt_config = load_config()
        db_path = kurt_config.get_absolute_db_path()

        if not db_path.exists():
            console.print("[yellow]No database to backup[/yellow]")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = db_path.parent / f"kurt.sqlite.backup.{timestamp}"

        console.print(f"[dim]Creating backup: {backup_path.name}[/dim]")
        shutil.copy2(db_path, backup_path)

        return backup_path

    except Exception as e:
        console.print(f"[red]Backup failed: {e}[/red]")
        return None


def check_migrations_needed() -> bool:
    """
    Check if database migrations are needed.

    Returns:
        True if migrations are pending, False otherwise
    """
    pending = get_pending_migrations()
    return len(pending) > 0


def display_migration_prompt(pending: List[Tuple[str, str]]) -> bool:
    """
    Display Rich UI for pending migrations and ask for confirmation.

    Args:
        pending: List of pending migrations (revision_id, description)

    Returns:
        True if user confirms migration, False otherwise
    """
    console.print()
    console.print(
        Panel.fit("[yellow]⚠  Database Migration Required[/yellow]", border_style="yellow")
    )
    console.print()

    # Show version info
    current_version = get_current_version() or "none"
    console.print(f"[dim]Current schema version:[/dim] {current_version}")
    console.print(f"[dim]Kurt CLI version:[/dim] {__version__}")
    console.print()

    # Show pending migrations table
    table = Table(title="Pending Migrations", show_header=True, header_style="bold cyan")
    table.add_column("Revision", style="cyan", width=12)
    table.add_column("Description", style="white", width=50)
    table.add_column("Status", justify="center", width=10)

    for revision, description in pending:
        # Truncate long descriptions
        if len(description) > 50:
            description = description[:47] + "..."
        table.add_row(revision[:8], description, "⏳ Pending")

    console.print(table)
    console.print()

    # Show what will happen
    console.print("[dim]This migration will:[/dim]")
    console.print("  • Create automatic backup: [cyan].kurt/kurt.sqlite.backup.TIMESTAMP[/cyan]")
    console.print(f"  • Apply {len(pending)} schema change(s)")
    console.print("  • Preserve all existing data")
    console.print()

    # Ask for confirmation
    return Confirm.ask("[bold]Apply migrations now?[/bold]", default=True)


def apply_migrations(auto_confirm: bool = False) -> bool:
    """
    Apply all pending database migrations with Rich progress UI.

    Args:
        auto_confirm: If True, skip confirmation prompt

    Returns:
        True if migrations were applied successfully, False otherwise
    """
    pending = get_pending_migrations()

    if not pending:
        console.print("[green]✓ Database is up to date[/green]")
        return True

    # Show prompt unless auto-confirm is enabled
    if not auto_confirm:
        if not display_migration_prompt(pending):
            console.print()
            console.print("[yellow]⚠ Migration skipped[/yellow]")
            console.print("[dim]Note: Some features may not work without the latest schema[/dim]")
            console.print()
            return False

    console.print()

    try:
        # Create backup with progress
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            backup_task = progress.add_task("[cyan]Creating backup...", total=None)
            backup_path = backup_database()
            progress.update(backup_task, completed=True)

        # Apply migrations with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("[yellow]Applying migrations...", total=len(pending))

            config = get_alembic_config()

            for idx, (revision, description) in enumerate(pending, 1):
                short_desc = description[:30] + "..." if len(description) > 30 else description
                progress.update(
                    task,
                    description=f"[yellow]Applying {idx}/{len(pending)}: {short_desc}[/yellow]",
                )

                # Apply single migration step by step
                command.upgrade(config, "+1")
                progress.update(task, advance=1)

        # Get current version for success message
        current_version = get_current_version()

        # Success message
        console.print()
        backup_info = f"[dim]Backup saved:[/dim] {backup_path.name}" if backup_path else ""
        console.print(
            Panel.fit(
                f"[bold green]✅ Database migrated successfully![/bold green]\n"
                f"[dim]Schema version:[/dim] {current_version or 'unknown'}\n"
                f"{backup_info}",
                border_style="green",
            )
        )
        console.print()

        return True

    except Exception as e:
        console.print()
        console.print(
            Panel.fit(
                f"[bold red]❌ Migration failed![/bold red]\n" f"[dim]Error:[/dim] {str(e)}",
                border_style="red",
            )
        )
        console.print()
        console.print(
            "[yellow]Your database has been backed up. " "You can restore it if needed.[/yellow]"
        )
        return False


def show_migration_status() -> None:
    """Display current migration status with Rich UI."""
    console.print()
    console.print("[bold]Migration Status[/bold]\n")

    # Database info
    kurt_config = load_config()
    db_path = kurt_config.get_absolute_db_path()
    console.print(f"[dim]Database:[/dim] {db_path}")

    current_version = get_current_version()
    console.print(f"[dim]Schema version:[/dim] {current_version or 'not initialized'}")
    console.print(f"[dim]Kurt CLI version:[/dim] {__version__}")
    console.print()

    # Check for pending migrations
    pending = get_pending_migrations()

    if pending:
        console.print("[yellow]⚠ Pending migrations detected[/yellow]\n")

        table = Table(title="Pending Migrations", show_header=True, header_style="bold yellow")
        table.add_column("Revision", style="cyan", width=12)
        table.add_column("Description", style="white", width=50)

        for revision, description in pending:
            table.add_row(revision[:8], description)

        console.print(table)
        console.print()
        console.print("[dim]Run [cyan]kurt admin migrate apply[/cyan] to apply migrations[/dim]")

    else:
        # Show applied migrations
        history = get_migration_history()

        if history:
            table = Table(title="Applied Migrations", show_header=True, header_style="bold green")
            table.add_column("Revision", style="cyan", width=12)
            table.add_column("Description", style="white", width=50)

            for revision, description, _ in history:
                table.add_row(revision[:8], description)

            console.print(table)
            console.print()

        console.print("[green]✓ Database is up to date[/green]")

    console.print()


def initialize_alembic() -> None:
    """Initialize Alembic for an existing database (stamp it as current)."""
    try:
        config = get_alembic_config()
        # Stamp the database with the current head revision
        command.stamp(config, "head")

        current_version = get_current_version()
        console.print(
            f"[green]✓ Database initialized with schema version: {current_version}[/green]"
        )

    except Exception as e:
        console.print(f"[red]Failed to initialize migrations: {e}[/red]")
        raise

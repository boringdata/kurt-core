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


@migrate.command("migrate-content")
@click.option("--to-workspace", required=True, help="Target workspace ID to migrate content to")
@click.option(
    "--from-workspace", help="Source workspace ID (default: 00000000-0000-0000-0000-000000000000)"
)
@click.option("--dry-run", is_flag=True, help="Show what would be migrated without making changes")
@click.option("--auto-confirm", "-y", is_flag=True, help="Skip confirmation prompt")
@track_command
def migrate_content(to_workspace: str, from_workspace: str, dry_run: bool, auto_confirm: bool):
    """
    Migrate content from one workspace to another.

    This command migrates all documents, entities, and relationships from
    one workspace (tenant) to another. Useful for:
    - Migrating local content to cloud workspace
    - Moving content between workspaces
    - Consolidating workspaces

    Example:
        # Migrate from local to cloud workspace
        kurt admin migrate migrate-content --to-workspace <workspace-id>

        # Dry run to see what would be migrated
        kurt admin migrate migrate-content --to-workspace <id> --dry-run
    """
    from uuid import UUID

    from rich.prompt import Confirm
    from sqlmodel import select

    from kurt.db.base import get_database_client
    from kurt.db.models import Document, DocumentEntity, Entity, EntityRelationship

    # Default from_workspace is local mode workspace
    if not from_workspace:
        from_workspace = "00000000-0000-0000-0000-000000000000"

    try:
        from_ws_id = UUID(from_workspace)
        to_ws_id = UUID(to_workspace)
    except ValueError as e:
        console.print(f"[red]✗[/red] Invalid workspace ID: {e}")
        return

    client = get_database_client()

    with client.get_session() as session:
        # Count items to migrate
        documents = session.exec(select(Document).where(Document.tenant_id == from_ws_id)).all()
        entities = session.exec(select(Entity).where(Entity.tenant_id == from_ws_id)).all()
        relationships = session.exec(
            select(EntityRelationship).where(EntityRelationship.tenant_id == from_ws_id)
        ).all()
        doc_entities = session.exec(
            select(DocumentEntity).where(DocumentEntity.tenant_id == from_ws_id)
        ).all()

        console.print("\n[bold]Content Migration Plan[/bold]")
        console.print(f"[dim]{'─' * 50}[/dim]")
        console.print(f"From workspace: {from_workspace}")
        console.print(f"To workspace:   {to_workspace}")
        console.print("\n[bold]Items to migrate:[/bold]")
        console.print(f"  • Documents:            {len(documents)}")
        console.print(f"  • Entities:             {len(entities)}")
        console.print(f"  • Entity Relationships: {len(relationships)}")
        console.print(f"  • Document-Entity Links: {len(doc_entities)}")

        if dry_run:
            console.print("\n[yellow]⚠[/yellow] Dry run mode - no changes will be made")
            return

        if not auto_confirm:
            if not Confirm.ask("\n[bold]Proceed with migration?[/bold]", default=False):
                console.print("[yellow]Migration cancelled[/yellow]")
                return

        # Perform migration
        console.print("\n[cyan]Starting migration...[/cyan]")

        updated = 0

        # Update documents
        for doc in documents:
            doc.tenant_id = to_ws_id
            session.add(doc)
            updated += 1
        console.print(f"[green]✓[/green] Migrated {len(documents)} documents")

        # Update entities
        for entity in entities:
            entity.tenant_id = to_ws_id
            session.add(entity)
            updated += 1
        console.print(f"[green]✓[/green] Migrated {len(entities)} entities")

        # Update relationships
        for rel in relationships:
            rel.tenant_id = to_ws_id
            session.add(rel)
            updated += 1
        console.print(f"[green]✓[/green] Migrated {len(relationships)} relationships")

        # Update document-entity links
        for de in doc_entities:
            de.tenant_id = to_ws_id
            session.add(de)
            updated += 1
        console.print(f"[green]✓[/green] Migrated {len(doc_entities)} document-entity links")

        session.commit()

        console.print("\n[green]✓[/green] Migration complete!")
        console.print(f"[dim]Total items updated: {updated}[/dim]")

"""Migrate SQLite database to PostgreSQL (e.g., Supabase)."""

import logging
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.table import Table
from sqlmodel import select

from kurt.config import load_config, update_config
from kurt.db.models import (
    Document,
    DocumentClusterEdge,
    DocumentEntity,
    DocumentLink,
    Entity,
    EntityRelationship,
    TopicCluster,
)
from kurt.db.postgresql import PostgreSQLClient
from kurt.db.sqlite import SQLiteClient

console = Console()
logger = logging.getLogger(__name__)


def migrate_sqlite_to_postgres(
    target_url: str,
    workspace_id: Optional[str] = None,
    auto_confirm: bool = False,
):
    """
    Migrate local SQLite database to PostgreSQL.

    Args:
        target_url: PostgreSQL connection string
        workspace_id: Workspace/tenant ID for multi-tenant setup
        auto_confirm: Skip confirmation prompts
    """
    console.print("\n[bold]Kurt Database Migration: SQLite → PostgreSQL[/bold]\n")

    # 1. Check source database
    console.print("[dim]Checking source database...[/dim]")
    sqlite_client = SQLiteClient()

    if not sqlite_client.check_database_exists():
        console.print("[red]Error: SQLite database not found.[/red]")
        console.print("[dim]Run 'kurt init' to create a database first.[/dim]")
        return

    sqlite_session = sqlite_client.get_session()

    # Get counts
    doc_count = sqlite_session.exec(select(Document)).all()
    entity_count = sqlite_session.exec(select(Entity)).all()
    cluster_count = sqlite_session.exec(select(TopicCluster)).all()

    console.print("[green]✓[/green] Found local database:")
    console.print(f"  • Documents: {len(doc_count)}")
    console.print(f"  • Entities: {len(entity_count)}")
    console.print(f"  • Topic Clusters: {len(cluster_count)}")

    # 2. Check target database
    console.print("\n[dim]Connecting to PostgreSQL...[/dim]")
    console.print(f"[dim]Target: {_mask_password(target_url)}[/dim]")

    try:
        postgres_client = PostgreSQLClient(database_url=target_url, workspace_id=workspace_id)

        if not postgres_client.check_database_exists():
            console.print("[red]Error: Cannot connect to PostgreSQL database.[/red]")
            console.print("[dim]Check your connection string and network access.[/dim]")
            return

        console.print("[green]✓[/green] Connected to PostgreSQL")

        # Check if schema exists
        postgres_session = postgres_client.get_session()

        # Try to query documents table
        try:
            existing_docs = postgres_session.exec(select(Document)).all()
            console.print(
                f"[yellow]⚠[/yellow] Target database already has {len(existing_docs)} documents"
            )

            if not auto_confirm:
                if not Confirm.ask(
                    "[yellow]Target database is not empty. Continue anyway?[/yellow]",
                    default=False,
                ):
                    console.print("[dim]Migration cancelled[/dim]")
                    return
        except Exception:
            # Table doesn't exist yet - that's fine
            console.print("[dim]Target database is empty (schema will be created)[/dim]")

    except Exception as e:
        console.print(f"[red]Error connecting to PostgreSQL: {e}[/red]")
        return

    # 3. Confirm migration
    if not auto_confirm:
        console.print("\n[bold]Migration Plan:[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Step", style="dim")
        table.add_column("Action")

        table.add_row("1", "Create schema in PostgreSQL (if needed)")
        table.add_row("2", f"Copy {len(doc_count)} documents")
        table.add_row("3", f"Copy {len(entity_count)} entities")
        table.add_row("4", "Copy relationships and clusters")
        table.add_row("5", "Update kurt.config to use PostgreSQL")

        console.print(table)

        console.print(
            "\n[yellow]Note: Content files stay local (only metadata is migrated)[/yellow]"
        )

        if not Confirm.ask("\n[bold]Proceed with migration?[/bold]", default=True):
            console.print("[dim]Migration cancelled[/dim]")
            return

    # 4. Run migration
    console.print("\n[bold]Starting migration...[/bold]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Step 1: Create schema
        task1 = progress.add_task("Creating PostgreSQL schema...", total=None)
        try:
            postgres_client.init_database()
            progress.update(task1, completed=1, total=1)
        except Exception as e:
            console.print(f"[red]Error creating schema: {e}[/red]")
            return

        # Step 2: Migrate documents
        task2 = progress.add_task(f"Migrating {len(doc_count)} documents...", total=len(doc_count))
        migrated_docs = 0
        skipped_docs = 0

        for doc in doc_count:
            try:
                # Check if document already exists (by source_url)
                existing = None
                if doc.source_url:
                    existing = postgres_session.exec(
                        select(Document).where(Document.source_url == doc.source_url)
                    ).first()

                if existing:
                    skipped_docs += 1
                else:
                    # Create new document with workspace_id
                    new_doc = Document(
                        id=doc.id,
                        tenant_id=workspace_id,  # Add workspace context
                        title=doc.title,
                        source_type=doc.source_type,
                        source_url=doc.source_url,
                        content_path=doc.content_path,
                        content_hash=doc.content_hash,
                        description=doc.description,
                        author=doc.author,
                        published_date=doc.published_date,
                        ingestion_status=doc.ingestion_status,
                        content_type=doc.content_type,
                        has_code_examples=doc.has_code_examples,
                        has_step_by_step_procedures=doc.has_step_by_step_procedures,
                        has_narrative_structure=doc.has_narrative_structure,
                        indexed_with_hash=doc.indexed_with_hash,
                        indexed_with_git_commit=doc.indexed_with_git_commit,
                        embedding=doc.embedding,
                        created_at=doc.created_at,
                        updated_at=doc.updated_at,
                    )
                    postgres_session.add(new_doc)
                    migrated_docs += 1

                progress.update(task2, advance=1)
            except Exception as e:
                logger.error(f"Error migrating document {doc.id}: {e}")
                progress.update(task2, advance=1)

        postgres_session.commit()

        # Step 3: Migrate entities
        task3 = progress.add_task(
            f"Migrating {len(entity_count)} entities...", total=len(entity_count)
        )
        migrated_entities = 0

        for entity in entity_count:
            try:
                # Check if entity exists
                existing = postgres_session.exec(
                    select(Entity)
                    .where(Entity.name == entity.name)
                    .where(Entity.entity_type == entity.entity_type)
                ).first()

                if not existing:
                    new_entity = Entity(
                        id=entity.id,
                        tenant_id=workspace_id,
                        name=entity.name,
                        entity_type=entity.entity_type,
                        canonical_name=entity.canonical_name,
                        aliases=entity.aliases,
                        description=entity.description,
                        embedding=entity.embedding,
                        confidence_score=entity.confidence_score,
                        source_mentions=entity.source_mentions,
                        created_at=entity.created_at,
                        updated_at=entity.updated_at,
                    )
                    postgres_session.add(new_entity)
                    migrated_entities += 1

                progress.update(task3, advance=1)
            except Exception as e:
                logger.error(f"Error migrating entity {entity.id}: {e}")
                progress.update(task3, advance=1)

        postgres_session.commit()

        # Step 4: Migrate relationships and clusters
        task4 = progress.add_task("Migrating relationships...", total=None)

        # Entity relationships
        relationships = sqlite_session.exec(select(EntityRelationship)).all()
        for rel in relationships:
            new_rel = EntityRelationship(
                id=rel.id,
                source_entity_id=rel.source_entity_id,
                target_entity_id=rel.target_entity_id,
                relationship_type=rel.relationship_type,
                confidence=rel.confidence,
                evidence_count=rel.evidence_count,
                context=rel.context,
                created_at=rel.created_at,
                updated_at=rel.updated_at,
            )
            postgres_session.merge(new_rel)

        # Document entities
        doc_entities = sqlite_session.exec(select(DocumentEntity)).all()
        for de in doc_entities:
            new_de = DocumentEntity(
                id=de.id,
                document_id=de.document_id,
                entity_id=de.entity_id,
                mention_count=de.mention_count,
                confidence=de.confidence,
                context=de.context,
                created_at=de.created_at,
                updated_at=de.updated_at,
            )
            postgres_session.merge(new_de)

        # Topic clusters
        for cluster in cluster_count:
            new_cluster = TopicCluster(
                id=cluster.id,
                name=cluster.name,
                description=cluster.description,
                created_at=cluster.created_at,
                updated_at=cluster.updated_at,
            )
            postgres_session.merge(new_cluster)

        # Document cluster edges
        edges = sqlite_session.exec(select(DocumentClusterEdge)).all()
        for edge in edges:
            new_edge = DocumentClusterEdge(
                id=edge.id,
                document_id=edge.document_id,
                cluster_id=edge.cluster_id,
                created_at=edge.created_at,
            )
            postgres_session.merge(new_edge)

        # Document links
        links = sqlite_session.exec(select(DocumentLink)).all()
        for link in links:
            new_link = DocumentLink(
                id=link.id,
                source_document_id=link.source_document_id,
                target_document_id=link.target_document_id,
                anchor_text=link.anchor_text,
                created_at=link.created_at,
            )
            postgres_session.merge(new_link)

        postgres_session.commit()
        progress.update(task4, completed=1, total=1)

    # 5. Update configuration
    console.print("\n[dim]Updating kurt.config...[/dim]")
    config = load_config()
    config.DATABASE_URL = target_url
    config.WORKSPACE_ID = workspace_id
    update_config(config)

    # 6. Summary
    console.print("\n[green]✓ Migration complete![/green]\n")

    summary = Table(show_header=True, header_style="bold green")
    summary.add_column("Component", style="dim")
    summary.add_column("Migrated", justify="right")

    summary.add_row("Documents", f"{migrated_docs}")
    if skipped_docs > 0:
        summary.add_row("Documents (skipped, already exist)", f"{skipped_docs}")
    summary.add_row("Entities", f"{migrated_entities}")
    summary.add_row("Relationships", f"{len(relationships)}")
    summary.add_row("Topic Clusters", f"{len(cluster_count)}")
    summary.add_row("Document Links", f"{len(links)}")

    console.print(summary)

    console.print("\n[bold]Next steps:[/bold]")
    console.print("  1. Test your connection: [cyan]kurt status[/cyan]")
    console.print("  2. Verify data: [cyan]kurt content list[/cyan]")
    console.print("  3. Your content files remain local in [cyan]sources/[/cyan]")
    console.print("  4. Commit to git: [cyan]git add sources/ kurt.config && git commit[/cyan]")

    if workspace_id:
        console.print(f"\n[dim]Workspace ID: {workspace_id}[/dim]")

    console.print("\n[yellow]⚠ Keep your SQLite database as a backup:[/yellow]")
    console.print("[dim]cp .kurt/kurt.sqlite .kurt/kurt.sqlite.backup[/dim]")


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

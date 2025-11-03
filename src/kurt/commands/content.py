"""Content management CLI commands - unified ingestion and document management."""

import asyncio
import logging

import click
from rich.console import Console
from rich.table import Table

console = Console()
logger = logging.getLogger(__name__)


# ============================================================================
# Command Group
# ============================================================================


@click.group()
def content():
    """Manage content ingestion and documents."""
    pass


# ============================================================================
# NOTE: The 'fetch' command has been moved to root level (kurt fetch)
# Old location: kurt content fetch
# New location: kurt fetch
#
# This aligns with CLI-SPEC.md where fetch is a root-level command alongside
# map and cluster-urls in the primary workflow: map → cluster-urls → fetch
# ============================================================================


@content.command("index")
@click.argument("doc-id", required=False)
@click.option(
    "--include",
    "include_pattern",
    type=str,
    help="Index documents matching glob pattern (source_url or content_path)",
)
@click.option(
    "--all",
    is_flag=True,
    help="Index all FETCHED documents that haven't been indexed yet",
)
@click.option(
    "--force",
    is_flag=True,
    help="Re-index documents even if already indexed",
)
def index(doc_id: str, include_pattern: str, all: bool, force: bool):
    """
    Extract metadata from document(s).

    Runs LLM-based content analysis to extract:
    - Content type (tutorial, guide, blog, etc.)
    - Primary topics
    - Tools/technologies mentioned
    - Structural elements (code examples, step-by-step, narrative)

    Examples:
        # Index single document
        kurt content index 44ea066e

        # Index all documents matching pattern
        kurt content index --include "*/docs/*"

        # Index all un-indexed documents
        kurt content index --all

        # Re-index already indexed documents
        kurt content index --include "*/docs/*" --force
    """
    from kurt.document import list_documents_for_indexing
    from kurt.ingestion.index import batch_extract_document_metadata, extract_document_metadata

    try:
        # Get documents to index using service layer function
        try:
            documents = list_documents_for_indexing(
                doc_id=doc_id,
                include_pattern=include_pattern,
                all_flag=all,
            )
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            if "Must provide either" in str(e):
                console.print("Use --help for examples")
            raise click.Abort()

        if not documents:
            console.print("[yellow]No documents found matching criteria[/yellow]")
            return

        console.print(f"[bold]Indexing {len(documents)} document(s)...[/bold]\n")

        # Use async batch processing for multiple documents (>1)
        if len(documents) > 1:
            console.print("[dim]Using async batch processing (max 5 concurrent)...[/dim]\n")

            # Extract document IDs
            document_ids = [str(doc.id) for doc in documents]

            # Run async batch extraction
            batch_result = asyncio.run(
                batch_extract_document_metadata(document_ids, max_concurrent=5, force=force)
            )

            # Display results
            for result in batch_result["results"]:
                if result.get("skipped", False):
                    console.print(f"[dim]{result['title']}[/dim]")
                    console.print("  [yellow]○[/yellow] Skipped (content unchanged)")
                else:
                    console.print(f"[dim]{result['title']}[/dim]")
                    console.print(f"  [green]✓[/green] {result['content_type']}: {result['title']}")
                    if result["topics"]:
                        console.print(f"    Topics: {', '.join(result['topics'][:3])}")
                    if result["tools"]:
                        console.print(f"    Tools: {', '.join(result['tools'][:3])}")

            # Display errors
            for error in batch_result["errors"]:
                console.print(f"[dim]{error['document_id']}[/dim]")
                console.print(f"  [red]✗[/red] Error: {error['error']}")

            indexed_count = batch_result["succeeded"] - batch_result["skipped"]
            skipped_count = batch_result["skipped"]
            error_count = batch_result["failed"]

        else:
            # Single document - use synchronous processing
            indexed_count = 0
            skipped_count = 0
            error_count = 0

            for doc in documents:
                try:
                    console.print(f"[dim]Processing: {doc.source_url}[/dim]")

                    # Extract and persist metadata
                    result = extract_document_metadata(str(doc.id), force=force)

                    if result.get("skipped", False):
                        console.print("  [yellow]○[/yellow] Skipped (content unchanged)")
                        skipped_count += 1
                    else:
                        console.print(
                            f"  [green]✓[/green] {result['content_type']}: {result['title']}"
                        )
                        if result["topics"]:
                            console.print(f"    Topics: {', '.join(result['topics'][:3])}")
                        if result["tools"]:
                            console.print(f"    Tools: {', '.join(result['tools'][:3])}")
                        indexed_count += 1

                except Exception as e:
                    console.print(f"  [red]✗[/red] Error: {e}")
                    error_count += 1
                    logger.exception(f"Failed to index document {doc.id}")

        # Process any pending metadata sync queue items
        # (handles SQL/agent updates that bypassed normal indexing)
        from kurt.db.metadata_sync import process_metadata_sync_queue

        queue_result = process_metadata_sync_queue()
        queue_synced = queue_result["processed"]

        # Summary
        console.print("\n[bold]Summary:[/bold]")
        console.print(f"  Indexed: {indexed_count}")
        if skipped_count > 0:
            console.print(f"  Skipped: {skipped_count}")
        if error_count > 0:
            console.print(f"  Errors: {error_count}")
        if queue_synced > 0:
            console.print(f"  Queue synced: {queue_synced}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


# ============================================================================
# Document Management Commands: list, get, delete, stats
# ============================================================================


@content.command("list")
@click.option(
    "--with-status",
    type=click.Choice(["NOT_FETCHED", "FETCHED", "ERROR"], case_sensitive=False),
    help="Filter by ingestion status (NOT_FETCHED | FETCHED | ERROR)",
)
@click.option(
    "--include",
    "include_pattern",
    type=str,
    help="Filter by URL/path pattern (glob matching source_url or content_path)",
)
@click.option(
    "--in-cluster",
    type=str,
    help="Filter by cluster name",
)
@click.option(
    "--with-content-type",
    type=str,
    help="Filter by content type (tutorial | guide | blog | etc)",
)
@click.option(
    "--max-depth",
    type=int,
    help="Filter by maximum URL depth (e.g., example.com/a/b has depth 2)",
)
@click.option("--limit", type=int, help="Limit number of results")
@click.option("--offset", type=int, default=0, help="Number of documents to skip (for pagination)")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format for AI agents",
)
def list_documents_cmd(
    with_status: str,
    include_pattern: str,
    in_cluster: str,
    with_content_type: str,
    max_depth: int,
    limit: int,
    offset: int,
    output_format: str,
):
    """
    List all your documents.

    Examples:
        kurt content list
        kurt content list --with-status FETCHED
        kurt content list --include "*/docs/*"
        kurt content list --in-cluster "Tutorials"
        kurt content list --with-content-type tutorial
        kurt content list --max-depth 2
        kurt content list --limit 20 --format json
    """
    from kurt.document import list_content

    try:
        # Call ingestion layer function
        docs = list_content(
            with_status=with_status,
            include_pattern=include_pattern,
            in_cluster=in_cluster,
            with_content_type=with_content_type,
            max_depth=max_depth,
            limit=limit,
            offset=offset,
        )

        if not docs:
            console.print("[yellow]No documents found[/yellow]")
            return

        # Output formatting (presentation layer - stays in command)
        if output_format == "json":
            import json

            print(json.dumps(docs, indent=2, default=str))
        else:
            # Create table
            table = Table(title=f"Documents ({len(docs)} shown)")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Title", style="white")
            table.add_column("Status", style="green")
            table.add_column("Depth", style="magenta", justify="right")
            table.add_column("Count", style="yellow", justify="right")
            table.add_column("URL", style="dim")

            # Calculate child counts for each document (from entire database, not just filtered results)
            from kurt.document import list_content
            from kurt.utils.url_utils import get_url_depth

            # Get ALL documents to calculate accurate child counts
            all_docs = list_content()

            # Build a map of URL -> child count
            child_counts = {}
            for doc in docs:
                if doc.source_url:
                    # Count how many docs in the entire database have URLs that start with this URL
                    count = sum(
                        1
                        for d in all_docs
                        if d.source_url
                        and d.source_url != doc.source_url
                        and d.source_url.startswith(doc.source_url.rstrip("/") + "/")
                    )
                    child_counts[doc.source_url] = count

            for doc in docs:
                # Truncate title and URL for display
                title = (
                    (doc.title or "Untitled")[:50] + "..."
                    if doc.title and len(doc.title) > 50
                    else (doc.title or "Untitled")
                )
                url = (
                    doc.source_url[:40] + "..."
                    if doc.source_url and len(doc.source_url) > 40
                    else doc.source_url
                )

                # Calculate URL depth
                depth = get_url_depth(doc.source_url)

                # Get child count
                child_count = child_counts.get(doc.source_url, 0)

                # Color status
                status_str = doc.ingestion_status.value
                if status_str == "FETCHED":
                    status_display = f"[green]{status_str}[/green]"
                elif status_str == "ERROR":
                    status_display = f"[red]{status_str}[/red]"
                else:
                    status_display = f"[yellow]{status_str}[/yellow]"

                table.add_row(
                    str(doc.id)[:8] + "...",
                    title,
                    status_display,
                    str(depth),
                    str(child_count),
                    url or "N/A",
                )

            console.print(table)

            # Show tip for getting full details
            console.print(
                "\n[dim]Tip: Use [cyan]kurt content get <id>[/cyan] for full details[/dim]"
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@content.command("get")
@click.argument("document_id")
@click.option(
    "--format",
    type=click.Choice(["pretty", "json"], case_sensitive=False),
    default="pretty",
    help="Output format",
)
def get_document_cmd(document_id: str, format: str):
    """
    Get document metadata by ID.

    Examples:
        kurt content get 550e8400-e29b-41d4-a716-446655440000
        kurt content get 550e8400 --format json
    """
    from kurt.document import get_document

    try:
        doc = get_document(document_id)

        if format == "json":
            import json

            print(json.dumps(doc, indent=2, default=str))
        else:
            # Pretty print document details
            console.print("\n[bold cyan]Document Details[/bold cyan]")
            console.print(f"[dim]{'─' * 60}[/dim]")

            console.print(f"[bold]ID:[/bold] {doc.id}")
            console.print(f"[bold]Title:[/bold] {doc.title or 'Untitled'}")
            console.print(f"[bold]Status:[/bold] {doc.ingestion_status.value}")
            console.print(f"[bold]Source Type:[/bold] {doc.source_type.value}")
            console.print(f"[bold]Source URL:[/bold] {doc.source_url or 'N/A'}")

            if doc.description:
                console.print("\n[bold]Description:[/bold]")
                console.print(f"  {doc.description[:200]}...")

            if doc.author:
                console.print(f"\n[bold]Author(s):[/bold] {', '.join(doc.author)}")

            if doc.published_date:
                console.print(f"[bold]Published:[/bold] {doc.published_date}")

            if doc.content_hash:
                console.print(f"[bold]Content Hash:[/bold] {doc.content_hash[:16]}...")

            console.print(f"\n[bold]Content Path:[/bold] {doc.content_path or 'N/A'}")
            console.print(f"[bold]Created:[/bold] {doc.created_at}")
            console.print(f"[bold]Updated:[/bold] {doc.updated_at}")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@content.command("delete")
@click.argument("document_id")
@click.option(
    "--delete-content",
    is_flag=True,
    help="Also delete content file from filesystem",
)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt",
)
def delete_document_cmd(document_id: str, delete_content: bool, force: bool):
    """
    Delete content from your project.

    Examples:
        kurt content delete 550e8400-e29b-41d4-a716-446655440000
        kurt content delete 550e8400 --delete-content
        kurt content delete 550e8400 --force
    """
    from kurt.document import delete_document, get_document

    try:
        # Get document first to show what will be deleted
        doc = get_document(document_id)

        # Show what will be deleted
        console.print("\n[yellow]About to delete:[/yellow]")
        console.print(f"  ID: [cyan]{doc.id}[/cyan]")
        console.print(f"  Title: {doc.title or 'Untitled'}")
        console.print(f"  URL: {doc.source_url or 'N/A'}")

        if delete_content:
            console.print("  [red]Content file will also be deleted[/red]")

        # Confirm deletion
        if not force:
            confirm = console.input("\n[bold]Are you sure? (y/N):[/bold] ")
            if confirm.lower() != "y":
                console.print("[dim]Cancelled[/dim]")
                return

        # Delete document
        result = delete_document(document_id, delete_content=delete_content)

        console.print(f"\n[green]✓[/green] Deleted document: [cyan]{result['deleted_id']}[/cyan]")
        console.print(f"  Title: {result['title']}")

        if delete_content:
            if result["content_deleted"]:
                console.print("  [green]✓[/green] Content file deleted")
            else:
                console.print("  [yellow]Content file not found or not deleted[/yellow]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@content.command("stats")
@click.option(
    "--include",
    "include_pattern",
    help="Filter stats by URL/path pattern (glob matching source_url or source_path)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format",
)
def stats_cmd(include_pattern: str, output_format: str):
    """
    Show document statistics.

    Examples:
        kurt content stats
        kurt content stats --include "*docs.dagster.io*"
        kurt content stats --format json
    """
    from kurt.document import get_document_stats

    try:
        stats = get_document_stats(include_pattern=include_pattern)

        if output_format == "json":
            import json

            console.print(json.dumps(stats, indent=2))
        else:
            console.print("\n[bold cyan]Document Statistics[/bold cyan]")
            console.print(f"[dim]{'─' * 40}[/dim]")
            if include_pattern:
                console.print(f"[dim]Filter: {include_pattern}[/dim]\n")
            console.print(f"Total Documents:     [bold]{stats['total']}[/bold]")
            console.print(f"  Not Fetched:       [yellow]{stats['not_fetched']}[/yellow]")
            console.print(f"  Fetched:           [green]{stats['fetched']}[/green]")
            console.print(f"  Error:             [red]{stats['error']}[/red]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


# ============================================================================
# Clustering Commands: list-clusters
# ============================================================================

# NOTE: content cluster command has been REMOVED
# Clustering is now at root level: `kurt cluster-urls`
# See: src/kurt/commands/cluster_urls.py


@content.command("list-clusters")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format for AI agents",
)
def list_clusters_cmd(output_format: str):
    """
    List all topic clusters with document counts.

    Examples:
        kurt content list-clusters
        kurt content list-clusters --format json
    """
    from kurt.document import list_clusters

    try:
        clusters = list_clusters()

        if not clusters:
            console.print("[yellow]No clusters found[/yellow]")
            console.print(
                "[dim]Tip: Run [cyan]kurt cluster-urls[/cyan] to create topic clusters[/dim]"
            )
            return

        # Output formatting
        if output_format == "json":
            import json

            output = [
                {
                    "id": str(cluster["id"]),
                    "name": cluster["name"],
                    "description": cluster["description"],
                    "doc_count": cluster["doc_count"],
                    "created_at": cluster["created_at"].isoformat(),
                }
                for cluster in clusters
            ]
            print(json.dumps(output, indent=2))
        else:
            # Table format
            table = Table(title=f"Topic Clusters ({len(clusters)} total)")
            table.add_column("Name", style="cyan bold", no_wrap=False)
            table.add_column("Description", style="white", no_wrap=False)
            table.add_column("Docs", style="green", justify="right")
            table.add_column("Created", style="dim")

            for cluster in clusters:
                # Truncate description if too long
                description = (
                    (cluster["description"][:60] + "...")
                    if cluster["description"] and len(cluster["description"]) > 60
                    else (cluster["description"] or "N/A")
                )

                # Format created_at
                created = cluster["created_at"].strftime("%Y-%m-%d")

                table.add_row(
                    cluster["name"],
                    description,
                    str(cluster["doc_count"]),
                    created,
                )

            console.print(table)

            # Show tips
            console.print(
                '\n[dim]💡 Tip: Use [cyan]kurt content list --in-cluster "ClusterName"[/cyan] to see documents in a cluster[/dim]'
            )
            console.print(
                '[dim]💡 Tip: Use [cyan]kurt fetch --in-cluster "ClusterName"[/cyan] to fetch documents from a cluster[/dim]'
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Failed to list clusters")
        raise click.Abort()


# ============================================================================
# Metadata Sync Command
# ============================================================================


@content.command("sync-metadata")
@click.option(
    "--include",
    "include_patterns",
    multiple=True,
    help="Sync specific URL/path pattern (glob matching source_url or source_path, repeatable)",
)
@click.option(
    "--all",
    is_flag=True,
    help="Sync all documents (overrides --include)",
)
def sync_metadata(include_patterns: tuple, all: bool):
    """Process metadata sync queue and update file frontmatter.

    This command processes any pending metadata changes that were made via
    direct SQL updates or external tools, and writes the updated metadata
    as YAML frontmatter to the corresponding markdown files.

    Examples:
        # Sync specific pattern
        kurt content sync-metadata --include "*docs.dagster.io*"

        # Sync all documents
        kurt content sync-metadata --all
    """
    from kurt.db.metadata_sync import process_metadata_sync_queue
    from kurt.document import list_content

    try:
        # Determine which documents to sync
        if all:
            console.print("[cyan]Syncing metadata for all documents...[/cyan]")
            docs = list_content(limit=None)
        elif include_patterns:
            console.print(
                f"[cyan]Syncing metadata for documents matching: {', '.join(include_patterns)}[/cyan]"
            )
            # Combine results from all patterns
            docs = []
            for pattern in include_patterns:
                pattern_docs = list_content(include_pattern=pattern, limit=None)
                docs.extend(pattern_docs)
            # Remove duplicates
            seen = set()
            unique_docs = []
            for doc in docs:
                if doc.id not in seen:
                    seen.add(doc.id)
                    unique_docs.append(doc)
            docs = unique_docs
        else:
            console.print("[yellow]Error: Please specify --include <pattern> or --all[/yellow]")
            console.print("\nExamples:")
            console.print('  kurt content sync-metadata --include "*docs.dagster.io*"')
            console.print("  kurt content sync-metadata --all")
            return

        if not docs:
            console.print("[yellow]No documents found matching criteria[/yellow]")
            return

        console.print(f"[dim]Found {len(docs)} documents to sync...[/dim]\n")

        # Process sync for these documents
        result = process_metadata_sync_queue(document_ids=[str(doc.id) for doc in docs])

        if result["processed"] == 0:
            console.print("[dim]No pending metadata updates.[/dim]")
        else:
            console.print(
                f"[green]✓[/green] Synced frontmatter for {result['processed']} document(s)"
            )

        if result["errors"]:
            console.print(f"\n[yellow]⚠[/yellow]  {len(result['errors'])} error(s):")
            for error in result["errors"]:
                console.print(f"  • Document {error['document_id']}: {error['error']}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception("Failed to process metadata sync queue")
        raise click.Abort()

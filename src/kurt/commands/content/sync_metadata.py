"""Sync-metadata command - Process metadata sync queue."""

import logging

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command

console = Console()
logger = logging.getLogger(__name__)


@click.command("sync-metadata")
@track_command
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
    from kurt.content.document import list_content
    from kurt.db.metadata_sync import process_metadata_sync_queue

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

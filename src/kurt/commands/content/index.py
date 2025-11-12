"""Index command - Extract metadata from documents using LLM."""

import asyncio
import logging

import click
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


@click.command("index")
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
@click.option(
    "--limit",
    type=int,
    help="Maximum number of documents to index (default: no limit)",
)
def index(doc_id: str, include_pattern: str, all: bool, force: bool, limit: int):
    """
    Extract metadata from FETCHED documents using LLM analysis.

    \b
    What it extracts:
    - Content type (tutorial, guide, blog, reference doc, etc.)
    - Primary topics and themes
    - Tools and technologies mentioned
    - Structural elements (code examples, step-by-step instructions, etc.)

    \b
    Note: Only works on FETCHED documents (use 'kurt fetch' first).
    Cost: ~$0.005 per document (OpenAI API).

    \b
    Examples:
        # Index single document
        kurt content index 44ea066e

        # Index all documents matching pattern
        kurt content index --include "*/docs/*"

        # Index all un-indexed documents
        kurt content index --all

        # Index with a limit
        kurt content index --all --limit 10

        # Re-index already indexed documents
        kurt content index --include "*/docs/*" --force
    """
    from kurt.content.document import list_documents_for_indexing
    from kurt.content.index import batch_extract_document_metadata, extract_document_metadata

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

        # Apply limit if specified
        if limit and len(documents) > limit:
            console.print(
                f"[dim]Limiting to first {limit} documents out of {len(documents)} found[/dim]"
            )
            documents = documents[:limit]

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

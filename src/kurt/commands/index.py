"""Document indexing CLI commands."""

import asyncio
import logging

import click
from rich.console import Console

from kurt.indexing import batch_extract_document_metadata, extract_document_metadata

console = Console()
logger = logging.getLogger(__name__)


# ============================================================================
# CLI Command
# ============================================================================


@click.command()
@click.argument("doc-id", required=False)
@click.option(
    "--url-prefix",
    type=str,
    help="Index all documents matching URL prefix (e.g., https://example.com/blog/)",
)
@click.option(
    "--url-contains",
    type=str,
    help="Index all documents where URL contains substring (e.g., tutorial)",
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
def index(doc_id: str, url_prefix: str, url_contains: str, all: bool, force: bool):
    """
    Extract metadata from document(s).

    Runs LLM-based content analysis to extract:
    - Content type (tutorial, guide, blog, etc.)
    - Primary topics
    - Tools/technologies mentioned
    - Structural elements (code examples, step-by-step, narrative)

    Examples:
        # Index single document
        kurt index 44ea066e

        # Index all documents from URL prefix
        kurt index --url-prefix https://example.com/blog/

        # Index all documents containing "tutorial"
        kurt index --url-contains tutorial

        # Index all un-indexed documents
        kurt index --all

        # Re-index already indexed documents
        kurt index --url-prefix https://example.com --force
    """
    from kurt.database import get_session
    from kurt.document import get_document, list_documents
    from kurt.models.models import IngestionStatus

    try:
        session = get_session()

        # Determine which documents to index
        documents = []

        if doc_id:
            # Single document mode
            try:
                doc = get_document(doc_id)
                if not doc:
                    console.print(f"[red]Document not found: {doc_id}[/red]")
                    raise click.Abort()
                documents = [doc]
            except ValueError as e:
                console.print(f"[red]Error: {e}[/red]")
                raise click.Abort()

        elif url_prefix or url_contains or all:
            # Batch mode - get matching documents
            docs = list_documents(
                status=IngestionStatus.FETCHED,
                url_prefix=url_prefix,
                url_contains=url_contains,
                limit=None,  # No limit for indexing
            )

            if not docs:
                console.print("[yellow]No documents found matching criteria[/yellow]")
                return

            documents = docs

        else:
            console.print("[red]Error: Provide either <doc-id> or filtering options[/red]")
            console.print("Use --help for examples")
            raise click.Abort()

        console.print(f"[bold]Indexing {len(documents)} document(s)...[/bold]\n")

        # Use async batch processing for multiple documents (>1)
        if len(documents) > 1:
            console.print(f"[dim]Using async batch processing (max 5 concurrent)...[/dim]\n")

            # Extract document IDs
            document_ids = [str(doc.id) for doc in documents]

            # Run async batch extraction
            batch_result = asyncio.run(
                batch_extract_document_metadata(document_ids, max_concurrent=5, force=force)
            )

            # Display results
            for result in batch_result['results']:
                if result.get('skipped', False):
                    console.print(f"[dim]{result['title']}[/dim]")
                    console.print(f"  [yellow]○[/yellow] Skipped (content unchanged)")
                else:
                    console.print(f"[dim]{result['title']}[/dim]")
                    console.print(
                        f"  [green]✓[/green] {result['content_type']}: {result['title']}"
                    )
                    if result['topics']:
                        console.print(f"    Topics: {', '.join(result['topics'][:3])}")
                    if result['tools']:
                        console.print(f"    Tools: {', '.join(result['tools'][:3])}")

            # Display errors
            for error in batch_result['errors']:
                console.print(f"[dim]{error['document_id']}[/dim]")
                console.print(f"  [red]✗[/red] Error: {error['error']}")

            indexed_count = batch_result['succeeded'] - batch_result['skipped']
            skipped_count = batch_result['skipped']
            error_count = batch_result['failed']

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

                    if result.get('skipped', False):
                        console.print(f"  [yellow]○[/yellow] Skipped (content unchanged)")
                        skipped_count += 1
                    else:
                        console.print(
                            f"  [green]✓[/green] {result['content_type']}: {result['title']}"
                        )
                        if result['topics']:
                            console.print(f"    Topics: {', '.join(result['topics'][:3])}")
                        if result['tools']:
                            console.print(f"    Tools: {', '.join(result['tools'][:3])}")
                        indexed_count += 1

                except Exception as e:
                    console.print(f"  [red]✗[/red] Error: {e}")
                    error_count += 1
                    logger.exception(f"Failed to index document {doc.id}")

        # Summary
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Indexed: {indexed_count}")
        if skipped_count > 0:
            console.print(f"  Skipped: {skipped_count}")
        if error_count > 0:
            console.print(f"  Errors: {error_count}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()

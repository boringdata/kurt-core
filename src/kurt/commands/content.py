"""Content management CLI commands - unified ingestion and document management."""

import asyncio
import logging

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
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
# Ingestion Commands: add, fetch, index
# ============================================================================


@content.command("add")
@click.argument("source")
@click.option("--fetch-only", is_flag=True, help="Discover + fetch only (skip indexing)")
@click.option(
    "--discover-only", is_flag=True, help="Discover only (skip fetch & index) [URLs only]"
)
@click.option("--dry-run", is_flag=True, help="Preview what would be added (no DB changes)")
@click.option(
    "--url-contains", type=str, help="Filter: only include URLs containing this string [URLs only]"
)
@click.option(
    "--url-starts-with",
    type=str,
    help="Filter: only include URLs starting with this prefix [URLs only]",
)
@click.option("--limit", type=int, help="Maximum number of pages/files to process")
@click.option("--force", is_flag=True, help="Skip confirmation for large batches")
@click.option(
    "--max-concurrent", type=int, default=5, help="Max parallel downloads (default: 5) [URLs only]"
)
@click.option(
    "--discover-dates",
    is_flag=True,
    help="Discover publish dates from blogroll/changelog pages [URLs only]",
)
@click.option(
    "--max-blogrolls",
    type=int,
    default=10,
    help="Maximum blogroll pages to scrape (default: 10) [URLs only]",
)
@click.option(
    "--fetch-engine",
    type=click.Choice(["firecrawl", "trafilatura"], case_sensitive=False),
    help="Fetch engine to use (overrides config default) [URLs only]",
)
def add(
    source: str,
    fetch_only: bool,
    discover_only: bool,
    dry_run: bool,
    url_contains: str,
    url_starts_with: str,
    limit: int,
    force: bool,
    max_concurrent: int,
    discover_dates: bool,
    max_blogrolls: int,
    fetch_engine: str,
):
    """
    Add content from URLs or local files to Kurt (discover + fetch + index in one command).

    Automatically detects source type:
    - URLs: http://, https://
    - Files: ./file.md, /path/to/file.md (must be .md)
    - Directories: ./docs/, /path/to/docs/ (processes all .md files recursively)

    Examples:
        # Add from URL (single page)
        kurt content add https://example.com/blog/my-post

        # Add from URL (entire site, auto-detects from sitemap)
        kurt content add https://example.com

        # Add single markdown file
        kurt content add ./article.md

        # Add directory of markdown files
        kurt content add ./documents/

        # Add with filters (URLs only)
        kurt content add https://example.com --url-contains "/blog/2024/"

        # Add without indexing (save LLM costs)
        kurt content add https://example.com --fetch-only
        kurt content add ./documents/ --fetch-only

        # Preview without adding
        kurt content add https://example.com --dry-run
        kurt content add ./documents/ --dry-run
    """
    from kurt.commands.add_files import handle_file_add
    from kurt.commands.add_urls import handle_url_add
    from kurt.ingestion.source_detection import detect_source_type

    # Detect source type
    source_type = detect_source_type(source)

    # Route to appropriate handler
    if source_type in ["file", "directory"]:
        # Validate that URL-specific options aren't used
        url_specific_options = {
            "discover_only": discover_only,
            "url_contains": url_contains,
            "url_starts_with": url_starts_with,
            "max_concurrent": max_concurrent != 5,  # Changed from default
            "discover_dates": discover_dates,
            "max_blogrolls": max_blogrolls != 10,  # Changed from default
            "fetch_engine": fetch_engine,
        }

        active_url_options = [k for k, v in url_specific_options.items() if v]
        if active_url_options:
            console.print(
                f"[red]Error:[/red] The following options are only valid for URLs: {', '.join('--' + k.replace('_', '-') for k in active_url_options)}"
            )
            raise click.Abort()

        # Handle file/directory
        handle_file_add(
            source=source,
            fetch_only=fetch_only,
            dry_run=dry_run,
            limit=limit,
            force=force,
        )
    else:
        # Handle URL
        handle_url_add(
            url=source,
            fetch_only=fetch_only,
            discover_only=discover_only,
            dry_run=dry_run,
            url_contains=url_contains,
            url_starts_with=url_starts_with,
            limit=limit,
            force=force,
            max_concurrent=max_concurrent,
            discover_dates=discover_dates,
            max_blogrolls=max_blogrolls,
            fetch_engine=fetch_engine,
        )


@content.command("fetch")
@click.argument("identifier", required=False)
@click.option(
    "--url-prefix", help="Batch: Fetch URLs starting with this prefix (alias for --url-starts-with)"
)
@click.option("--url-starts-with", help="Batch: Fetch URLs starting with this prefix")
@click.option("--url-contains", help="Batch: Fetch URLs containing this string")
@click.option("--all", "fetch_all", is_flag=True, help="Batch: Fetch all documents with status")
@click.option(
    "--status",
    type=click.Choice(["NOT_FETCHED", "ERROR"]),
    default="NOT_FETCHED",
    help="Batch: Filter by status (default: NOT_FETCHED)",
)
@click.option(
    "--max-concurrent", type=int, default=5, help="Batch: Max parallel downloads (default: 5)"
)
@click.option("--force", is_flag=True, help="Re-fetch even if already fetched")
@click.option(
    "--fetch-engine",
    type=click.Choice(["firecrawl", "trafilatura"], case_sensitive=False),
    help="Fetch engine to use (overrides config default)",
)
def fetch(
    identifier: str,
    url_prefix: str,
    url_starts_with: str,
    url_contains: str,
    fetch_all: bool,
    status: str,
    max_concurrent: int,
    force: bool,
    fetch_engine: str,
):
    """
    Fetch content from URLs.

    Single document mode (provide identifier):
        kurt content fetch <doc-id>          # By document ID
        kurt content fetch <url>             # By URL (creates if needed)

    Batch mode (use filters):
        kurt content fetch --url-starts-with https://example.com/blog/
        kurt content fetch --url-contains tutorial
        kurt content fetch --all             # All NOT_FETCHED docs
        kurt content fetch --status ERROR    # Retry failed fetches

    Examples:
        # Fetch single document
        kurt content fetch 44ea066e

        # Fetch all unfetched documents
        kurt content fetch --all

        # Fetch documents from specific section
        kurt content fetch --url-starts-with https://example.com/blog/

        # Retry failed fetches
        kurt content fetch --status ERROR --force

        # Fetch with more parallelism
        kurt content fetch --all --max-concurrent 10

        # Use specific fetch engine
        kurt content fetch --all --fetch-engine firecrawl
    """
    from sqlmodel import select

    from kurt.db.database import get_session
    from kurt.db.models import Document, IngestionStatus
    from kurt.ingestion.fetch import fetch_document, fetch_documents_batch

    # Handle url_prefix as alias for url_starts_with
    if url_prefix and not url_starts_with:
        url_starts_with = url_prefix

    # Single document mode
    if identifier:
        if url_starts_with or url_contains or fetch_all:
            console.print(
                "[red]Error:[/red] Cannot use identifier with batch options (--url-starts-with, --url-contains, --all)"
            )
            raise click.Abort()

        try:
            console.print(f"[cyan]Fetching content for:[/cyan] {identifier}\n")
            result = fetch_document(identifier, fetch_engine=fetch_engine)
            console.print(f"[green]✓ Fetched:[/green] {result['title']}")
            console.print(f"  Document ID: [cyan]{result['document_id']}[/cyan]")
            console.print(f"  Content: {result['content_length']} characters")
            if result.get("content_path"):
                console.print(f"  Path: {result['content_path']}")
            console.print(f"  Status: [green]{result['status']}[/green]")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise click.Abort()
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            console.print("\n[yellow]Document marked as ERROR status[/yellow]")
            raise click.Abort()
        return

    # Batch mode
    if not (url_starts_with or url_contains or fetch_all):
        console.print("[red]Error:[/red] Provide either:")
        console.print("  - An identifier: [cyan]kurt content fetch <doc-id>[/cyan]")
        console.print("  - Batch filters: [cyan]kurt content fetch --url-starts-with <url>[/cyan]")
        console.print("  - Fetch all: [cyan]kurt content fetch --all[/cyan]")
        raise click.Abort()

    try:
        # Build query
        session = get_session()

        # Start with base query
        stmt = select(Document)

        # Apply status filter unless force=True
        if not force:
            stmt = stmt.where(Document.ingestion_status == IngestionStatus[status])

        # Apply URL filters
        if url_starts_with:
            stmt = stmt.where(Document.source_url.startswith(url_starts_with))
        if url_contains:
            stmt = stmt.where(Document.source_url.contains(url_contains))

        docs = session.exec(stmt).all()

        if not docs:
            if force:
                filter_desc = url_starts_with or url_contains or "matching filters"
                console.print(f"[yellow]No documents found for:[/yellow] {filter_desc}")
            else:
                filter_desc = url_starts_with or url_contains or f"all {status}"
                console.print(f"[yellow]No {status} documents found for:[/yellow] {filter_desc}")
            return

        doc_ids = [str(doc.id) for doc in docs]
        console.print(
            f"[cyan]Fetching {len(doc_ids)} documents with {max_concurrent} parallel downloads...[/cyan]\n"
        )

        # Fetch in parallel with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching...", total=len(doc_ids))

            results = fetch_documents_batch(
                doc_ids, max_concurrent=max_concurrent, fetch_engine=fetch_engine
            )

            progress.update(task, completed=len(doc_ids))

        # Summary
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        console.print(f"\n[green]✓ Success:[/green] {len(successful)}/{len(results)} documents")
        if failed:
            console.print(f"[red]✗ Failed:[/red] {len(failed)} documents")
            for r in failed[:5]:  # Show first 5 errors
                console.print(
                    f"  [dim]{r.get('document_id', 'unknown')}: {r.get('error', 'Unknown error')}[/dim]"
                )
            if len(failed) > 5:
                console.print(f"  [dim]... and {len(failed) - 5} more[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@content.command("index")
@click.argument("doc-id", required=False)
@click.option(
    "--url-starts-with",
    type=str,
    help="Index all documents matching URL prefix (e.g., https://example.com/blog/)",
)
@click.option(
    "--url-prefix",
    type=str,
    help="Alias for --url-starts-with",
    hidden=True,
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
def index(
    doc_id: str, url_starts_with: str, url_prefix: str, url_contains: str, all: bool, force: bool
):
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

        # Index all documents from URL prefix
        kurt content index --url-starts-with https://example.com/blog/

        # Index all documents containing "tutorial"
        kurt content index --url-contains tutorial

        # Index all un-indexed documents
        kurt content index --all

        # Re-index already indexed documents
        kurt content index --url-starts-with https://example.com --force
    """
    from kurt.db.models import IngestionStatus
    from kurt.document import get_document, list_documents
    from kurt.ingestion.index import batch_extract_document_metadata, extract_document_metadata

    # Handle url_prefix as alias for url_starts_with
    if url_prefix and not url_starts_with:
        url_starts_with = url_prefix

    try:
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

        elif url_starts_with or url_contains or all:
            # Batch mode - get matching documents
            docs = list_documents(
                status=IngestionStatus.FETCHED,
                url_prefix=url_starts_with,
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
    "--status",
    type=click.Choice(["NOT_FETCHED", "FETCHED", "ERROR"], case_sensitive=False),
    help="Filter by ingestion status",
)
@click.option(
    "--url-starts-with",
    type=str,
    help="Filter by URL prefix (e.g., https://example.com)",
)
@click.option(
    "--url-prefix",
    type=str,
    help="Alias for --url-starts-with",
    hidden=True,
)
@click.option(
    "--url-contains",
    type=str,
    help="Filter by URL substring (e.g., blog)",
)
@click.option("--limit", type=int, help="Maximum number of documents to show")
@click.option("--offset", type=int, default=0, help="Number of documents to skip")
@click.option(
    "--format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format",
)
@click.option(
    "--with-analytics",
    is_flag=True,
    help="Include analytics data in results (shows traffic metrics)",
)
@click.option(
    "--pageviews-30d-min",
    type=int,
    help="Filter by minimum pageviews (last 30 days)",
)
@click.option(
    "--pageviews-30d-max",
    type=int,
    help="Filter by maximum pageviews (last 30 days)",
)
@click.option(
    "--pageviews-trend",
    type=click.Choice(["increasing", "stable", "decreasing"], case_sensitive=False),
    help="Filter by traffic trend",
)
@click.option(
    "--order-by",
    type=click.Choice(["created_at", "pageviews_30d", "pageviews_60d", "trend_percentage"], case_sensitive=False),
    help="Sort results by field (default: created_at)",
)
def list_documents_cmd(
    status: str,
    url_starts_with: str,
    url_prefix: str,
    url_contains: str,
    limit: int,
    offset: int,
    format: str,
    with_analytics: bool,
    pageviews_30d_min: int,
    pageviews_30d_max: int,
    pageviews_trend: str,
    order_by: str,
):
    """
    List all your documents.

    Examples:
        kurt content list
        kurt content list --status FETCHED
        kurt content list --url-starts-with https://example.com
        kurt content list --url-contains blog
        kurt content list --url-starts-with https://example.com --url-contains article
        kurt content list --limit 10
        kurt content list --format json
    """
    from kurt.db.models import IngestionStatus
    from kurt.document import list_documents

    # Handle url_prefix as alias for url_starts_with
    if url_prefix and not url_starts_with:
        url_starts_with = url_prefix

    try:
        # Convert status string to enum if provided
        status_filter = None
        if status:
            status_filter = IngestionStatus(status)

        docs = list_documents(
            status=status_filter,
            url_prefix=url_starts_with,
            url_contains=url_contains,
            limit=limit,
            offset=offset,
            with_analytics=with_analytics,
            pageviews_30d_min=pageviews_30d_min,
            pageviews_30d_max=pageviews_30d_max,
            pageviews_trend=pageviews_trend,
            order_by=order_by,
        )

        if not docs:
            console.print("[yellow]No documents found[/yellow]")
            return

        if format == "json":
            import json
            from kurt.db.database import get_session
            from kurt.db.models import DocumentAnalytics

            # Enrich with analytics data if requested
            result = []
            for doc in docs:
                doc_dict = {
                    "id": str(doc.id),
                    "title": doc.title,
                    "source_url": doc.source_url,
                    "ingestion_status": doc.ingestion_status.value,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                }
                if with_analytics:
                    # Get analytics data
                    session = get_session()
                    analytics = session.query(DocumentAnalytics).filter(
                        DocumentAnalytics.document_id == doc.id
                    ).first()
                    if analytics:
                        doc_dict["analytics"] = {
                            "pageviews_30d": analytics.pageviews_30d,
                            "pageviews_60d": analytics.pageviews_60d,
                            "pageviews_trend": analytics.pageviews_trend,
                            "trend_percentage": analytics.trend_percentage,
                            "unique_visitors_30d": analytics.unique_visitors_30d,
                            "bounce_rate": analytics.bounce_rate,
                        }
                    else:
                        doc_dict["analytics"] = None
                result.append(doc_dict)
            print(json.dumps(result, indent=2))
        else:
            # Create table
            table = Table(title=f"Documents ({len(docs)} shown)")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Title", style="white")
            table.add_column("Status", style="green")

            # Add analytics columns if requested
            if with_analytics:
                table.add_column("Views (30d)", style="yellow", justify="right")
                table.add_column("Trend", style="magenta")

            table.add_column("URL", style="dim")

            # Fetch analytics data for all docs if needed
            doc_analytics = {}
            if with_analytics:
                from kurt.db.database import get_session
                from kurt.db.models import DocumentAnalytics
                session = get_session()
                doc_ids = [doc.id for doc in docs]
                analytics_list = session.query(DocumentAnalytics).filter(
                    DocumentAnalytics.document_id.in_(doc_ids)
                ).all()
                doc_analytics = {a.document_id: a for a in analytics_list}

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

                # Color status
                status_str = doc.ingestion_status.value
                if status_str == "FETCHED":
                    status_display = f"[green]{status_str}[/green]"
                elif status_str == "ERROR":
                    status_display = f"[red]{status_str}[/red]"
                else:
                    status_display = f"[yellow]{status_str}[/yellow]"

                # Build row
                row = [
                    str(doc.id)[:8] + "...",
                    title,
                    status_display,
                ]

                # Add analytics columns if requested
                if with_analytics:
                    analytics = doc_analytics.get(doc.id)
                    if analytics:
                        pageviews = f"{analytics.pageviews_30d:,}"
                        trend_symbol = {
                            "increasing": "↑",
                            "stable": "→",
                            "decreasing": "↓",
                        }.get(analytics.pageviews_trend, "?")
                        trend_color = {
                            "increasing": "green",
                            "stable": "yellow",
                            "decreasing": "red",
                        }.get(analytics.pageviews_trend, "white")
                        trend_pct = f"{analytics.trend_percentage:+.0f}%" if analytics.trend_percentage else ""
                        trend_display = f"[{trend_color}]{trend_symbol} {trend_pct}[/{trend_color}]"
                        row.extend([pageviews, trend_display])
                    else:
                        row.extend(["-", "-"])

                row.append(url or "N/A")
                table.add_row(*row)

            console.print(table)

            # Show tip for getting full details
            console.print(
                "\n[dim]Tip: Use [cyan]kurt content get-metadata <id>[/cyan] for full details[/dim]"
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@content.command("get-metadata")
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
        kurt content get-metadata 550e8400-e29b-41d4-a716-446655440000
        kurt content get-metadata 550e8400 --format json
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
    "--yes",
    is_flag=True,
    help="Skip confirmation prompt",
)
def delete_document_cmd(document_id: str, delete_content: bool, yes: bool):
    """
    Delete content from your project.

    Examples:
        kurt content delete 550e8400-e29b-41d4-a716-446655440000
        kurt content delete 550e8400 --delete-content
        kurt content delete 550e8400 --yes
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
        if not yes:
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
    "--url-starts-with",
    type=str,
    help="Filter by URL prefix (e.g., https://docs.company.com)",
)
@click.option(
    "--show-analytics",
    is_flag=True,
    help="Show analytics statistics (traffic distribution, percentiles)",
)
def stats_cmd(url_starts_with: str, show_analytics: bool):
    """
    Show document statistics.

    Examples:
        kurt content stats
        kurt content stats --url-starts-with https://docs.company.com
        kurt content stats --show-analytics --url-starts-with https://docs.company.com
    """
    from kurt.document import get_analytics_stats, get_document_stats

    try:
        stats = get_document_stats()
        domain_label = url_starts_with if url_starts_with else "All Domains"

        console.print(f"\n[bold cyan]Document Statistics ({domain_label})[/bold cyan]")
        console.print(f"[dim]{'─' * 40}[/dim]")
        console.print(f"Total Documents:     [bold]{stats['total']}[/bold]")
        console.print(f"  Not Fetched:       [yellow]{stats['not_fetched']}[/yellow]")
        console.print(f"  Fetched:           [green]{stats['fetched']}[/green]")
        console.print(f"  Error:             [red]{stats['error']}[/red]")

        # Show analytics statistics if requested
        if show_analytics:
            analytics_stats = get_analytics_stats(url_prefix=url_starts_with)

            if analytics_stats['total_with_analytics'] > 0:
                console.print(f"\n[bold cyan]Analytics Statistics[/bold cyan]")
                console.print(f"[dim]{'─' * 40}[/dim]")
                console.print(f"Documents with Analytics: [bold]{analytics_stats['total_with_analytics']}[/bold]")
                console.print(f"\n[bold]Traffic Distribution (30d pageviews):[/bold]")
                console.print(f"  Average:        {analytics_stats['avg_pageviews_30d']:,.1f} views/month")
                console.print(f"  Median (p50):   {analytics_stats['median_pageviews_30d']:,} views/month")
                console.print(f"  75th %ile:      {analytics_stats['p75_pageviews_30d']:,} views/month  [dim](HIGH traffic threshold)[/dim]")
                console.print(f"  25th %ile:      {analytics_stats['p25_pageviews_30d']:,} views/month  [dim](LOW traffic threshold)[/dim]")

                console.print(f"\n[bold]Traffic Categories:[/bold]")
                cats = analytics_stats['traffic_categories']
                total = analytics_stats['total_with_analytics']
                console.print(f"  [red]ZERO traffic:[/red]    {cats['zero']:3d} pages ({cats['zero']/total*100:.0f}%)")
                console.print(f"  [yellow]LOW traffic:[/yellow]     {cats['low']:3d} pages ({cats['low']/total*100:.0f}%)  [dim](≤ p25)[/dim]")
                console.print(f"  [cyan]MEDIUM traffic:[/cyan]  {cats['medium']:3d} pages ({cats['medium']/total*100:.0f}%)  [dim](p25-p75)[/dim]")
                console.print(f"  [green]HIGH traffic:[/green]    {cats['high']:3d} pages ({cats['high']/total*100:.0f}%)  [dim](> p75)[/dim]")
            else:
                console.print(f"\n[yellow]No analytics data available for this domain[/yellow]")
                console.print(f"[dim]Run [cyan]kurt analytics onboard <domain>[/cyan] to enable analytics[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


# ============================================================================
# Clustering Commands: cluster
# ============================================================================


@content.command("cluster")
@click.option(
    "--url-starts-with",
    type=str,
    help="Compute clusters from documents matching URL prefix (e.g., https://example.com/blog/)",
)
@click.option(
    "--url-prefix",
    type=str,
    help="Alias for --url-starts-with",
    hidden=True,
)
@click.option(
    "--url-contains",
    type=str,
    help="Compute clusters from documents where URL contains substring (e.g., tutorial)",
)
@click.option(
    "--format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format",
)
def cluster_command(
    url_starts_with: str,
    url_prefix: str,
    url_contains: str,
    format: str,
):
    """
    Compute topic clusters from document metadata.

    Uses LLM to analyze document URLs, titles, and descriptions to identify
    5-10 distinct topic clusters. Creates TopicCluster records and links
    documents to clusters via DocumentClusterEdge.

    Examples:
        # Compute clusters from all blog posts
        kurt content cluster --url-starts-with https://example.com/blog/

        # Compute clusters from tutorial documents
        kurt content cluster --url-contains tutorial

        # Output as JSON
        kurt content cluster --url-starts-with https://example.com --format json
    """
    from kurt.ingestion.cluster import compute_topic_clusters

    # Handle url_prefix as alias for url_starts_with
    if url_prefix and not url_starts_with:
        url_starts_with = url_prefix

    try:
        if not url_starts_with and not url_contains:
            console.print("[red]Error: Provide either --url-starts-with or --url-contains[/red]")
            raise click.Abort()

        console.print("[bold]Computing topic clusters...[/bold]\n")

        # Run clustering
        result = compute_topic_clusters(
            url_prefix=url_starts_with,
            url_contains=url_contains,
        )

        # Display results
        if format == "json":
            import json

            console.print(json.dumps(result, indent=2))

        else:
            # Table format
            console.print(f"[green]✓[/green] Analyzed {result['total_pages']} documents")
            console.print(f"[green]✓[/green] Created {len(result['clusters'])} clusters")
            console.print(
                f"[green]✓[/green] Created {result['edges_created']} document-cluster links\n"
            )

            table = Table(title=f"Topic Clusters ({len(result['clusters'])} total)")
            table.add_column("Name", style="cyan", no_wrap=False)
            table.add_column("Description", style="white", no_wrap=False)
            table.add_column("Examples", style="dim", no_wrap=False)

            for cluster in result["clusters"]:
                example_urls_str = "\n".join(cluster["example_urls"][:3])
                table.add_row(
                    cluster["name"],
                    cluster["description"],
                    example_urls_str,
                )

            console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception("Failed to compute clusters")
        raise click.Abort()


# ============================================================================
# Metadata Sync Command
# ============================================================================


@content.command("sync-metadata")
def sync_metadata():
    """Process metadata sync queue and update file frontmatter.

    This command processes any pending metadata changes that were made via
    direct SQL updates or external tools, and writes the updated metadata
    as YAML frontmatter to the corresponding markdown files.
    """
    from kurt.db.metadata_sync import process_metadata_sync_queue

    try:
        console.print("[cyan]Processing metadata sync queue...[/cyan]")
        result = process_metadata_sync_queue()

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

"""Content ingestion CLI commands."""

import click
from rich.console import Console

console = Console()


@click.group()
def ingest():
    """Ingest content from web sources."""
    pass


@ingest.command("map")
@click.argument("url")
@click.option("--limit", type=int, help="Maximum number of URLs to process (creates + fetches)")
@click.option("--output", type=click.Choice(["list", "json"]), default="list", help="Output format")
@click.option("--fetch", is_flag=True, help="Fetch content for all documents immediately")
@click.option("--discover-dates", is_flag=True, help="Discover publish dates from blogroll/changelog pages")
@click.option("--max-blogrolls", type=int, default=10, help="Maximum blogroll pages to scrape (default: 10)")
def map_sitemap_cmd(url: str, limit: int, output: str, fetch: bool, discover_dates: bool, max_blogrolls: int):
    """
    Discover sitemap and create documents in database.

    Creates documents with NOT_FETCHED status for all URLs found in sitemap.
    If document already exists, skips creation.

    Use --fetch to download content immediately for all discovered URLs.
    Use --limit to process only the first N URLs (useful with --fetch).
    Use --discover-dates to extract publish dates from blogroll/changelog pages.

    Example:
        kurt ingest map https://example.com
        kurt ingest map https://example.com --limit 10
        kurt ingest map https://example.com --fetch
        kurt ingest map https://example.com --discover-dates
        kurt ingest map https://example.com --discover-dates --max-blogrolls 5
        kurt ingest map https://example.com --output json
    """
    from kurt.ingest_map import map_sitemap

    try:
        console.print(f"[cyan]Discovering sitemap for:[/cyan] {url}")
        if fetch:
            if limit:
                console.print(f"[cyan]Fetching content for first {limit} URLs...[/cyan]\n")
            else:
                console.print("[cyan]Fetching content for all URLs...[/cyan]\n")
        if discover_dates:
            console.print(f"[cyan]Will discover publish dates from up to {max_blogrolls} blogroll/changelog pages[/cyan]\n")

        docs = map_sitemap(url, fetch_all=fetch, limit=limit, discover_blogrolls=discover_dates, max_blogrolls=max_blogrolls)

        created_count = sum(1 for d in docs if d["created"])
        existing_count = len(docs) - created_count
        fetched_count = sum(1 for d in docs if d.get("fetched", False))

        # Separate sitemap vs blogroll docs
        sitemap_docs = [d for d in docs if d.get("discovery_method") != "blogroll"]
        blogroll_docs = [d for d in docs if d.get("discovery_method") == "blogroll"]
        dated_docs = [d for d in blogroll_docs if d.get("published_date")]

        console.print(f"[green]✓[/green] Found {len(sitemap_docs)} URLs from sitemap")
        console.print(f"  Created: [green]{created_count}[/green] new documents")
        if existing_count > 0:
            console.print(f"  Skipped: [yellow]{existing_count}[/yellow] existing documents")
        if fetch:
            console.print(f"  Fetched: [green]{fetched_count}[/green] documents")

        if discover_dates and blogroll_docs:
            console.print(f"\n[green]✓[/green] Discovered {len(blogroll_docs)} additional posts from blogrolls/changelogs")
            console.print(f"  With publish dates: [green]{len(dated_docs)}[/green] ({len(dated_docs)/len(blogroll_docs)*100:.0f}%)")

        console.print()

        if output == "json":
            import json

            print(json.dumps(docs, indent=2, default=str))
        else:
            # List format - show all docs (already limited by function)
            for doc in docs:
                status_icon = "✓" if doc["created"] else "○"
                status_color = "green" if doc["created"] else "yellow"

                # Show fetch icon if fetched
                if fetch and doc.get("fetched"):
                    status_icon = "⬇"
                    status_color = "blue"

                console.print(f"  [{status_color}]{status_icon}[/{status_color}] {doc['url']}")

                # Build metadata line
                metadata_parts = [f"ID: {doc['document_id']}", f"Status: {doc['status']}"]
                if doc.get("fetched"):
                    metadata_parts.append(f"{doc.get('content_length', 0)} chars")
                if doc.get("published_date"):
                    # Format date nicely
                    date_str = doc["published_date"].strftime("%Y-%m-%d") if hasattr(doc["published_date"], "strftime") else str(doc["published_date"])[:10]
                    metadata_parts.append(f"📅 {date_str}")

                console.print(f"     [dim]{' | '.join(metadata_parts)}[/dim]")

        if not fetch:
            console.print(f"\n[yellow]Tip:[/yellow] Fetch content with: [cyan]kurt ingest fetch <doc-id>[/cyan]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("\n[yellow]Tip:[/yellow] If no sitemap found, you can:")
        console.print("  1. Try crawling the website directly using trafilatura")
        console.print("  2. Manually add individual URLs with: [cyan]kurt ingest add <url>[/cyan]")
        raise click.Abort()


@ingest.command("add")
@click.argument("url")
@click.option("--title", help="Document title (defaults to last path segment)")
def add_document_cmd(url: str, title: str):
    """
    Add single document record (NOT_FETCHED status).

    Creates a document entry in the database without fetching content.
    If document already exists, returns existing document ID.
    Use 'kurt ingest fetch' to download content later.

    Example:
        kurt ingest add https://example.com/page1
        kurt ingest add https://example.com/page1 --title "My Page"
    """
    from kurt.ingest_fetch import add_document
    from sqlmodel import select

    from kurt.database import get_session
    from kurt.models.models import Document

    try:
        # Check if exists before adding
        session = get_session()
        stmt = select(Document).where(Document.source_url == url)
        existing_doc = session.exec(stmt).first()

        doc_id = add_document(url, title)

        if existing_doc:
            console.print(f"[yellow]○[/yellow] Document already exists: [cyan]{doc_id}[/cyan]")
        else:
            console.print(f"[green]✓[/green] Document created: [cyan]{doc_id}[/cyan]")

        console.print(f"[dim]URL: {url}[/dim]")
        console.print(f"[dim]Status: NOT_FETCHED[/dim]")
        console.print(f"\n[yellow]Tip:[/yellow] Fetch content with: [cyan]kurt ingest fetch {doc_id}[/cyan]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@ingest.command("fetch")
@click.argument("identifier", required=False)
@click.option("--url-prefix", help="Batch: Fetch URLs starting with this prefix")
@click.option("--url-contains", help="Batch: Fetch URLs containing this string")
@click.option("--all", "fetch_all", is_flag=True, help="Batch: Fetch all documents with status")
@click.option("--status", type=click.Choice(["NOT_FETCHED", "ERROR"]), default="NOT_FETCHED", help="Batch: Filter by status (default: NOT_FETCHED)")
@click.option("--max-concurrent", type=int, default=5, help="Batch: Max parallel downloads (default: 5)")
def fetch_document_cmd(identifier: str, url_prefix: str, url_contains: str, fetch_all: bool, status: str, max_concurrent: int):
    """
    Fetch content for one or multiple documents.

    \b
    Single document mode (provide identifier):
        kurt ingest fetch <doc-id>          # By document ID
        kurt ingest fetch <url>             # By URL (creates if needed)

    \b
    Batch mode (use filters):
        kurt ingest fetch --url-prefix https://example.com/
        kurt ingest fetch --url-contains /blog/
        kurt ingest fetch --all             # All NOT_FETCHED docs
        kurt ingest fetch --url-prefix https://example.com/ --max-concurrent 10
        kurt ingest fetch --url-prefix https://example.com/ --status ERROR
    """
    from kurt.database import get_session
    from kurt.models.models import Document, IngestionStatus
    from kurt.ingest_fetch import fetch_document, fetch_documents_batch
    from sqlmodel import select

    # Single document mode
    if identifier:
        if url_prefix or url_contains or fetch_all:
            console.print("[red]Error:[/red] Cannot use identifier with batch options (--url-prefix, --url-contains, --all)")
            raise click.Abort()

        try:
            console.print(f"[cyan]Fetching content for:[/cyan] {identifier}\n")
            result = fetch_document(identifier)
            console.print(f"[green]✓ Fetched:[/green] {result['title']}")
            console.print(f"  Document ID: [cyan]{result['document_id']}[/cyan]")
            console.print(f"  Content: {result['content_length']} characters")
            console.print(f"  Status: [green]{result['status']}[/green]")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise click.Abort()
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            console.print(f"\n[yellow]Document marked as ERROR status[/yellow]")
            raise click.Abort()
        return

    # Batch mode
    if not (url_prefix or url_contains or fetch_all):
        console.print("[red]Error:[/red] Provide either:")
        console.print("  - An identifier: [cyan]kurt ingest fetch <doc-id>[/cyan]")
        console.print("  - Batch filters: [cyan]kurt ingest fetch --url-prefix <url>[/cyan]")
        console.print("  - Fetch all: [cyan]kurt ingest fetch --all[/cyan]")
        raise click.Abort()

    try:
        # Build query
        session = get_session()
        stmt = select(Document).where(Document.ingestion_status == IngestionStatus[status])

        if url_prefix:
            stmt = stmt.where(Document.source_url.startswith(url_prefix))
        if url_contains:
            stmt = stmt.where(Document.source_url.contains(url_contains))

        docs = session.exec(stmt).all()

        if not docs:
            filter_desc = url_prefix or url_contains or f"all {status}"
            console.print(f"[yellow]No {status} documents found for:[/yellow] {filter_desc}")
            return

        doc_ids = [str(doc.id) for doc in docs]
        console.print(f"[cyan]Fetching {len(doc_ids)} documents with {max_concurrent} parallel downloads...[/cyan]\n")

        # Fetch in parallel
        results = fetch_documents_batch(doc_ids, max_concurrent=max_concurrent)

        # Summary
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        console.print(f"\n[green]✓ Success:[/green] {len(successful)}/{len(results)} documents")
        if failed:
            console.print(f"[red]✗ Failed:[/red] {len(failed)} documents")
            for r in failed[:5]:  # Show first 5 errors
                console.print(f"  [dim]{r['document_id']}: {r['error']}[/dim]")
            if len(failed) > 5:
                console.print(f"  [dim]... and {len(failed) - 5} more[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

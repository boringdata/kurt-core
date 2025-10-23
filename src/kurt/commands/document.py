"""Document management CLI commands."""

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def document():
    """Manage documents."""
    pass


@document.command("list")
@click.option(
    "--status",
    type=click.Choice(["NOT_FETCHED", "FETCHED", "ERROR"], case_sensitive=False),
    help="Filter by ingestion status",
)
@click.option(
    "--url-prefix",
    type=str,
    help="Filter by URL prefix (e.g., https://example.com)",
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
def list_documents_cmd(
    status: str,
    url_prefix: str,
    url_contains: str,
    limit: int,
    offset: int,
    format: str,
):
    """
    List all documents with optional URL filtering.

    Examples:
        kurt document list
        kurt document list --status FETCHED
        kurt document list --url-prefix https://example.com
        kurt document list --url-contains blog
        kurt document list --url-prefix https://example.com --url-contains article
        kurt document list --limit 10
        kurt document list --format json
    """
    from kurt.document import list_documents
    from kurt.models.models import IngestionStatus

    try:
        # Convert status string to enum if provided
        status_filter = None
        if status:
            status_filter = IngestionStatus(status)

        docs = list_documents(
            status=status_filter,
            url_prefix=url_prefix,
            url_contains=url_contains,
            limit=limit,
            offset=offset,
        )

        if not docs:
            console.print("[yellow]No documents found[/yellow]")
            return

        if format == "json":
            import json

            print(json.dumps(docs, indent=2, default=str))
        else:
            # Create table
            table = Table(title=f"Documents ({len(docs)} shown)")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Title", style="white")
            table.add_column("Status", style="green")
            table.add_column("URL", style="dim")

            for doc in docs:
                # Truncate title and URL for display
                title = (doc.title or "Untitled")[:50] + "..." if doc.title and len(doc.title) > 50 else (doc.title or "Untitled")
                url = doc.source_url[:40] + "..." if doc.source_url and len(doc.source_url) > 40 else doc.source_url

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
                    url or "N/A",
                )

            console.print(table)

            # Show tip for getting full details
            console.print("\n[dim]Tip: Use [cyan]kurt document get <id>[/cyan] for full details[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@document.command("get")
@click.argument("document_id")
@click.option(
    "--format",
    type=click.Choice(["pretty", "json"], case_sensitive=False),
    default="pretty",
    help="Output format",
)
def get_document_cmd(document_id: str, format: str):
    """
    Get document details by ID.

    Examples:
        kurt document get 550e8400-e29b-41d4-a716-446655440000
        kurt document get 550e8400 --format json
    """
    from kurt.document import get_document

    try:
        doc = get_document(document_id)

        if format == "json":
            import json

            print(json.dumps(doc, indent=2, default=str))
        else:
            # Pretty print document details
            console.print(f"\n[bold cyan]Document Details[/bold cyan]")
            console.print(f"[dim]{'─' * 60}[/dim]")

            console.print(f"[bold]ID:[/bold] {doc.id}")
            console.print(f"[bold]Title:[/bold] {doc.title or 'Untitled'}")
            console.print(f"[bold]Status:[/bold] {doc.ingestion_status.value}")
            console.print(f"[bold]Source Type:[/bold] {doc.source_type.value}")
            console.print(f"[bold]Source URL:[/bold] {doc.source_url or 'N/A'}")

            if doc.description:
                console.print(f"\n[bold]Description:[/bold]")
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


@document.command("delete")
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
    Delete document by ID.

    Examples:
        kurt document delete 550e8400-e29b-41d4-a716-446655440000
        kurt document delete 550e8400 --delete-content
        kurt document delete 550e8400 --yes
    """
    from kurt.document import delete_document, get_document

    try:
        # Get document first to show what will be deleted
        doc = get_document(document_id)

        # Show what will be deleted
        console.print(f"\n[yellow]About to delete:[/yellow]")
        console.print(f"  ID: [cyan]{doc.id}[/cyan]")
        console.print(f"  Title: {doc.title or 'Untitled'}")
        console.print(f"  URL: {doc.source_url or 'N/A'}")

        if delete_content:
            console.print(f"  [red]Content file will also be deleted[/red]")

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
                console.print(f"  [green]✓[/green] Content file deleted")
            else:
                console.print(f"  [yellow]Content file not found or not deleted[/yellow]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@document.command("stats")
def stats_cmd():
    """
    Show document statistics.

    Example:
        kurt document stats
    """
    from kurt.document import get_document_stats

    try:
        stats = get_document_stats()

        console.print("\n[bold cyan]Document Statistics[/bold cyan]")
        console.print(f"[dim]{'─' * 40}[/dim]")
        console.print(f"Total Documents:     [bold]{stats['total']}[/bold]")
        console.print(f"  Not Fetched:       [yellow]{stats['not_fetched']}[/yellow]")
        console.print(f"  Fetched:           [green]{stats['fetched']}[/green]")
        console.print(f"  Error:             [red]{stats['error']}[/red]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

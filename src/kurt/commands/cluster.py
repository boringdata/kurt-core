"""Topic clustering CLI commands."""

import logging

import click
from rich.console import Console
from rich.table import Table

from kurt.clustering import compute_topic_clusters

console = Console()
logger = logging.getLogger(__name__)


# ============================================================================
# CLI Commands
# ============================================================================


@click.group()
def cluster():
    """Manage topic clusters."""
    pass


@cluster.command("compute")
@click.option(
    "--url-prefix",
    type=str,
    help="Compute clusters from documents matching URL prefix (e.g., https://example.com/blog/)",
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
def compute_clusters_command(
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
        kurt cluster compute --url-prefix https://example.com/blog/

        # Compute clusters from tutorial documents
        kurt cluster compute --url-contains tutorial

        # Output as JSON
        kurt cluster compute --url-prefix https://example.com --format json
    """
    try:
        if not url_prefix and not url_contains:
            console.print("[red]Error: Provide either --url-prefix or --url-contains[/red]")
            raise click.Abort()

        console.print("[bold]Computing topic clusters...[/bold]\n")

        # Run clustering
        result = compute_topic_clusters(
            url_prefix=url_prefix,
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
            console.print(f"[green]✓[/green] Created {result['edges_created']} document-cluster links\n")

            table = Table(title=f"Topic Clusters ({len(result['clusters'])} total)")
            table.add_column("Name", style="cyan", no_wrap=False)
            table.add_column("Description", style="white", no_wrap=False)
            table.add_column("Examples", style="dim", no_wrap=False)

            for cluster in result['clusters']:
                example_urls_str = "\n".join(cluster['example_urls'][:3])
                table.add_row(
                    cluster['name'],
                    cluster['description'],
                    example_urls_str,
                )

            console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception("Failed to compute clusters")
        raise click.Abort()


@cluster.command("get-from-url")
@click.option(
    "--url-prefix",
    type=str,
    help="Get documents matching URL prefix (e.g., https://example.com/blog/)",
)
@click.option(
    "--url-contains",
    type=str,
    help="Get documents where URL contains substring (e.g., tutorial)",
)
@click.option(
    "--format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format",
)
def get_from_url(
    url_prefix: str,
    url_contains: str,
    format: str,
):
    """
    Get documents by URL pattern.

    Examples:
        # Get all documents from a URL prefix
        kurt cluster get-from-url --url-prefix https://example.com/blog/

        # Get documents containing "tutorial" in URL
        kurt cluster get-from-url --url-contains tutorial

        # Output as JSON
        kurt cluster get-from-url --url-prefix https://example.com --format json
    """
    from kurt.document import list_documents
    from kurt.models.models import IngestionStatus

    try:
        if not url_prefix and not url_contains:
            console.print("[red]Error: Provide either --url-prefix or --url-contains[/red]")
            raise click.Abort()

        # Get matching documents
        docs = list_documents(
            status=IngestionStatus.FETCHED,
            url_prefix=url_prefix,
            url_contains=url_contains,
            limit=None,
        )

        if not docs:
            console.print("[yellow]No documents found matching criteria[/yellow]")
            return

        # Display results
        if format == "json":
            import json

            output = []
            for doc in docs:
                doc_data = {
                    "id": str(doc.id),
                    "title": doc.title,
                    "url": doc.source_url,
                    "status": doc.ingestion_status.value,
                }
                output.append(doc_data)

            console.print(json.dumps(output, indent=2))

        else:
            # Table format
            table = Table(title=f"Documents matching URL pattern ({len(docs)} found)")
            table.add_column("ID", style="cyan")
            table.add_column("Title", style="white")
            table.add_column("URL", style="blue")

            for doc in docs:
                table.add_row(
                    str(doc.id)[:8],
                    doc.title or "(no title)",
                    doc.source_url or "",
                )

            console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@cluster.command("list")
@click.option(
    "--format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format",
)
def list_clusters(format: str):
    """
    List all topic clusters.

    Examples:
        kurt cluster list
        kurt cluster list --format json
    """
    from kurt.database import get_session
    from kurt.models.models import TopicCluster
    from sqlmodel import select

    try:
        session = get_session()
        stmt = select(TopicCluster)
        clusters = session.exec(stmt).all()

        if not clusters:
            console.print("[yellow]No clusters found[/yellow]")
            return

        if format == "json":
            import json

            output = [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "description": c.description,
                    "created_at": c.created_at.isoformat(),
                }
                for c in clusters
            ]
            console.print(json.dumps(output, indent=2))

        else:
            table = Table(title=f"Topic Clusters ({len(clusters)} total)")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("Description", style="dim")
            table.add_column("Created", style="blue")

            for c in clusters:
                table.add_row(
                    str(c.id)[:8],
                    c.name,
                    c.description or "(no description)",
                    c.created_at.strftime("%Y-%m-%d %H:%M"),
                )

            console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()

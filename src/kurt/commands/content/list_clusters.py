"""List-clusters command - List all topic clusters."""

import logging

import click
from rich.console import Console
from rich.table import Table

console = Console()
logger = logging.getLogger(__name__)


@click.command("list-clusters")
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
    from kurt.content.document import list_clusters

    try:
        clusters = list_clusters()

        if not clusters:
            console.print("[yellow]No clusters found[/yellow]")
            console.print(
                "[dim]Tip: Run [cyan]kurt content cluster[/cyan] to create topic clusters[/dim]"
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
                '[dim]💡 Tip: Use [cyan]kurt content fetch --in-cluster "ClusterName"[/cyan] to fetch documents from a cluster[/dim]'
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Failed to list clusters")
        raise click.Abort()

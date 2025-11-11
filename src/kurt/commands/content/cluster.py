"""Cluster-urls command - organize documents into topics."""

import logging

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

console = Console()
logger = logging.getLogger(__name__)


@click.command("cluster-urls")
@click.option(
    "--include",
    "include_pattern",
    type=str,
    help="Cluster specific URL/path pattern (glob, filter before clustering)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Ignore existing clusters and create fresh (default: refine existing clusters)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format for AI agents",
)
def cluster_urls_cmd(
    include_pattern: str,
    force: bool,
    output_format: str,
):
    """
    Organize documents into topic clusters and classify content types.

    \b
    What it does:
    - Groups documents by topic (using URLs only, no content needed)
    - Classifies content types (tutorial, guide, blog, etc.)
    - Works on ANY status: NOT_FETCHED, FETCHED, or ERROR
    - Single LLM call for efficiency

    \b
    Incremental clustering (default):
    - Refines existing clusters intelligently
    - Keeps/refines valid clusters
    - Splits large clusters or merges similar ones
    - Adds clusters for new content
    - Removes outdated clusters
    Use --force to ignore existing clusters and start fresh.

    \b
    Workflow: map → cluster-urls → fetch --in-cluster "ClusterName"

    \b
    Examples:
        # Refine existing clusters + classify content types
        kurt cluster-urls

        # Ignore existing clusters, create fresh
        kurt cluster-urls --force

        # Cluster specific URL pattern
        kurt cluster-urls --include "*/docs/*"

        # JSON output for AI agents
        kurt cluster-urls --format json
    """
    from kurt.content.cluster import compute_topic_clusters

    try:
        # Check for existing clusters first
        from kurt.content.cluster import get_existing_clusters_summary
        from kurt.content.document import list_content

        # Get document count
        doc_count = len(list_content(include_pattern=include_pattern, limit=None))

        # Get existing clusters summary
        clusters_summary = get_existing_clusters_summary()
        existing_cluster_count = clusters_summary["count"]
        existing_clusters = clusters_summary["clusters"]

        if existing_cluster_count > 0 and not force:
            console.print(
                f"[bold cyan]ℹ[/bold cyan] Found {existing_cluster_count} existing clusters for {doc_count} documents - will refine and update them\n"
            )
            # Show existing cluster names
            if existing_cluster_count <= 10:
                console.print("[dim]  Existing clusters:[/dim]")
                for cluster in existing_clusters[:10]:
                    console.print(f"[dim]    • {cluster.name}[/dim]")
            else:
                console.print(
                    f"[dim]  Existing clusters: {', '.join([c.name for c in existing_clusters[:5]])} and {existing_cluster_count - 5} more...[/dim]"
                )
            console.print()
            console.print(
                "[dim]  (Use --force to ignore existing clusters and create fresh)[/dim]\n"
            )
        elif force and existing_cluster_count > 0:
            console.print(
                f"[bold yellow]⚡[/bold yellow] Force mode: ignoring {existing_cluster_count} existing clusters, creating fresh for {doc_count} documents\n"
            )
        elif doc_count > 0:
            console.print(
                f"[bold cyan]ℹ[/bold cyan] No existing clusters - creating fresh for {doc_count} documents\n"
            )

        console.print("[bold]Computing topic clusters and classifying content types...[/bold]")

        # Warn if large batch (>500 docs) - guardrail
        if doc_count > 500:
            console.print(
                f"\n[yellow]⚠ Large dataset:[/yellow] Processing {doc_count} documents in batches of 200"
            )
            console.print(f"[dim]  Estimated time: ~{(doc_count // 200 + 1) * 30} seconds[/dim]")
            console.print(
                f"[dim]  This will make {(doc_count // 200 + 1)} LLM calls (incremental refinement)[/dim]\n"
            )
        elif doc_count > 200:
            console.print(f"\n[cyan]ℹ[/cyan] Processing {doc_count} documents in batches of 200\n")
        else:
            console.print()  # Just add spacing

        # Run clustering with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task("Starting clustering...", total=None)

            def progress_callback(message):
                progress.update(task_id, description=message)

            # Run clustering with glob pattern (or None to cluster ALL documents)
            result = compute_topic_clusters(
                include_pattern=include_pattern,
                force=force,
                progress_callback=progress_callback,
            )

            progress.update(task_id, description="Clustering complete", completed=1, total=1)

        console.print()  # Add spacing after progress bar

        # Display results
        if output_format == "json":
            import json

            # Format for AI agents
            output = {
                "clusters": result["clusters"],
                "total_docs": result["total_pages"],
                "edges_created": result["edges_created"],
                "classifications": result["classifications"],
            }

            console.print(json.dumps(output, indent=2))

        else:
            # Table format
            console.print(f"[green]✓[/green] Analyzed {result['total_pages']} documents")

            # Show refinement info if applicable
            if result["refined"]:
                console.print(
                    f"[green]✓[/green] Refined {result['existing_clusters_count']} existing clusters → {len(result['clusters'])} clusters"
                )
            else:
                console.print(f"[green]✓[/green] Created {len(result['clusters'])} clusters")

            console.print(
                f"[green]✓[/green] Created {result['edges_created']} document-cluster links"
            )
            console.print(
                f"[green]✓[/green] Classified {result['classifications']['classified']} documents\n"
            )

            # Show classification breakdown
            if result["classifications"]["content_types"]:
                console.print("[dim]Content types:[/dim]")
                for content_type, count in sorted(
                    result["classifications"]["content_types"].items(),
                    key=lambda x: x[1],
                    reverse=True,
                ):
                    console.print(f"  {content_type}: {count}")
                console.print()

            table = Table(title=f"Topic Clusters ({len(result['clusters'])} total)")
            table.add_column("Cluster", style="cyan bold", no_wrap=False)
            table.add_column("Doc Count", style="green", justify="right")
            table.add_column("Sample URLs", style="dim", no_wrap=False)

            # Get doc counts per cluster from service
            from kurt.content.cluster import get_cluster_document_counts

            cluster_names = [cluster["name"] for cluster in result["clusters"]]
            doc_counts = get_cluster_document_counts(cluster_names)

            for cluster in result["clusters"]:
                doc_count = doc_counts.get(cluster["name"], 0)

                example_urls_str = "\n".join(cluster["example_urls"][:2])
                table.add_row(
                    f"{cluster['name']}\n{cluster['description']}",
                    str(doc_count),
                    example_urls_str,
                )

            console.print(table)

            # Show tip for next step
            console.print(
                '\n[dim]💡 Next: Use [cyan]kurt fetch --in-cluster "ClusterName"[/cyan] to fetch documents from a specific cluster[/dim]'
            )

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception("Failed to compute clusters")
        raise click.Abort()

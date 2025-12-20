"""Cluster-urls command - organize documents into topics."""

import asyncio
import logging

import click
from rich.console import Console
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command
from kurt.commands.content._shared_options import add_filter_options, add_output_options

console = Console()
logger = logging.getLogger(__name__)


@click.command("cluster-urls")
@track_command
@add_filter_options(exclude=False, status=False, content_type=False, cluster=False)
@click.option(
    "--force",
    is_flag=True,
    help="Ignore existing clusters and create fresh (default: refine existing clusters)",
)
@add_output_options(table_format=True)
def cluster_urls_cmd(
    include_pattern: str,
    ids: str,
    limit: int,
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
    - Uses LLM for intelligent clustering

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
        kurt content cluster-urls

        # Ignore existing clusters, create fresh
        kurt content cluster-urls --force

        # Cluster specific URL pattern
        kurt content cluster-urls --include "*/docs/*"

        # JSON output for AI agents
        kurt content cluster-urls --format json
    """
    from kurt.core import run_pipeline_workflow
    from kurt.utils.filtering import DocumentFilters

    try:
        # Build filters
        filters = DocumentFilters(
            ids=ids,
            include_pattern=include_pattern,
            limit=limit,
        )

        # Build config for the model
        config = {"force_fresh": force}

        console.print("[bold]Computing topic clusters and classifying content types...[/bold]\n")

        # Run the pipeline
        result = asyncio.run(
            run_pipeline_workflow(
                target="staging.topic_clustering",
                filters=filters,
                config=config,
            )
        )

        # Display results
        if output_format == "json":
            import json

            console.print(json.dumps(result, indent=2, default=str))
        else:
            _display_result(result)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception("Failed to compute clusters")
        raise click.Abort()


def _display_result(result: dict) -> None:
    """Display clustering results in table format."""
    docs_processed = result.get("documents_processed", 0)
    clusters_discovered = result.get("clusters_discovered", 0)
    docs_classified = result.get("documents_classified", 0)
    docs_assigned = result.get("documents_assigned", 0)

    console.print(f"[green]✓[/green] Analyzed {docs_processed} documents")
    console.print(f"[green]✓[/green] Discovered {clusters_discovered} clusters")
    console.print(f"[green]✓[/green] Classified {docs_classified} documents")
    console.print(f"[green]✓[/green] Assigned {docs_assigned} documents to clusters\n")

    # Show cluster summary from staging table
    _show_cluster_summary()

    # Show tip for next step
    console.print(
        '\n[dim]Tip: Use [cyan]kurt content fetch --in-cluster "ClusterName"[/cyan] to fetch documents from a specific cluster[/dim]'
    )


def _show_cluster_summary() -> None:
    """Show cluster summary from staging_topic_clustering table."""
    from kurt.db.database import get_session

    session = get_session()

    try:
        # Get cluster counts from staging table
        sql = """
            SELECT
                cluster_name,
                cluster_description,
                COUNT(*) as doc_count
            FROM staging_topic_clustering
            WHERE cluster_name IS NOT NULL
            GROUP BY cluster_name, cluster_description
            ORDER BY doc_count DESC
        """
        result = session.execute(sql)
        rows = result.fetchall()

        if not rows:
            console.print("[dim]No clusters found in staging table[/dim]")
            return

        table = Table(title=f"Topic Clusters ({len(rows)} total)")
        table.add_column("Cluster", style="cyan bold", no_wrap=False)
        table.add_column("Doc Count", style="green", justify="right")

        for row in rows:
            cluster_name, cluster_desc, doc_count = row
            display_text = f"{cluster_name}"
            if cluster_desc:
                display_text += f"\n{cluster_desc}"
            table.add_row(display_text, str(doc_count))

        console.print(table)

    except Exception as e:
        logger.debug(f"Could not query staging table: {e}")
        console.print("[dim]Cluster summary not available[/dim]")
    finally:
        session.close()

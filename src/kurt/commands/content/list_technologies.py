"""List-technologies command - List all indexed technologies from metadata and knowledge graph."""

import json
import logging

import click
from rich.console import Console
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command

console = Console()
logger = logging.getLogger(__name__)


@click.command("list-technologies")
@track_command
@click.option(
    "--min-docs",
    type=int,
    default=1,
    help="Minimum number of documents a technology must appear in",
)
@click.option(
    "--include",
    "include_pattern",
    type=str,
    help="Filter to documents matching glob pattern (e.g., '*/docs/*')",
)
@click.option(
    "--source",
    type=click.Choice(["metadata", "graph", "both"], case_sensitive=False),
    default="both",
    help="Data source: metadata (fast), graph (comprehensive), or both (default)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format",
)
def list_technologies_cmd(min_docs: int, include_pattern: str, source: str, output_format: str):
    """
    List all unique technologies from indexed documents with document counts.

    Technologies are aggregated from two sources:
    - Document metadata (tools_technologies field) - fast
    - Knowledge graph entities (Technology/Tool/Product types) - comprehensive

    Examples:
        kurt content list-technologies
        kurt content list-technologies --min-docs 5
        kurt content list-technologies --include "*/docs/*"
        kurt content list-technologies --source graph
        kurt content list-technologies --format json
    """
    from kurt.content.filtering import list_technologies

    try:
        technologies = list_technologies(
            min_docs=min_docs,
            include_pattern=include_pattern,
            source=source,
        )

        if not technologies:
            console.print("[yellow]No technologies found[/yellow]")
            if source == "metadata":
                console.print(
                    "[dim]Tip: Run [cyan]kurt content index[/cyan] to extract technologies from fetched documents[/dim]"
                )
            elif source == "graph":
                console.print(
                    "[dim]Tip: Knowledge graph is empty. Run [cyan]kurt content index[/cyan] to populate it[/dim]"
                )
            else:
                console.print(
                    "[dim]Tip: Run [cyan]kurt content index[/cyan] to extract technologies and build knowledge graph[/dim]"
                )
            return

        # Output formatting
        if output_format == "json":
            print(json.dumps(technologies, indent=2))
        else:
            # Table format
            title_parts = [f"Indexed Technologies ({len(technologies)} total)"]
            if include_pattern:
                title_parts.append(f" - Filtered: {include_pattern}")
            if min_docs > 1:
                title_parts.append(f" - Min {min_docs} docs")
            title_parts.append(f" - Source: {source}")

            table = Table(title="".join(title_parts))
            table.add_column("Technology", style="cyan bold", no_wrap=False)
            table.add_column("Documents", style="green", justify="right", width=10)
            table.add_column("Source", style="dim", width=10)

            for tech_info in technologies:
                table.add_row(
                    tech_info["technology"],
                    str(tech_info["doc_count"]),
                    tech_info["source"],
                )

            console.print(table)

            # Show tips
            console.print(
                '\n[dim]💡 Tip: Use [cyan]kurt content search "TechName"[/cyan] to search for technology mentions[/dim]'
            )
            console.print(
                "[dim]💡 Tip: Use [cyan]--source graph[/cyan] to see resolved/canonical technology names[/dim]"
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Failed to list technologies")
        raise click.Abort()

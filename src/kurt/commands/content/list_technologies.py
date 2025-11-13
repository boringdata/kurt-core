"""List-technologies command - List all indexed technologies."""

import logging

import click
from rich.console import Console
from rich.table import Table

console = Console()
logger = logging.getLogger(__name__)


@click.command("list-technologies")
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
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format",
)
def list_technologies_cmd(min_docs: int, include_pattern: str, output_format: str):
    """
    List all unique technologies from indexed documents with document counts.

    Examples:
        kurt content list-technologies
        kurt content list-technologies --min-docs 5
        kurt content list-technologies --include "*/docs/*"
        kurt content list-technologies --format json
    """
    from kurt.content.document import list_indexed_technologies

    try:
        technologies = list_indexed_technologies(
            min_docs=min_docs,
            include_pattern=include_pattern,
        )

        if not technologies:
            console.print("[yellow]No technologies found[/yellow]")
            console.print(
                "[dim]Tip: Run [cyan]kurt content index --all[/cyan] to extract technologies from fetched documents[/dim]"
            )
            return

        # Output formatting
        if output_format == "json":
            import json

            print(json.dumps(technologies, indent=2))
        else:
            # Table format
            title_parts = [f"Indexed Technologies ({len(technologies)} total)"]
            if include_pattern:
                title_parts.append(f" - Filtered: {include_pattern}")
            if min_docs > 1:
                title_parts.append(f" - Min {min_docs} docs")

            table = Table(title="".join(title_parts))
            table.add_column("Technology", style="cyan bold", no_wrap=False)
            table.add_column("Documents", style="green", justify="right")

            for tech_info in technologies:
                table.add_row(
                    tech_info["technology"],
                    str(tech_info["doc_count"]),
                )

            console.print(table)

            # Show tips
            console.print(
                '\n[dim]💡 Tip: Use [cyan]kurt content list --with-technology "TechName"[/cyan] to see documents using a technology[/dim]'
            )
            console.print(
                '[dim]💡 Tip: Use [cyan]kurt content search "TechName"[/cyan] to search for technology mentions[/dim]'
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Failed to list technologies")
        raise click.Abort()

"""List-topics command - List all indexed topics from metadata and knowledge graph."""

import json
import logging

import click
from rich.console import Console
from rich.table import Table

console = Console()
logger = logging.getLogger(__name__)


@click.command("list-topics")
@click.option(
    "--min-docs",
    type=int,
    default=1,
    help="Minimum number of documents a topic must appear in",
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
def list_topics_cmd(min_docs: int, include_pattern: str, source: str, output_format: str):
    """
    List all unique topics from indexed documents with document counts.

    Topics are aggregated from two sources:
    - Document metadata (primary_topics field) - fast
    - Knowledge graph entities (entity_type='Topic') - comprehensive

    Examples:
        kurt content list-topics
        kurt content list-topics --min-docs 5
        kurt content list-topics --include "*/docs/*"
        kurt content list-topics --source graph
        kurt content list-topics --format json
    """
    from kurt.content.filtering import list_topics

    try:
        topics = list_topics(
            min_docs=min_docs,
            include_pattern=include_pattern,
            source=source,
        )

        if not topics:
            console.print("[yellow]No topics found[/yellow]")
            if source == "metadata":
                console.print(
                    "[dim]Tip: Run [cyan]kurt content index[/cyan] to extract topics from fetched documents[/dim]"
                )
            elif source == "graph":
                console.print(
                    "[dim]Tip: Knowledge graph is empty. Run [cyan]kurt content index[/cyan] to populate it[/dim]"
                )
            else:
                console.print(
                    "[dim]Tip: Run [cyan]kurt content index[/cyan] to extract topics and build knowledge graph[/dim]"
                )
            return

        # Output formatting
        if output_format == "json":
            print(json.dumps(topics, indent=2))
        else:
            # Table format
            title_parts = [f"Indexed Topics ({len(topics)} total)"]
            if include_pattern:
                title_parts.append(f" - Filtered: {include_pattern}")
            if min_docs > 1:
                title_parts.append(f" - Min {min_docs} docs")
            title_parts.append(f" - Source: {source}")

            table = Table(title="".join(title_parts))
            table.add_column("Topic", style="cyan bold", no_wrap=False)
            table.add_column("Documents", style="green", justify="right", width=10)
            table.add_column("Source", style="dim", width=10)

            for topic_info in topics:
                table.add_row(
                    topic_info["topic"],
                    str(topic_info["doc_count"]),
                    topic_info["source"],
                )

            console.print(table)

            # Show tips
            console.print(
                '\n[dim]💡 Tip: Use [cyan]kurt content list --in-cluster "TopicName"[/cyan] to see documents in a topic cluster[/dim]'
            )
            console.print(
                '[dim]💡 Tip: Use [cyan]kurt content search "TopicName"[/cyan] to search for topic mentions[/dim]'
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Failed to list topics")
        raise click.Abort()

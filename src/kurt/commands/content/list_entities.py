"""List-entities command - List all indexed entities from knowledge graph."""

import json
import logging

import click
from rich.console import Console
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command
from kurt.db.models import EntityType

console = Console()
logger = logging.getLogger(__name__)


@click.command("list-entities")
@track_command
@click.argument(
    "entity_type",
    type=click.Choice(
        [e.value.lower() for e in EntityType] + ["all"],
        case_sensitive=False,
    ),
    default="all",
    required=False,
)
@click.option(
    "--min-docs",
    type=int,
    default=1,
    help="Minimum number of documents an entity must appear in",
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
def list_entities_cmd(entity_type: str, min_docs: int, include_pattern: str, output_format: str):
    """
    List all unique entities from indexed documents with document counts.

    Entities are extracted from the knowledge graph.

    ENTITY_TYPE can be: topic, technology, product, feature, company, integration, or all

    Examples:
        kurt content list-entities topic
        kurt content list-entities technology --min-docs 5
        kurt content list-entities all --include "*/docs/*"
        kurt content list-entities product --format json
    """
    from kurt.db.graph_queries import list_entities_by_type

    try:
        # Normalize entity_type to EntityType enum value format (Title case)
        if entity_type.lower() == "all":
            normalized_entity_type = None
        else:
            normalized_entity_type = entity_type.capitalize()

        entities = list_entities_by_type(
            entity_type=normalized_entity_type,
            min_docs=min_docs,
            include_pattern=include_pattern,
        )

        if not entities:
            console.print(f"[yellow]No {entity_type} entities found[/yellow]")
            console.print(
                "[dim]Tip: Run [cyan]kurt content index[/cyan] to extract entities and build knowledge graph[/dim]"
            )
            return

        # Output formatting
        if output_format == "json":
            print(json.dumps(entities, indent=2))
        else:
            # Table format
            title_parts = [f"Indexed {entity_type.capitalize()} Entities ({len(entities)} total)"]
            if include_pattern:
                title_parts.append(f" - Filtered: {include_pattern}")
            if min_docs > 1:
                title_parts.append(f" - Min {min_docs} docs")

            table = Table(title="".join(title_parts))
            table.add_column("Entity", style="cyan bold", no_wrap=False)

            # Add type column only if showing all entity types
            if entity_type.lower() == "all":
                table.add_column("Type", style="magenta", width=15)

            table.add_column("Documents", style="green", justify="right", width=10)

            for entity_info in entities:
                if entity_type.lower() == "all":
                    table.add_row(
                        entity_info["entity"],
                        entity_info["entity_type"],
                        str(entity_info["doc_count"]),
                    )
                else:
                    table.add_row(
                        entity_info["entity"],
                        str(entity_info["doc_count"]),
                    )

            console.print(table)

            # Show tips
            console.print(
                f'\n[dim]💡 Tip: Use [cyan]kurt content list --with-entity "{entity_type.capitalize()}:EntityName"[/cyan] to see documents mentioning an entity[/dim]'
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Failed to list entities")
        raise click.Abort()

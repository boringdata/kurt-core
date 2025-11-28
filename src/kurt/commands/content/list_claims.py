"""List-claims command - List all indexed claims from knowledge graph."""

import json
import logging

import click
from rich.console import Console
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command
from kurt.db.models import ClaimType

console = Console()
logger = logging.getLogger(__name__)


@click.command("list-claims")
@track_command
@click.argument(
    "claim_type",
    type=click.Choice(
        [e.value.lower() for e in ClaimType] + ["all"],
        case_sensitive=False,
    ),
    default="all",
    required=False,
)
@click.option(
    "--min-docs",
    type=int,
    default=1,
    help="Minimum number of documents a claim must appear in",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format",
)
@click.option(
    "--limit",
    type=int,
    default=100,
    help="Maximum number of claims to return",
)
def list_claims_cmd(claim_type: str, min_docs: int, output_format: str, limit: int):
    """
    List all unique claims from indexed documents with document counts.

    Claims are extracted from the knowledge graph during indexing.

    CLAIM_TYPE can be: factual, comparative, capability, performance, benefit, limitation, integration, other, or all

    Examples:
        kurt content list-claims factual
        kurt content list-claims capability --min-docs 2
        kurt content list-claims all --format json
        kurt content list-claims performance --limit 50
    """
    from kurt.db.graph_queries import list_claims_by_type

    try:
        # Normalize claim_type to ClaimType enum value format
        if claim_type.lower() == "all":
            normalized_claim_type = None
        else:
            normalized_claim_type = claim_type.lower()

        claims = list_claims_by_type(
            claim_type=normalized_claim_type,
            limit=limit,
        )

        # Filter by min_docs
        if min_docs > 1:
            claims = [c for c in claims if c.get("source_mentions", 0) >= min_docs]

        if not claims:
            console.print(f"[yellow]No {claim_type} claims found[/yellow]")
            console.print(
                "[dim]Tip: Run [cyan]kurt content index[/cyan] to extract claims and build knowledge graph[/dim]"
            )
            return

        # Output formatting
        if output_format == "json":
            print(json.dumps(claims, indent=2))
        else:
            # Table format
            title_parts = [f"Indexed {claim_type.capitalize()} Claims ({len(claims)} total)"]
            if min_docs > 1:
                title_parts.append(f" - Min {min_docs} docs")

            table = Table(title="".join(title_parts))
            table.add_column("Claim", style="cyan", no_wrap=False, max_width=60)

            # Add type column only if showing all claim types
            if claim_type.lower() == "all":
                table.add_column("Type", style="magenta", width=12)

            table.add_column("Documents", style="green", justify="right", width=10)
            table.add_column("Confidence", style="yellow", justify="right", width=10)

            for claim_info in claims:
                # Truncate long claims for display
                claim_text = claim_info.get("canonical_text") or claim_info.get("claim_text", "")
                if len(claim_text) > 57:
                    claim_text = claim_text[:57] + "..."

                confidence = claim_info.get("confidence_score", 0.0)
                confidence_str = f"{confidence:.2f}" if confidence else "-"

                if claim_type.lower() == "all":
                    table.add_row(
                        claim_text,
                        claim_info.get("claim_type", ""),
                        str(claim_info.get("source_mentions", 0)),
                        confidence_str,
                    )
                else:
                    table.add_row(
                        claim_text,
                        str(claim_info.get("source_mentions", 0)),
                        confidence_str,
                    )

            console.print(table)

            # Show claim type legend
            console.print("\n[dim]Claim Types:[/dim]")
            console.print(
                "[dim]  • factual: Objective statements (e.g., 'X has 99.9% uptime')[/dim]"
            )
            console.print(
                "[dim]  • comparative: Comparisons (e.g., 'X is faster than Y')[/dim]"
            )
            console.print(
                "[dim]  • capability: What something can do (e.g., 'supports 10k connections')[/dim]"
            )
            console.print(
                "[dim]  • performance: Performance metrics (e.g., 'reduces latency by 50%')[/dim]"
            )
            console.print(
                "[dim]  • benefit: Value propositions (e.g., 'saves engineering time')[/dim]"
            )
            console.print(
                "[dim]  • limitation: Constraints (e.g., 'requires minimum 8GB RAM')[/dim]"
            )
            console.print(
                "[dim]  • integration: Integration claims (e.g., 'works seamlessly with Z')[/dim]"
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Failed to list claims")
        raise click.Abort()

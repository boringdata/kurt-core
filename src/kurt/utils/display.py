"""Display formatting utilities for indexing pipeline.

This module contains step-specific formatting logic that transforms
raw data into display-ready format. The generic display layer
(_live_display.py) should only receive ready-to-display data.
"""

from rich import box
from rich.console import Console
from rich.table import Table


def format_claim_type(claim_type: str) -> str:
    """Format claim type for compact display.

    Args:
        claim_type: Raw claim type (e.g., "ClaimType.definition", "comparison")

    Returns:
        Shortened display string (e.g., "def", "comp")
    """
    return (
        claim_type.replace("ClaimType.", "")
        .replace("definition", "def")
        .replace("comparison", "comp")
        .replace("performance", "perf")
    )


def format_timestamp(timestamp) -> str:
    """Format timestamp for display.

    Args:
        timestamp: datetime string or datetime object

    Returns:
        Formatted string like "2024-01-15 12:30" or "-" if empty
    """
    if not timestamp:
        return "-"

    if isinstance(timestamp, str):
        return timestamp[:16].replace("T", " ")  # "2024-01-15 12:30"
    else:
        return timestamp.strftime("%Y-%m-%d %H:%M")


def format_claim_for_display(claim: dict) -> dict:
    """Format a claim dict for display.

    Transforms raw claim data into display-ready format.

    Args:
        claim: Raw claim dict with keys like 'statement', 'claim_type', 'created_at', etc.

    Returns:
        Display-ready dict with formatted values
    """
    entities_in_claim = claim.get("referenced_entities", [])

    return {
        "statement": claim["statement"],
        "entities": ", ".join(entities_in_claim) if entities_in_claim else "-",
        "type": format_claim_type(claim.get("claim_type", "")),
        "created": format_timestamp(claim.get("created_at")),
    }


def format_claims_for_display(claims: list[dict]) -> list[dict]:
    """Format a list of claims for display.

    Args:
        claims: List of raw claim dicts

    Returns:
        List of display-ready claim dicts
    """
    return [format_claim_for_display(claim) for claim in claims]


def build_claims_table(claims: list[dict]) -> Table:
    """Build a Rich Table for claims display.

    Args:
        claims: List of raw claim dicts

    Returns:
        Rich Table ready to print
    """
    table = Table(
        show_header=True,
        header_style="bold dim",
        box=box.SIMPLE,
        padding=(0, 1),
        expand=False,
    )
    table.add_column("Statement", style="", max_width=80)
    table.add_column("Entities", style="dim", max_width=25)
    table.add_column("Type", style="dim", max_width=10)
    table.add_column("Created", style="dim", max_width=12)

    formatted_claims = format_claims_for_display(claims)
    for claim in formatted_claims:
        table.add_row(claim["statement"], claim["entities"], claim["type"], claim["created"])

    return table


def build_entities_table(entities: list[dict], relationships: list[dict] = None) -> Table:
    """Build a Rich Table for entities with relationships display.

    Args:
        entities: List of entity dicts with 'name', 'type', 'confidence', 'mentions_in_doc'
        relationships: Optional list of relationship dicts

    Returns:
        Rich Table ready to print
    """
    # Group relationships by source entity
    relationships_by_entity = {}
    if relationships:
        for rel in relationships:
            source = rel["source_entity"]
            if source not in relationships_by_entity:
                relationships_by_entity[source] = []
            relationships_by_entity[source].append(rel)

    table = Table(
        show_header=True,
        header_style="bold dim",
        box=box.SIMPLE,
        padding=(0, 1),
        expand=False,
    )
    table.add_column("Entity", style="bold", max_width=25)
    table.add_column("Type", style="dim", max_width=12)
    table.add_column("Conf", style="dim", max_width=6)
    table.add_column("Mentions", style="dim", max_width=8)
    table.add_column("Relationship", style="dim", max_width=45)

    for entity in entities:
        entity_rels = relationships_by_entity.get(entity["name"], [])
        conf_str = f"{entity['confidence']:.2f}"
        mentions_str = str(entity["mentions_in_doc"])

        if entity_rels:
            # First row has entity info + first relationship
            first_rel = entity_rels[0]
            rel_str = f"→ {first_rel.get('relationship_type', 'related_to')} → {first_rel['target_entity']}"
            table.add_row(entity["name"], entity["type"], conf_str, mentions_str, rel_str)

            # Additional rows have empty entity columns (visual merge effect)
            for rel in entity_rels[1:5]:  # Show up to 5 relationships
                rel_str = f"→ {rel.get('relationship_type', 'related_to')} → {rel['target_entity']}"
                table.add_row("", "", "", "", rel_str)

            if len(entity_rels) > 5:
                table.add_row("", "", "", "", f"(+{len(entity_rels) - 5} more)")
        else:
            table.add_row(entity["name"], entity["type"], conf_str, mentions_str, "-")

    return table


def print_entity_resolution_tables(
    cleanup_stats: dict,
    rows: list,
    print_info_fn,
    print_table_fn,
):
    """Print verbose tables for entity resolution step.

    Args:
        cleanup_stats: Stats from cleanup_old_entities (with 'details' key)
        rows: List of EntityResolutionRow objects
        print_info_fn: Function to print info headers (e.g., print_info)
        print_table_fn: Function to print inline tables (e.g., print_inline_table)
    """
    # Table 1: Cleanup summary per document (if any cleanup happened)
    cleanup_details = cleanup_stats.get("details", [])
    cleanup_rows = []
    for detail in cleanup_details:
        if detail["before"]["entity_count"] > 0:
            doc_id_short = detail["document_id"][:8]
            cleanup_rows.append(
                {
                    "doc": doc_id_short,
                    "before": detail["before"]["entity_count"],
                    "existing": detail["kept"]["existing_count"],
                    "new": detail["kept"]["new_count"],
                    "removed": detail["removed"]["count"],
                }
            )

    if cleanup_rows:
        print_info_fn("Graph state per document:")
        print_table_fn(
            cleanup_rows,
            columns=["doc", "before", "existing", "new", "removed"],
            max_items=10,
            column_widths={"doc": 10, "before": 8, "existing": 10, "new": 8, "removed": 10},
        )

    # Table 2: Deleted entities (if any)
    deleted_entities = []
    for detail in cleanup_details:
        for entity_name in detail["removed"]["entity_names"]:
            deleted_entities.append(
                {
                    "entity": entity_name,
                    "doc": detail["document_id"][:8],
                }
            )

    if deleted_entities:
        print_info_fn("Entities removed:")
        print_table_fn(
            deleted_entities,
            columns=["entity", "doc"],
            max_items=15,
            column_widths={"entity": 40, "doc": 10},
        )

    # Table 3: Entity operations (created/linked/merged)
    if rows:
        entity_ops = [
            {
                "name": r.entity_name,
                "operation": r.operation,
                "canonical": r.canonical_name or "",
            }
            for r in rows
        ]
        print_info_fn("Entity operations:")
        print_table_fn(
            entity_ops,
            columns=["name", "operation", "canonical"],
            max_items=20,
            cli_command="kurt kg entities" if len(entity_ops) > 20 else None,
        )


def display_knowledge_graph(kg: dict, console: Console, title: str = "Knowledge Graph"):
    """Display knowledge graph in a consistent format.

    Args:
        kg: Knowledge graph data with stats, entities, and relationships
        console: Rich Console instance for output
        title: Title to display (default: "Knowledge Graph")
    """
    if not kg:
        return

    # Claims section (first)
    if kg.get("claims"):
        claim_count = len(kg["claims"])
        console.print(f"\n[bold cyan]Claims ({claim_count})[/bold cyan]")
        console.print(f"[dim]{'─' * 60}[/dim]")
        console.print(build_claims_table(kg["claims"]))

    # Entities & Relationships section
    entity_count = kg["stats"]["entity_count"]
    rel_count = kg["stats"]["relationship_count"]
    console.print(
        f"\n[bold cyan]Entities & Relationships ({entity_count} entities, {rel_count} relationships)[/bold cyan]"
    )
    console.print(f"[dim]{'─' * 60}[/dim]")

    if kg.get("entities"):
        console.print(build_entities_table(kg["entities"], kg.get("relationships")))

    # Summary line
    console.print()
    avg_conf = kg["stats"].get("avg_entity_confidence", 0)
    claim_count = kg["stats"].get("claim_count", 0)
    console.print(
        f"[dim]Summary: {entity_count} entities • {rel_count} relationships • "
        f"{claim_count} claims • Avg confidence: {avg_conf:.2f}[/dim]"
    )

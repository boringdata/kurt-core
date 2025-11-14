"""Get command - Get document metadata by ID."""

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command

console = Console()


@click.command("get")
@track_command
@click.argument("identifier")
@click.option(
    "--format",
    type=click.Choice(["pretty", "json"], case_sensitive=False),
    default="pretty",
    help="Output format",
)
def get_document_cmd(identifier: str, format: str):
    """
    Get document metadata by ID, URL, or file path (includes knowledge graph).

    IDENTIFIER can be a document ID, URL, or file path.

    Examples:
        kurt content get 550e8400-e29b-41d4-a716-446655440000
        kurt content get 550e8400 --format json
        kurt content get https://example.com/article
        kurt content get ./docs/article.md
    """
    from kurt.content.document import get_document
    from kurt.content.filtering import resolve_identifier_to_doc_id

    try:
        # Resolve identifier to document ID (supports partial UUIDs)
        doc_id = resolve_identifier_to_doc_id(identifier)

        doc = get_document(doc_id)

        # Get knowledge graph (always included)
        kg = None
        from kurt.content.indexing import get_document_knowledge_graph

        try:
            kg = get_document_knowledge_graph(doc_id)
        except Exception:
            # Silently skip if no KG data (document may not be indexed yet)
            pass

        if format == "json":
            import json

            # Convert SQLModel to dict
            output = doc.model_dump() if hasattr(doc, "model_dump") else dict(doc)
            if kg:
                output["knowledge_graph"] = kg
            print(json.dumps(output, indent=2, default=str))
        else:
            # Pretty print document details
            console.print("\n[bold cyan]Document Details[/bold cyan]")
            console.print(f"[dim]{'─' * 60}[/dim]")

            console.print(f"[bold]ID:[/bold] {doc.id}")
            console.print(f"[bold]Title:[/bold] {doc.title or 'Untitled'}")
            console.print(f"[bold]Status:[/bold] {doc.ingestion_status.value}")
            console.print(f"[bold]Source Type:[/bold] {doc.source_type.value}")
            console.print(f"[bold]Source URL:[/bold] {doc.source_url or 'N/A'}")

            if doc.description:
                console.print("\n[bold]Description:[/bold]")
                console.print(f"  {doc.description[:200]}...")

            if doc.author:
                console.print(f"\n[bold]Author(s):[/bold] {', '.join(doc.author)}")

            if doc.published_date:
                console.print(f"[bold]Published:[/bold] {doc.published_date}")

            if doc.content_hash:
                console.print(f"[bold]Content Hash:[/bold] {doc.content_hash[:16]}...")

            console.print(f"\n[bold]Content Path:[/bold] {doc.content_path or 'N/A'}")
            console.print(f"[bold]Created:[/bold] {doc.created_at}")
            console.print(f"[bold]Updated:[/bold] {doc.updated_at}")

            # Show knowledge graph if included
            if kg:
                from kurt.commands.content._live_display import display_knowledge_graph

                display_knowledge_graph(kg, console)

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

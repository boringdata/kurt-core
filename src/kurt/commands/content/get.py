"""Get command - Get document metadata by ID."""

import click
from rich.console import Console

console = Console()


@click.command("get")
@click.argument("document_id")
@click.option(
    "--format",
    type=click.Choice(["pretty", "json"], case_sensitive=False),
    default="pretty",
    help="Output format",
)
def get_document_cmd(document_id: str, format: str):
    """
    Get document metadata by ID.

    Examples:
        kurt content get 550e8400-e29b-41d4-a716-446655440000
        kurt content get 550e8400 --format json
    """
    from kurt.content.document import get_document

    try:
        doc = get_document(document_id)

        if format == "json":
            import json

            print(json.dumps(doc, indent=2, default=str))
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

            # Indexed metadata section
            if (
                doc.content_type
                or doc.primary_topics
                or doc.tools_technologies
                or doc.has_code_examples
                or doc.has_step_by_step_procedures
                or doc.has_narrative_structure
            ):
                console.print(f"\n[dim]{'─' * 60}[/dim]")
                console.print("[bold cyan]Indexed Metadata[/bold cyan]")

                if doc.content_type:
                    console.print(f"[bold]Content Type:[/bold] {doc.content_type.value}")

                if doc.primary_topics:
                    console.print(f"[bold]Topics:[/bold] {', '.join(doc.primary_topics)}")

                if doc.tools_technologies:
                    console.print(f"[bold]Technologies:[/bold] {', '.join(doc.tools_technologies)}")

                # Structural flags
                structural_flags = []
                if doc.has_code_examples:
                    structural_flags.append("code examples")
                if doc.has_step_by_step_procedures:
                    structural_flags.append("step-by-step procedures")
                if doc.has_narrative_structure:
                    structural_flags.append("narrative structure")

                if structural_flags:
                    console.print(f"[bold]Structure:[/bold] {', '.join(structural_flags)}")

                # Indexing metadata
                if doc.indexed_with_hash or doc.indexed_with_git_commit:
                    console.print("\n[dim]Indexing Info:[/dim]")
                    if doc.indexed_with_hash:
                        console.print(
                            f"  [dim]Indexed with content hash: {doc.indexed_with_hash[:16]}...[/dim]"
                        )
                    if doc.indexed_with_git_commit:
                        console.print(
                            f"  [dim]Indexed with git commit: {doc.indexed_with_git_commit[:8]}[/dim]"
                        )

            console.print(f"\n[dim]{'─' * 60}[/dim]")
            console.print(f"[bold]Content Path:[/bold] {doc.content_path or 'N/A'}")
            console.print(f"[bold]Created:[/bold] {doc.created_at}")
            console.print(f"[bold]Updated:[/bold] {doc.updated_at}")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

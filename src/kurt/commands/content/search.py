"""Search command - Search document content using vector similarity."""

import json

import click
from rich.console import Console
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command

console = Console()


@click.command("search")
@track_command
@click.argument("query", type=str)
@click.option(
    "--include",
    "include_pattern",
    type=str,
    help="Filter by URL/path pattern (glob matching source_url or content_path)",
)
@click.option(
    "--max-results",
    type=int,
    default=20,
    help="Maximum number of results to display (default: 20)",
)
@click.option(
    "--min-similarity",
    type=float,
    default=0.70,
    help="Minimum similarity threshold 0.0-1.0 (default: 0.70)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format (default: table)",
)
def search_cmd(
    query: str,
    include_pattern: str,
    max_results: int,
    min_similarity: float,
    output_format: str,
):
    """
    Search for semantically similar documents using vector embeddings.

    Uses document embeddings to find documents related to your query.
    This is semantic search - it finds documents by meaning, not just keywords.

    Examples:
        kurt content search "how models are trained"
        kurt content search "neural networks" --include "*/article/*"
        kurt content search "AI safety" --min-similarity 0.80
        kurt content search "authentication" --format json

    Note: This searches at the document level. For more granular search
    (specific facts or claims), we'll add claim-level search in the future.
    """
    from fnmatch import fnmatch

    from kurt.content.document import list_documents
    from kurt.content.embeddings import embedding_to_bytes, generate_embeddings
    from kurt.db.sqlite import SQLiteClient

    # Generate query embedding
    try:
        query_embedding_vector = generate_embeddings([query])[0]
        query_embedding_bytes = embedding_to_bytes(query_embedding_vector)
    except Exception as e:
        console.print(f"[red]Error generating embedding:[/red] {e}")
        raise click.Abort()

    # Search for similar documents using vector search
    client = SQLiteClient()
    try:
        results = client.search_similar_documents(
            query_embedding_bytes, limit=max_results, min_similarity=min_similarity
        )
    except Exception as e:
        console.print(f"[red]Error during vector search:[/red] {e}")
        console.print("[dim]Hint: Make sure vector tables are initialized with migrations[/dim]")
        raise click.Abort()

    if not results:
        console.print(f"[yellow]No similar documents found for:[/yellow] '{query}'")
        console.print(f"[dim]Try lowering --min-similarity (current: {min_similarity})[/dim]")
        return

    # Load document metadata and apply include filter
    all_docs = list_documents()
    doc_map = {str(d.id): d for d in all_docs}

    filtered_results = []
    for doc_id, similarity in results:
        doc = doc_map.get(doc_id)
        if not doc:
            continue

        # Apply include pattern filter
        if include_pattern:
            if not (
                (doc.source_url and fnmatch(doc.source_url, include_pattern))
                or (doc.content_path and fnmatch(str(doc.content_path), include_pattern))
            ):
                continue

        filtered_results.append((doc, similarity))

    if not filtered_results:
        console.print(f"[yellow]No documents match pattern:[/yellow] {include_pattern}")
        return

    # Output results
    if output_format == "json":
        output = {
            "query": query,
            "total_matches": len(filtered_results),
            "min_similarity": min_similarity,
            "results": [
                {
                    "document_id": str(doc.id),
                    "title": doc.title or "Untitled",
                    "source_url": doc.source_url or "N/A",
                    "content_path": doc.content_path or "N/A",
                    "content_type": doc.content_type or "N/A",
                    "similarity": similarity,
                }
                for doc, similarity in filtered_results
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        # Table format (default)
        console.print()
        console.print("[bold cyan]Semantic Search Results[/bold cyan]")
        console.print(f"[dim]Query: '{query}'[/dim]")
        if include_pattern:
            console.print(f"[dim]Pattern: {include_pattern}[/dim]")
        console.print(f"[dim]Found {len(filtered_results)} similar documents[/dim]")
        console.print()

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Similarity", style="yellow", width=10, justify="right")
        table.add_column("Title", style="bold")
        table.add_column("Type", style="cyan", width=12)
        table.add_column("ID", style="dim", width=12)

        for doc, similarity in filtered_results:
            table.add_row(
                f"{similarity:.1%}",
                doc.title[:60] + "..." if len(doc.title) > 60 else doc.title,
                doc.content_type or "N/A",
                str(doc.id)[:8] + "...",
            )

        console.print(table)
        console.print()


@click.command("links")
@click.argument("identifier", type=str)
@click.option(
    "--direction",
    type=click.Choice(["outbound", "inbound"], case_sensitive=False),
    default="outbound",
    help="Link direction: outbound (default) = links from doc, inbound = links to doc",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format",
)
def links_cmd(identifier: str, direction: str, output_format: str):
    """
    Show links from or to a document.

    Claude interprets anchor text to understand relationship types
    (prerequisites, related content, examples, references).

    Examples:
        kurt content links 550e8400                    # Show outbound links (default)
        kurt content links 550e8400 --direction inbound  # Show inbound links
        kurt content links 550e8400 --format json
    """
    from kurt.content.document import get_document
    from kurt.db.graph_queries import get_document_links

    try:
        # Resolve identifier to UUID
        doc = get_document(identifier)
        links = get_document_links(doc.id, direction=direction)

        if output_format == "json":
            print(json.dumps(links, indent=2))
        else:
            if not links:
                console.print(f"\n[yellow]No {direction} links found[/yellow]")
                return

            console.print(f"\n[bold cyan]{direction.capitalize()} Links[/bold cyan]")
            console.print(f"[dim]{'─' * 60}[/dim]\n")

            table = Table(show_header=True, header_style="bold magenta")

            if direction == "outbound":
                table.add_column("Target Title", style="cyan")
                table.add_column("Anchor Text", style="green")
                table.add_column("Target ID", style="dim", width=12)
            else:  # inbound
                table.add_column("Source Title", style="cyan")
                table.add_column("Anchor Text", style="green")
                table.add_column("Source ID", style="dim", width=12)

            for link in links:
                if direction == "outbound":
                    title = link["target_title"]
                    doc_id = link["target_id"][:8] + "..."
                else:  # inbound
                    title = link["source_title"]
                    doc_id = link["source_id"][:8] + "..."

                anchor = link["anchor_text"] or "[no text]"
                # Truncate long anchor text
                if len(anchor) > 50:
                    anchor = anchor[:47] + "..."

                table.add_row(title[:60], anchor, doc_id)

            console.print(table)
            console.print(f"\n[dim]Total: {len(links)} links[/dim]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

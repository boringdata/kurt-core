"""Retrieve command - Hybrid retrieval from knowledge graph and embeddings."""

import asyncio
import json

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command

console = Console()


@click.command("retrieve")
@track_command
@click.argument("query", type=str)
@click.option(
    "--mode",
    type=click.Choice(["rag", "cag"], case_sensitive=False),
    default="cag",
    help="Retrieval mode: cag (fast, entity-based) or rag (full pipeline)",
)
@click.option(
    "--type",
    "query_type",
    type=click.Choice(["hybrid", "graph", "semantic"], case_sensitive=False),
    default="hybrid",
    help="RAG retrieval type: hybrid (default), graph-only, or semantic-only",
)
@click.option(
    "--deep",
    is_flag=True,
    default=False,
    help="Enable deep mode for more thorough retrieval (RAG only)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["context", "json", "citations"], case_sensitive=False),
    default="context",
    help="Output format (default: context)",
)
@click.option(
    "--session-id",
    type=str,
    default=None,
    help="Session ID for multi-turn conversations",
)
@click.option(
    "--top-k",
    type=int,
    default=5,
    help="CAG: Number of entities to match (default: 5)",
)
@click.option(
    "--min-similarity",
    type=float,
    default=0.3,
    help="CAG: Minimum entity similarity threshold (default: 0.3)",
)
def retrieve_cmd(
    query: str,
    mode: str,
    query_type: str,
    deep: bool,
    output_format: str,
    session_id: str,
    top_k: int,
    min_similarity: float,
):
    """
    Retrieve context from the knowledge graph for a query.

    Two modes available:

    CAG (default): Fast, entity-based retrieval for agent sessions.
    - Single embedding call to match entities
    - SQL-only context loading
    - Optimized for agent bootstrap

    RAG: Full pipeline with multiple search strategies.
    - Query analysis + 5 parallel searches + RRF fusion
    - More thorough but slower

    Examples:
        kurt retrieve "What integrations does Segment support?"
        kurt retrieve "authentication flow" --mode rag --type semantic
        kurt retrieve "API rate limits" --format json
        kurt retrieve "pricing" --mode rag --deep
        kurt retrieve "Segment" --top-k 10 --min-similarity 0.4
    """
    console.print()
    console.print(f"[dim]Retrieving context for:[/dim] [bold]{query}[/bold]")

    if mode == "cag":
        # CAG mode: fast, entity-based retrieval using unified step
        from kurt.retrieval.cag import retrieve_cag

        console.print(f"[dim]Mode: CAG (top_k={top_k}, min_sim={min_similarity})[/dim]")
        console.print("[dim]Using unified retrieval.cag step[/dim]")
        console.print()

        try:
            result = asyncio.run(
                retrieve_cag(
                    query,
                    top_k_entities=top_k,
                    min_similarity=min_similarity,
                )
            )
        except Exception as e:
            console.print(f"[red]Error during CAG retrieval:[/red] {e}")
            raise click.Abort()

        # Output based on format
        if output_format == "json":
            output = {
                "query": query,
                "mode": "cag",
                "topics": result.topics,
                "matched_entities": result.matched_entities,
                "context_markdown": result.context_markdown,
                "token_estimate": result.token_estimate,
                "sources": result.sources,
                "telemetry": result.telemetry,
            }
            print(json.dumps(output, indent=2))

        elif output_format == "citations":
            if not result.sources:
                console.print("[yellow]No sources found[/yellow]")
                return

            console.print("[bold cyan]Sources[/bold cyan]")
            console.print()

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("#", style="yellow", width=4, justify="right")
            table.add_column("Title", style="bold")
            table.add_column("URL", style="dim")

            for i, src in enumerate(result.sources, 1):
                title = src.get("title", "Untitled")
                if len(title) > 50:
                    title = title[:47] + "..."
                url = src.get("url", "N/A")
                if len(url) > 40:
                    url = url[:37] + "..."
                table.add_row(str(i), title, url)

            console.print(table)
            console.print()
            console.print(f"[dim]Total: {len(result.sources)} sources[/dim]")

        else:  # context (default)
            console.print(
                Panel(
                    result.context_markdown,
                    title="[bold cyan]Agent Context (CAG)[/bold cyan]",
                    border_style="cyan",
                )
            )

            # Show stats
            console.print()
            console.print("[dim]Stats:[/dim]")
            console.print(f"  Topics: {', '.join(result.topics) if result.topics else 'None'}")
            console.print(f"  Matched entities: {', '.join(result.matched_entities[:5])}")
            console.print(f"  Token estimate: {result.token_estimate}")
            if result.telemetry:
                console.print(f"  Claims loaded: {result.telemetry.get('claims_loaded', 0)}")
                console.print(f"  Sources: {result.telemetry.get('sources_loaded', 0)}")

        return

    # RAG mode: unified multi-signal retrieval
    from kurt.retrieval import RetrievalContext, retrieve

    console.print(f"[dim]Mode: RAG ({query_type})" + (" (deep)" if deep else "") + "[/dim]")
    console.print("[dim]Using unified retrieval.rag step[/dim]")
    console.print()

    # Create retrieval context
    ctx = RetrievalContext(
        query=query,
        query_type=query_type,
        deep_mode=deep,
        session_id=session_id,
    )

    # Run retrieval
    try:
        result = asyncio.run(retrieve(ctx))
    except Exception as e:
        console.print(f"[red]Error during retrieval:[/red] {e}")
        raise click.Abort()

    # Output based on format
    if output_format == "json":
        output = {
            "query": query,
            "query_type": query_type,
            "deep_mode": deep,
            "context_text": result.context_text,
            "citations": [
                {
                    "doc_id": c.doc_id,
                    "title": c.title,
                    "source_url": c.source_url,
                    "confidence": c.confidence,
                }
                for c in result.citations
            ],
            "graph_payload": {
                "nodes": result.graph_payload.nodes if result.graph_payload else [],
                "edges": result.graph_payload.edges if result.graph_payload else [],
            },
            "telemetry": result.telemetry,
        }
        print(json.dumps(output, indent=2))

    elif output_format == "citations":
        if not result.citations:
            console.print("[yellow]No citations found[/yellow]")
            return

        console.print("[bold cyan]Citations[/bold cyan]")
        console.print()

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Rank", style="yellow", width=6, justify="right")
        table.add_column("Title", style="bold")
        table.add_column("Score", style="green", width=8, justify="right")
        table.add_column("URL", style="dim")

        for i, citation in enumerate(result.citations, 1):
            title = citation.title or "Untitled"
            if len(title) > 50:
                title = title[:47] + "..."
            url = citation.source_url or "N/A"
            if len(url) > 40:
                url = url[:37] + "..."

            table.add_row(
                str(i),
                title,
                f"{citation.confidence:.1%}",
                url,
            )

        console.print(table)
        console.print()
        console.print(f"[dim]Total: {len(result.citations)} citations[/dim]")

    else:  # context (default)
        # Show context in a panel
        console.print(
            Panel(
                result.context_text,
                title="[bold cyan]Retrieved Context[/bold cyan]",
                border_style="cyan",
            )
        )

        # Show summary stats
        telemetry = result.telemetry or {}
        console.print()
        console.print("[dim]Stats:[/dim]")
        if "graph_results" in telemetry:
            console.print(f"  Graph results: {telemetry['graph_results']}")
        if "semantic_results" in telemetry:
            console.print(f"  Semantic results: {telemetry['semantic_results']}")
        if "entities" in telemetry:
            console.print(f"  Entities: {telemetry['entities']}")
        if result.citations:
            console.print(f"  Citations: {len(result.citations)}")

        # Show suggested prompt if available
        if result.suggested_prompt:
            console.print()
            console.print("[dim]Suggested prompt:[/dim]")
            console.print(f"  {result.suggested_prompt}")

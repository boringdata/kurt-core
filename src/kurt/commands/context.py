"""Context command - Retrieve relevant documents for a question using GraphRAG."""

import json
from pathlib import Path

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command
from kurt.config import config_file_exists
from kurt.content.answer import retrieve_context
from kurt.content.context_formatter import (
    format_context_as_markdown,
    format_documents_info,
    format_entities_info,
    format_relationships_info,
    format_retrieval_stats,
)

console = Console()


@click.command()
@click.argument("question", type=str)
@click.option(
    "--max-docs",
    type=int,
    default=10,
    help="Maximum number of documents to retrieve (default: 10)",
)
@click.option(
    "--output",
    type=click.Path(),
    default=None,
    help="Write context to markdown file instead of stdout",
)
@click.option(
    "--json-output",
    is_flag=True,
    help="Output as JSON with document paths and metadata",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed retrieval information including entities",
)
@click.option(
    "--full-content",
    is_flag=True,
    help="Include full document content (otherwise just paths and metadata)",
)
@track_command
def context(
    question: str,
    max_docs: int,
    output: str | None,
    json_output: bool,
    verbose: bool,
    full_content: bool,
):
    """Retrieve relevant document context for a question using GraphRAG.

    Unlike 'answer', this command doesn't synthesize a response. Instead, it:
    1. Finds relevant entities via embedding similarity
    2. Traverses relationships to expand context
    3. Retrieves connected documents
    4. Returns document paths and metadata for further processing

    This is ideal for feeding relevant context to external tools like Claude Code
    for synthesis, or for exploring what documents are relevant to a topic.

    Example:
        kurt context "What is FastAPI?"
        kurt context "How does authentication work?" --json-output
        kurt context "What integrations are available?" --max-docs 20 --full-content
    """
    # Check if project is initialized
    if not config_file_exists():
        console.print("[red]Error:[/red] Kurt project not initialized")
        console.print("Run [cyan]kurt init[/cyan] to initialize a project")
        raise click.Abort()

    try:
        import time

        start_time = time.time()

        # Retrieve context from knowledge graph (shared with answer command)
        ctx = retrieve_context(question, max_documents=max_docs)

        duration = time.time() - start_time

        # Use shared formatting functions
        # For JSON output, always include absolute paths and entities for CC integration
        documents_info = format_documents_info(
            ctx,
            full_content=full_content,
            include_absolute_paths=json_output,  # Always include absolute paths in JSON
            include_entities=True,  # Always include entities in documents
        )
        # Always get entities info (not just in verbose mode)
        entities_info = format_entities_info(ctx)
        relationships_info = format_relationships_info(ctx)
        retrieval_stats = format_retrieval_stats(ctx, duration)

        if json_output:
            # Output as JSON optimized for CC integration - includes full context
            result = {
                "question": question,
                "relevant_files": [
                    {
                        "path": doc.get("absolute_path", doc.get("content_path", "")),
                        "title": doc["title"],
                        "relevance": doc["score"],
                        "url": doc.get("source_url"),
                        "entities": doc.get("entities", []),  # Entities found in this document
                    }
                    for doc in documents_info
                ],
                "entities": entities_info[:10],  # Top 10 entities overall
                "relationships": relationships_info,
                "stats": retrieval_stats,
            }

            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        # Output file specified - write markdown
        if output:
            output_path = Path(output)

            # Use shared markdown formatter
            md_content = format_context_as_markdown(
                question=question,
                context=ctx,
                full_content=full_content,
                verbose=verbose,
                duration=duration,
            )

            # Write to file
            output_path.write_text(md_content, encoding="utf-8")
            console.print(f"[green]✓[/green] Context written to: {output_path}")
            return

        # Default console output
        if not json_output:
            console.print(f"[dim]Question:[/dim] {question}\n")

        console.print(f"[bold]Retrieved {len(documents_info)} Relevant Documents:[/bold]\n")

        for i, doc_info in enumerate(documents_info, 1):
            console.print(f"[bold]{i}.[/bold] {doc_info['title']}")
            console.print(f"   [dim]Score:[/dim] {doc_info['score']:.2f}")

            if doc_info.get("content_path"):
                console.print(f"   [dim]File:[/dim] .kurt/sources/{doc_info['content_path']}")

            if doc_info.get("source_url"):
                console.print(f"   [dim]URL:[/dim] {doc_info['source_url']}")

            # Show entities found in this document
            if doc_info.get("entities"):
                entities_list = doc_info["entities"][:5]  # Show top 5 entities
                entities_text = ", ".join([f"{e['name']} ({e['mentions']})" for e in entities_list])
                if len(doc_info["entities"]) > 5:
                    entities_text += f" ... +{len(doc_info['entities']) - 5} more"
                console.print(f"   [dim]Entities:[/dim] {entities_text}")

            if doc_info.get("preview"):
                console.print(f"   [dim]Preview:[/dim] {doc_info['preview']}")

            console.print()

        # Always show key entities
        if entities_info:
            console.print("[bold]Key Entities:[/bold]")
            for entity in entities_info[:10]:  # Top 10 entities
                console.print(
                    f"  • {entity['name']} ({entity['type']}) "
                    f"[dim]similarity: {entity['similarity']:.2f}[/dim]"
                )
            console.print()

        # Show relationships in verbose mode
        if verbose and relationships_info:
            console.print("[bold]Entity Relationships:[/bold]")
            for rel in relationships_info[:10]:  # Top 10 relationships
                console.print(
                    f"  • {rel['source']} → {rel['relationship']} → {rel['target']} "
                    f"[dim](confidence: {rel['confidence']:.2f})[/dim]"
                )
            console.print()

        # Retrieval stats
        console.print("[bold]Retrieval Stats:[/bold]")
        console.print(f"  • Documents found: {retrieval_stats['documents_found']}")
        console.print(f"  • Entities found: {retrieval_stats['entities_found']}")
        console.print(f"  • Top entity similarity: {retrieval_stats['top_entity_similarity']:.2f}")
        console.print(f"  • Retrieval time: {duration:.2f}s")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback

            console.print("\n[dim]" + traceback.format_exc() + "[/dim]")
        raise click.Abort()

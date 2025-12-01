"""Answer command - GraphRAG-based question answering."""

import json

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command
from kurt.config import config_file_exists
from kurt.content.answer import answer_question

console = Console()


def _log_usage(token_usage: dict | None):
    """Print token usage metrics for human-readable output."""
    if not token_usage:
        return

    tokens = token_usage.get("total_tokens")
    duration = token_usage.get("duration_seconds")

    if tokens is not None:
        console.print(f"[dim]Tokens Used:[/dim] {tokens}")
    if duration is not None:
        console.print(f"[dim]Generation Time:[/dim] {duration:.2f}s")


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
    help="Write answer to markdown file instead of stdout",
)
@click.option("--verbose", is_flag=True, help="Show detailed retrieval information")
@click.option(
    "--json-output",
    is_flag=True,
    help="Print answer, metadata, and usage as a single JSON object (disables rich formatting)",
)
@track_command
def answer(question: str, max_docs: int, output: str, verbose: bool, json_output: bool):
    """Answer a question using GraphRAG retrieval from the knowledge graph.

    Uses local search strategy:
    1. Find relevant entities via embedding similarity
    2. Traverse relationships to expand context
    3. Retrieve connected documents
    4. Generate answer with citations

    Example:
        kurt answer "What is FastAPI?"
        kurt answer "How does authentication work?" --verbose
        kurt answer "What integrations are available?" --max-docs 20
    """
    # Check if project is initialized
    if not config_file_exists():
        console.print("[red]Error:[/red] Kurt project not initialized")
        console.print("Run [cyan]kurt init[/cyan] to initialize a project")
        raise click.Abort()

    try:
        import time
        start_time = time.time()

        # Answer the question
        result = answer_question(question, max_documents=max_docs)

        duration = time.time() - start_time

        if not output and not json_output:
            console.print(f"[dim]Question:[/dim] {question}\n")

        cached_response = result.token_usage is None

        # Prepare token_usage with duration
        token_usage = result.token_usage or {}
        # Always add duration_seconds
        token_usage["duration_seconds"] = duration

        metadata = {
            "question": question,
            "confidence": result.confidence,
            "documents_retrieved": result.retrieval_stats["documents_found"],
            "entities_found": result.retrieval_stats["entities_found"],
            "token_usage": token_usage,
            "sources": result.documents_cited,
            "key_entities": result.entities_used,
            "cached_response": cached_response,
        }

        # If output file specified, write to markdown
        if output:
            from pathlib import Path

            output_path = Path(output)

            # Build markdown content
            md_content = f"# Answer\n\n{result.answer}\n\n"

            # Add reasoning section if available
            if hasattr(result, 'reasoning') and result.reasoning:
                md_content += "## Reasoning\n\n"
                md_content += f"{result.reasoning}\n\n"

            # Add sources section with documents and entities
            md_content += "## Sources\n\n"

            # Documents section
            if result.documents_cited:
                md_content += "### Documents Used\n\n"
                for doc_id, doc_title, content_path, score in result.documents_cited:
                    # Use content_path if available, otherwise fall back to doc_title
                    if content_path:
                        md_content += f"- {content_path} (relevance: {score:.2f})\n"
                    else:
                        md_content += f"- {doc_title} (relevance: {score:.2f})\n"
                md_content += "\n"

            # Entities section
            if result.entities_used:
                md_content += "### Entities Used\n\n"
                for entity_name, similarity in result.entities_used:
                    md_content += f"- **{entity_name}** (similarity: {similarity:.2f})\n"
                md_content += "\n"

            # Relationships section
            if hasattr(result, 'relationships_used') and result.relationships_used:
                md_content += "### Entity Relationships\n\n"
                for source, rel_type, target, context in result.relationships_used:
                    rel_text = f"- **{source}** → _{rel_type}_ → **{target}**"
                    if context:
                        # Truncate context if too long
                        ctx_display = context[:150] + "..." if len(context) > 150 else context
                        rel_text += f"\n  - Context: _{ctx_display}_"
                    md_content += rel_text + "\n"
                md_content += "\n"

            # Knowledge Graph Usage Details
            md_content += "### Knowledge Graph Usage\n\n"
            md_content += f"- **Total Entities Found**: {result.retrieval_stats['entities_found']}\n"
            md_content += f"- **Total Documents Retrieved**: {result.retrieval_stats['documents_found']}\n"
            if 'top_entity_similarity' in result.retrieval_stats:
                md_content += f"- **Top Entity Similarity**: {result.retrieval_stats['top_entity_similarity']:.2f}\n"
            if hasattr(result, 'relationships_used') and result.relationships_used:
                md_content += f"- **Relationships Explored**: {len(result.relationships_used)}\n"
            md_content += "\n"

            # Add metadata section
            md_content += "## Metadata\n\n"
            md_content += f"- **Confidence**: {result.confidence:.2f}\n"

            if result.entities_used:
                # Only show entities with positive similarity in the summary
                key_entities = [e[0] for e in result.entities_used if e[1] > 0]
                if key_entities:
                    md_content += (
                        f"- **Key Entities**: {', '.join(key_entities)}\n"
                    )

            md_content += (
                f"- **Documents Retrieved**: {result.retrieval_stats['documents_found']}\n"
            )
            md_content += f"- **Entities Found**: {result.retrieval_stats['entities_found']}\n"

            if result.token_usage:
                tokens = result.token_usage.get("total_tokens")
                duration = result.token_usage.get("duration_seconds")
                if tokens is not None:
                    md_content += f"- **Tokens Used**: {tokens}\n"
                if duration is not None:
                    md_content += f"- **Generation Time**: {duration:.2f} seconds\n"
            else:
                md_content += "- **Tokens Used**: cached result (no new tokens)\n"

            # Write to file
            output_path.write_text(md_content, encoding="utf-8")
            if not json_output:
                console.print(f"[green]✓[/green] Answer written to: {output_path}")
                if cached_response:
                    console.print("[dim]Token usage unavailable (cached response).[/dim]")
                else:
                    _log_usage(result.token_usage)
                return

        if json_output:
            json_payload = {
                "answer": result.answer,
                **metadata,
                "answer_file": output if output else None,
            }
            print(json.dumps(json_payload, ensure_ascii=False, indent=2))
            return

        # Otherwise display to console
        console.print("[bold]Answer:[/bold]")
        console.print(result.answer)
        console.print()

        # Display reasoning in verbose mode
        if verbose and hasattr(result, 'reasoning') and result.reasoning:
            console.print("[bold]Reasoning:[/bold]")
            console.print(result.reasoning)
            console.print()

        # Display confidence
        confidence_color = (
            "green" if result.confidence >= 0.7 else "yellow" if result.confidence >= 0.5 else "red"
        )
        console.print(
            f"[bold]Confidence:[/bold] [{confidence_color}]{result.confidence:.2f}[/{confidence_color}]"
        )
        console.print()

        # Display entities used
        if result.entities_used:
            console.print("[bold]Key Entities:[/bold]")
            for entity_name, similarity in result.entities_used:
                console.print(f"  • {entity_name} [dim](relevance: {similarity:.2f})[/dim]")
            console.print()

        # Display documents cited
        if result.documents_cited:
            console.print("[bold]Sources:[/bold]")
            for doc_id, doc_title, content_path, score in result.documents_cited:
                # Use content_path if available, otherwise fall back to doc_title
                display_name = content_path if content_path else doc_title
                console.print(f"  • {display_name} [dim](score: {score:.2f})[/dim]")
            console.print()

        # Display retrieval stats (verbose mode)
        if verbose:
            console.print("[bold]Retrieval Stats:[/bold]")
            console.print(f"  • Entities found: {result.retrieval_stats['entities_found']}")
            console.print(f"  • Documents found: {result.retrieval_stats['documents_found']}")
            console.print(
                f"  • Top entity similarity: {result.retrieval_stats['top_entity_similarity']:.2f}"
            )
            console.print()

        if cached_response:
            console.print("[dim]Token usage unavailable (cached response).[/dim]")
        else:
            _log_usage(result.token_usage)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback

            console.print("\n[dim]" + traceback.format_exc() + "[/dim]")
        raise click.Abort()

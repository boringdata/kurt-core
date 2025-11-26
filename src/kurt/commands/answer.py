"""Answer command - GraphRAG-based question answering."""

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command
from kurt.config import config_file_exists
from kurt.content.answer import answer_question

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
    help="Write answer to markdown file instead of stdout",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed retrieval information",
)
@track_command
def answer(question: str, max_docs: int, output: str, verbose: bool):
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

    if not output:
        console.print(f"[dim]Question:[/dim] {question}\n")

    try:
        # Answer the question
        result = answer_question(question, max_documents=max_docs)

        # If output file specified, write to markdown
        if output:
            from pathlib import Path

            output_path = Path(output)

            # Build markdown content
            md_content = f"# Answer\n\n{result.answer}\n\n"

            # Add sources section
            if result.documents_cited:
                md_content += "## Sources\n\n"
                for doc_id, doc_title, score in result.documents_cited:
                    md_content += f"- {doc_title} (relevance: {score:.2f})\n"
                md_content += "\n"

            # Add metadata section
            md_content += "## Metadata\n\n"
            md_content += f"- **Confidence**: {result.confidence:.2f}\n"

            if result.entities_used:
                md_content += f"- **Key Entities**: {', '.join([e[0] for e in result.entities_used])}\n"

            md_content += f"- **Documents Retrieved**: {result.retrieval_stats['documents_found']}\n"
            md_content += f"- **Entities Found**: {result.retrieval_stats['entities_found']}\n"

            # Write to file
            output_path.write_text(md_content, encoding="utf-8")
            console.print(f"[green]✓[/green] Answer written to: {output_path}")
            return

        # Otherwise display to console
        console.print("[bold]Answer:[/bold]")
        console.print(result.answer)
        console.print()

        # Display confidence
        confidence_color = "green" if result.confidence >= 0.7 else "yellow" if result.confidence >= 0.5 else "red"
        console.print(f"[bold]Confidence:[/bold] [{confidence_color}]{result.confidence:.2f}[/{confidence_color}]")
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
            for doc_id, doc_title, score in result.documents_cited:
                console.print(f"  • {doc_title} [dim](score: {score:.2f})[/dim]")
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

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback

            console.print("\n[dim]" + traceback.format_exc() + "[/dim]")
        raise click.Abort()

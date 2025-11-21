"""Write command - Generate content with AI based on sources and goals."""

import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from kurt.admin.telemetry.decorators import track_command
from kurt.content.generation import ContentGenerationRequest, generate_content_workflow
from kurt.content.generation.models import ContentFormat, ContentTone
from kurt.workflows import DBOS, init_dbos

console = Console()
logger = logging.getLogger(__name__)


@click.command("write")
@track_command
@click.argument("goal", required=True)
@click.option(
    "--format",
    type=click.Choice([f.value for f in ContentFormat], case_sensitive=False),
    default=ContentFormat.BLOG_POST.value,
    help="Content format to generate (blog-post, tutorial, guide, product-page, etc.)",
)
@click.option(
    "--tone",
    type=click.Choice([t.value for t in ContentTone], case_sensitive=False),
    default=ContentTone.PROFESSIONAL.value,
    help="Writing tone (professional, conversational, technical, friendly, formal, casual)",
)
@click.option(
    "--ids",
    "document_ids",
    help="SOURCES: Comma-separated document IDs to use as sources",
)
@click.option(
    "--entities",
    "entity_names",
    help="SOURCES: Comma-separated entity names from knowledge graph (e.g., 'Topic:authentication,Technology:OAuth')",
)
@click.option(
    "--search",
    "search_query",
    help="SOURCES: Search query to find relevant documents automatically",
)
@click.option(
    "--word-count",
    type=int,
    help="Target word count (approximate)",
)
@click.option(
    "--code-examples",
    is_flag=True,
    help="Include code examples in the generated content",
)
@click.option(
    "--no-citations",
    is_flag=True,
    help="Don't include citations to source documents",
)
@click.option(
    "--ai-provider",
    type=click.Choice(["anthropic", "openai"], case_sensitive=False),
    default="anthropic",
    help="AI provider to use (default: anthropic)",
)
@click.option(
    "--ai-model",
    help="Specific AI model to use (defaults to provider default)",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    help="Output file path (default: print to console)",
)
@click.option(
    "--no-frontmatter",
    is_flag=True,
    help="Don't include YAML frontmatter in output",
)
@click.option(
    "--background",
    is_flag=True,
    help="Run generation in background and return immediately",
)
def write_cmd(
    goal: str,
    format: str,
    tone: str,
    document_ids: Optional[str],
    entity_names: Optional[str],
    search_query: Optional[str],
    word_count: Optional[int],
    code_examples: bool,
    no_citations: bool,
    ai_provider: str,
    ai_model: Optional[str],
    output_path: Optional[str],
    no_frontmatter: bool,
    background: bool,
):
    """
    Generate content with AI based on goal and sources.

    GOAL is what you want the content to achieve (e.g., "Explain OAuth 2.0 flow").

    \b
    Examples:
        # Generate blog post about authentication
        kurt content write "Explain OAuth 2.0 authentication flow" \\
            --format blog-post \\
            --search "OAuth authentication" \\
            --output blog/oauth-explained.md

        # Generate tutorial from specific documents
        kurt content write "Create getting started tutorial" \\
            --format tutorial \\
            --ids "abc123,def456" \\
            --word-count 1500 \\
            --code-examples

        # Generate content based on knowledge graph entities
        kurt content write "Write about our authentication features" \\
            --format product-page \\
            --entities "Topic:authentication,Technology:OAuth,Technology:JWT" \\
            --tone conversational

        # Background generation
        kurt content write "Create comprehensive API guide" \\
            --format guide \\
            --search "API documentation" \\
            --background \\
            --output docs/api-guide.md
    """
    console.print(f"\n[bold blue]Generating content:[/bold blue] {goal}\n")

    # Parse document IDs
    source_document_ids = []
    if document_ids:
        try:
            source_document_ids = [UUID(id.strip()) for id in document_ids.split(",")]
        except ValueError as e:
            console.print(f"[red]Error:[/red] Invalid document ID format: {e}")
            raise click.Abort()

    # Parse entity names
    source_entity_names = []
    if entity_names:
        source_entity_names = [name.strip() for name in entity_names.split(",")]

    # Validate sources
    if not source_document_ids and not source_entity_names and not search_query:
        console.print(
            "[yellow]Warning:[/yellow] No sources specified. "
            "Content will be generic. Consider using --ids, --entities, or --search."
        )
        if not click.confirm("Continue anyway?"):
            raise click.Abort()

    # Validate output path
    if output_path:
        output_file = Path(output_path)
        if output_file.exists():
            console.print(f"[yellow]Warning:[/yellow] File exists: {output_path}")
            if not click.confirm("Overwrite?"):
                raise click.Abort()

    # Create request
    request = ContentGenerationRequest(
        goal=goal,
        format=ContentFormat(format),
        tone=ContentTone(tone),
        source_document_ids=source_document_ids,
        source_entity_names=source_entity_names,
        source_query=search_query,
        target_word_count=word_count,
        include_code_examples=code_examples,
        include_citations=not no_citations,
        ai_provider=ai_provider,
        ai_model=ai_model,
        output_path=output_path,
        add_frontmatter=not no_frontmatter,
    )

    # Show request summary
    console.print(
        Panel.fit(
            f"""[bold]Generation Request[/bold]

Format: {format}
Tone: {tone}
AI Provider: {ai_provider} ({ai_model or 'default model'})

Sources:
  • Documents: {len(source_document_ids)} specified
  • Entities: {len(source_entity_names)} specified
  • Search: {'Yes' if search_query else 'No'}

Options:
  • Target words: {word_count or 'not specified'}
  • Code examples: {'Yes' if code_examples else 'No'}
  • Citations: {'Yes' if not no_citations else 'No'}
  • Output: {output_path or 'console'}""",
            title="Configuration",
            border_style="blue",
        )
    )

    # Initialize DBOS
    init_dbos()

    # Start workflow
    console.print("\n[bold]Starting generation workflow...[/bold]\n")

    request_dict = request.model_dump()

    if background:
        # Start in background
        handle = DBOS.start_workflow(
            generate_content_workflow,
            request_dict,
        )

        console.print(
            f"[green]✓[/green] Generation started in background\n"
            f"Workflow ID: {handle.workflow_id}\n\n"
            f"Check status with: [cyan]dbos workflow get {handle.workflow_id}[/cyan]"
        )

    else:
        # Run synchronously with status updates
        try:
            with console.status("[bold blue]Generating content...") as status:
                status.update("[bold blue]Building context from sources...")

                # Start workflow
                handle = DBOS.start_workflow(
                    generate_content_workflow,
                    request_dict,
                )

                status.update("[bold blue]Generating content with AI...")

                # Wait for result
                result = handle.get_result()

            # Display result
            console.print("\n[green]✓ Content generated successfully![/green]\n")

            console.print(f"[bold]Title:[/bold] {result['title']}")
            console.print(f"[bold]Word count:[/bold] {result['word_count']}")
            console.print(f"[bold]Sources used:[/bold] {len(result['sources'])}")
            console.print(f"[bold]Tokens:[/bold] ~{result['tokens_used']}\n")

            if output_path:
                console.print(f"[green]Content saved to:[/green] {output_path}\n")
            else:
                # Display content in console
                console.print("[bold]Generated Content:[/bold]\n")

                # Reconstruct full content
                from kurt.content.generation.models import GeneratedContent

                gen_content = GeneratedContent(
                    request=request,
                    title=result["title"],
                    content=result["content"],
                    word_count=result["word_count"],
                    sources=[],
                    ai_provider=result["ai_provider"],
                    ai_model=result["ai_model"],
                    tokens_used=result["tokens_used"],
                )

                markdown_output = gen_content.to_markdown(include_metadata=not no_frontmatter)

                # Display with syntax highlighting
                console.print(
                    Panel(
                        Markdown(markdown_output),
                        title="Generated Content",
                        border_style="green",
                    )
                )

        except Exception as e:
            console.print(f"\n[red]Error during generation:[/red] {e}")
            logger.exception("Content generation failed")
            raise click.Abort()

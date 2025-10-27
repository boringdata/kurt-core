"""Research integration CLI commands."""

import click
import json
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import Optional
from datetime import datetime

from kurt.research.config import (
    research_config_exists,
    source_configured,
    get_source_config
)

console = Console()


def get_adapter(source: str):
    """Get research adapter instance for the specified source."""
    config = get_source_config(source)

    if source == "perplexity":
        from kurt.research.perplexity import PerplexityAdapter
        return PerplexityAdapter(config)
    elif source == "tavily":
        raise NotImplementedError("Tavily support coming soon")
    elif source == "exa":
        raise NotImplementedError("Exa support coming soon")
    else:
        raise ValueError(f"Unsupported research source: {source}")


@click.group()
def research():
    """Research integration for discovering topics and gathering information."""
    pass


@research.command("search")
@click.argument("query")
@click.option("--source", default="perplexity", help="Research source (perplexity, tavily, exa)")
@click.option("--recency", type=click.Choice(["hour", "day", "week", "month"]), help="Time filter for results")
@click.option("--model", help="Override default model")
@click.option("--save", is_flag=True, help="Save results to sources/research/")
@click.option("--output", type=click.Choice(["markdown", "json"]), default="markdown", help="Output format")
def search_cmd(query: str, source: str, recency: Optional[str], model: Optional[str], save: bool, output: str):
    """
    Execute research query.

    Examples:
        kurt research search "AI coding tools news today"
        kurt research search "developer tools trends" --recency week
        kurt research search "GitHub Copilot updates" --save
    """
    try:
        # Check if source is configured
        if not source_configured(source):
            console.print(f"[red]Error:[/red] {source.capitalize()} not configured")
            console.print(f"Add your API key to .kurt/research-config.json")
            console.print(f"See .kurt/README.md for setup instructions")
            raise click.Abort()

        adapter = get_adapter(source)

        # Show progress while researching
        console.print(f"[cyan]Researching:[/cyan] {query}")
        if recency:
            console.print(f"[dim]Recency: {recency}[/dim]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[cyan]Analyzing sources..."),
            console=console,
            transient=True
        ) as progress:
            progress.add_task("research", total=None)

            # Execute search (this will block while API processes)
            result = adapter.search(
                query=query,
                recency=recency,
                model=model
            )

        # Display results
        console.print()
        console.print(f"[green]✓ Research complete[/green] ({result.response_time_seconds:.1f}s)")
        console.print(f"[bold]{query}[/bold]")
        console.print()

        if output == "json":
            print(json.dumps(result.to_dict(), indent=2, default=str))
        else:
            # Display answer
            console.print(result.answer)
            console.print()

            # Display sources
            if result.citations:
                console.print(f"[bold]Sources ({len(result.citations)}):[/bold]")
                for i, citation in enumerate(result.citations[:10], 1):
                    console.print(f"  [{i}] {citation.url}")
                if len(result.citations) > 10:
                    console.print(f"  ... and {len(result.citations) - 10} more")

        # Save if requested
        if save:
            # Create output directory
            sources_dir = Path("sources/research")
            sources_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            date_str = datetime.now().strftime("%Y-%m-%d")
            # Sanitize query for filename
            safe_query = "".join(c if c.isalnum() or c in (' ', '-') else '' for c in query)
            safe_query = safe_query.replace(' ', '-').lower()[:50]
            filename = f"{date_str}-{safe_query}.md"
            filepath = sources_dir / filename

            # Save as markdown
            with open(filepath, 'w') as f:
                f.write(result.to_markdown())

            console.print()
            console.print(f"[green]✓ Saved to:[/green] {filepath}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@research.command("list")
@click.option("--limit", type=int, default=20, help="Number of results to show")
def list_cmd(limit: int):
    """
    List recent research results.

    Shows markdown files saved in sources/research/

    Example:
        kurt research list
        kurt research list --limit 10
    """
    try:
        sources_dir = Path("sources/research")

        if not sources_dir.exists():
            console.print("[yellow]No research results found[/yellow]")
            console.print(f"Run: [cyan]kurt research search \"your query\" --save[/cyan]")
            return

        # Find all markdown files
        md_files = sorted(sources_dir.glob("**/*.md"), key=lambda p: p.stat().st_mtime, reverse=True)

        if not md_files:
            console.print("[yellow]No research results found[/yellow]")
            return

        console.print(f"[bold]Recent Research ({len(md_files)} results)[/bold]\n")

        for filepath in md_files[:limit]:
            # Read frontmatter to get metadata
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                    if content.startswith('---'):
                        import yaml
                        parts = content.split('---', 2)
                        if len(parts) >= 3:
                            frontmatter = yaml.safe_load(parts[1])
                            query = frontmatter.get('research_query', filepath.stem)
                            date = frontmatter.get('research_date', '')
                            sources_count = frontmatter.get('sources_count', 0)

                            console.print(f"[cyan]{filepath.name}[/cyan]")
                            console.print(f"  Query: {query}")
                            console.print(f"  Date: {str(date)[:10] if date else 'unknown'}")
                            console.print(f"  Sources: {sources_count}")
                            console.print()
            except Exception as e:
                console.print(f"[yellow]Could not read:[/yellow] {filepath.name}")
                console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@research.command("get")
@click.argument("filename")
def get_cmd(filename: str):
    """
    Display a specific research result.

    Args:
        filename: Name of the research file (with or without .md extension)

    Example:
        kurt research get 2025-10-27-ai-coding-tools
    """
    try:
        sources_dir = Path("sources/research")

        # Add .md extension if not present
        if not filename.endswith('.md'):
            filename = f"{filename}.md"

        filepath = sources_dir / filename

        if not filepath.exists():
            console.print(f"[red]Error:[/red] Research result not found: {filename}")
            console.print(f"Run [cyan]kurt research list[/cyan] to see available results")
            raise click.Abort()

        # Read and display
        with open(filepath, 'r') as f:
            content = f.read()

        # Parse frontmatter and display
        if content.startswith('---'):
            import yaml
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                body = parts[2].strip()

                console.print(f"[bold cyan]Research Result[/bold cyan]")
                console.print(f"[dim]File: {filename}[/dim]\n")

                console.print(f"[bold]Query:[/bold] {frontmatter.get('research_query', 'N/A')}")
                console.print(f"[bold]Date:[/bold] {str(frontmatter.get('research_date', 'N/A'))[:19]}")
                console.print(f"[bold]Source:[/bold] {frontmatter.get('research_source', 'N/A')}")
                console.print(f"[bold]Sources:[/bold] {frontmatter.get('sources_count', 0)} citations")
                console.print()

                console.print(body)
        else:
            console.print(content)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

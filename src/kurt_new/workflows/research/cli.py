"""CLI commands for research workflow execution."""

from __future__ import annotations

import json

import click
from rich.console import Console

from kurt_new.admin.telemetry.decorators import track_command
from kurt_new.cli.options import format_option

console = Console()


@click.group()
def research_group():
    """
    Research commands.

    \\b
    Commands:
      search      Execute research query via Perplexity
    """
    pass


@research_group.command("search")
@click.argument("query")
@click.option(
    "--recency",
    default="day",
    type=click.Choice(["hour", "day", "week", "month"]),
    help="Time filter",
)
@click.option("--model", default="sonar-reasoning", help="Perplexity model")
@click.option("--save", is_flag=True, help="Save result to sources/research/")
@click.option("--background", is_flag=True, help="Run in background")
@click.option("--dry-run", is_flag=True, help="Execute but don't persist to DB")
@format_option
@track_command
def search_cmd(
    query: str,
    recency: str,
    model: str,
    save: bool,
    background: bool,
    dry_run: bool,
    output_format: str,
):
    """
    Execute research query via Perplexity.

    \\b
    Examples:
        kurt research search "What are the latest trends in AI?"
        kurt research search "B2B SaaS pricing strategies" --recency week
        kurt research search "Python best practices" --save
        kurt research search "Market analysis" --background
    """
    from .config import ResearchConfig
    from .workflow import run_research

    config = ResearchConfig(
        query=query,
        recency=recency,
        model=model,
        save=save,
        dry_run=dry_run,
    )

    if background:
        console.print("[dim]Starting research workflow in background...[/dim]")
        workflow_id = run_research(config, background=True)
        console.print(f"[green]\u2713 Workflow started:[/green] {workflow_id}")
        console.print(
            "[dim]Use [cyan]kurt workflows status {workflow_id}[/cyan] to check progress[/dim]"
        )
        return

    console.print("[dim]Executing research query...[/dim]")

    try:
        result = run_research(config)

        if output_format == "json":
            print(json.dumps(result, indent=2, default=str))
        else:
            _display_research_result(result)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


def _display_research_result(result: dict):
    """Display research result in a nice format."""
    console.print()
    console.print(f"[bold cyan]Query:[/bold cyan] {result['query']}")
    console.print(
        f"[dim]Source: {result['source']} | Model: {result.get('result', {}).get('model', 'N/A')}[/dim]"
    )

    if result.get("response_time_seconds"):
        console.print(f"[dim]Response time: {result['response_time_seconds']:.1f}s[/dim]")

    console.print()

    # Show answer
    answer = result.get("result", {}).get("answer", "")
    console.print("[bold]Answer:[/bold]")
    console.print(answer)
    console.print()

    # Show citations
    citations = result.get("result", {}).get("citations", [])
    if citations:
        console.print(f"[bold]Sources ({len(citations)}):[/bold]")
        for i, cite in enumerate(citations, 1):
            console.print(
                f"  [{i}] {cite.get('title', 'Source')} - [cyan]{cite.get('url', '')}[/cyan]"
            )
        console.print()

    # Persistence info
    if result.get("content_path"):
        console.print(f"[green]\u2713 Saved to:[/green] {result['content_path']}")
    if result.get("document_id"):
        console.print(f"[dim]Document ID: {result['document_id']}[/dim]")

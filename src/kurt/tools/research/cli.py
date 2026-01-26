"""CLI command for research tool."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command
from kurt.cli.options import add_background_options, dry_run_option, format_option
from kurt.cli.output import print_json
from kurt.tools.runner import create_pending_run, run_tool_with_tracking, spawn_background_run

console = Console()


@click.group()
def research_group():
    """
    Research commands.

    \b
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
    help="Time filter for results",
)
@click.option("--model", default="sonar-reasoning", help="Perplexity model to use")
@click.option("--save", is_flag=True, help="Save result to sources/research/")
@click.option("--output-dir", default="sources/research", help="Directory to save research results")
@add_background_options()
@dry_run_option
@format_option
@track_command
def search_cmd(
    query: str,
    recency: str,
    model: str,
    save: bool,
    output_dir: str,
    background: bool,
    priority: int,
    dry_run: bool,
    output_format: str,
):
    """
    Execute research query via Perplexity.

    \b
    Examples:
        kurt research search "What are the latest trends in AI?"
        kurt research search "B2B SaaS pricing strategies" --recency week
        kurt research search "Python best practices" --save
        kurt research search "Market analysis" --background
    """
    params: dict[str, object] = {
        "query": query,
        "source": "perplexity",
        "recency": recency,
        "model": model,
        "save": save,
        "output_dir": output_dir,
        "dry_run": dry_run,
    }

    cli_command = "kurt " + " ".join(sys.argv[1:])

    if background:
        run_id = create_pending_run(
            "research",
            params,
            project_root=str(Path.cwd()),
            cli_command=cli_command,
            priority=priority,
        )
        spawn_background_run(
            "research",
            params,
            run_id=run_id,
            project_root=str(Path.cwd()),
            cli_command=cli_command,
            priority=priority,
        )
        if output_format == "json":
            print_json({"run_id": run_id, "background": True})
        else:
            console.print(f"[green]\u2713[/green] Research started (run_id: {run_id})")
            console.print("[dim]Use 'kurt logs <run_id>' to check progress[/dim]")
        return

    run_id, result = run_tool_with_tracking(
        "research",
        params,
        project_root=str(Path.cwd()),
        cli_command=cli_command,
        priority=priority,
    )

    if output_format == "json":
        print_json({"run_id": run_id, **result})
        return

    _display_research_result(result)


def _display_research_result(result: dict):
    """Display research result in a nice format."""
    if not result.get("success"):
        errors = result.get("errors", [])
        for error in errors:
            console.print(f"[red]Error:[/red] {error.get('message', 'Unknown error')}")
        return

    data = result.get("data", [])
    if not data:
        console.print("[yellow]No results returned[/yellow]")
        return

    # Get first result
    item = data[0]

    console.print()
    console.print(f"[bold cyan]Query:[/bold cyan] {item.get('query', 'N/A')}")
    console.print(
        f"[dim]Source: {item.get('source', 'N/A')} | Model: {item.get('model', 'N/A')}[/dim]"
    )

    response_time = item.get("response_time_seconds")
    if response_time:
        console.print(f"[dim]Response time: {response_time:.1f}s[/dim]")

    console.print()

    # Show answer
    answer = item.get("answer", "")
    console.print("[bold]Answer:[/bold]")
    console.print(answer)
    console.print()

    # Show citations
    citations = item.get("citations", [])
    if citations:
        console.print(f"[bold]Sources ({len(citations)}):[/bold]")
        for i, cite in enumerate(citations, 1):
            console.print(
                f"  [{i}] {cite.get('title', 'Source')} - [cyan]{cite.get('url', '')}[/cyan]"
            )
        console.print()

    # Persistence info
    content_path = item.get("content_path")
    if content_path:
        console.print(f"[green]\u2713 Saved to:[/green] {content_path}")

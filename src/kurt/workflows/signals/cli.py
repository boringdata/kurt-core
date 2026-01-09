"""CLI commands for signals workflow execution."""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command
from kurt.cli.options import format_option

console = Console()


@click.group()
def signals_group():
    """
    Signal monitoring commands.

    \\b
    Commands:
      reddit      Monitor Reddit discussions
      hackernews  Monitor HackerNews
      feeds       Monitor RSS/Atom feeds
    """
    pass


@signals_group.command("reddit")
@click.option(
    "-s", "--subreddit", required=True, help="Subreddit(s) to monitor (comma or + separated)"
)
@click.option(
    "--timeframe",
    default="day",
    type=click.Choice(["hour", "day", "week", "month"]),
    help="Time filter",
)
@click.option(
    "--sort", default="hot", type=click.Choice(["hot", "new", "top", "rising"]), help="Sort order"
)
@click.option("--keywords", default=None, help="Keywords to filter (comma-separated)")
@click.option("--min-score", type=int, default=0, help="Minimum score threshold")
@click.option("--limit", type=int, default=25, help="Maximum results")
@click.option("--background", is_flag=True, help="Run in background")
@click.option("--dry-run", is_flag=True, help="Execute but don't persist to DB")
@format_option
@track_command
def reddit_cmd(
    subreddit: str,
    timeframe: str,
    sort: str,
    keywords: str,
    min_score: int,
    limit: int,
    background: bool,
    dry_run: bool,
    output_format: str,
):
    """
    Monitor Reddit discussions.

    \\b
    Examples:
        kurt signals reddit -s python
        kurt signals reddit -s dataengineering --timeframe week
        kurt signals reddit -s "datascience+machinelearning" --keywords "LLM,GPT"
        kurt signals reddit -s programming --min-score 50 --limit 10
    """
    from .config import SignalsConfig
    from .workflow import run_signals

    config = SignalsConfig(
        source="reddit",
        subreddit=subreddit,
        timeframe=timeframe,
        sort=sort,
        keywords=keywords,
        min_score=min_score,
        limit=limit,
        dry_run=dry_run,
    )

    if background:
        console.print("[dim]Starting Reddit signals workflow in background...[/dim]")
        workflow_id = run_signals(config, background=True)
        console.print(f"[green]\u2713 Workflow started:[/green] {workflow_id}")
        return

    console.print(f"[dim]Fetching from r/{subreddit}...[/dim]")

    try:
        result = run_signals(config)

        if output_format == "json":
            print(json.dumps(result, indent=2, default=str))
        else:
            _display_signals(result, "Reddit")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@signals_group.command("hackernews")
@click.option(
    "--timeframe",
    default="day",
    type=click.Choice(["hour", "day", "week", "month"]),
    help="Time filter",
)
@click.option("--keywords", default=None, help="Keywords to filter (comma-separated)")
@click.option("--min-score", type=int, default=10, help="Minimum score threshold")
@click.option("--limit", type=int, default=30, help="Maximum results")
@click.option("--background", is_flag=True, help="Run in background")
@click.option("--dry-run", is_flag=True, help="Execute but don't persist to DB")
@format_option
@track_command
def hackernews_cmd(
    timeframe: str,
    keywords: str,
    min_score: int,
    limit: int,
    background: bool,
    dry_run: bool,
    output_format: str,
):
    """
    Monitor HackerNews.

    \\b
    Examples:
        kurt signals hackernews
        kurt signals hackernews --timeframe week --min-score 100
        kurt signals hackernews --keywords "Python,Rust" --limit 20
    """
    from .config import SignalsConfig
    from .workflow import run_signals

    config = SignalsConfig(
        source="hackernews",
        timeframe=timeframe,
        keywords=keywords,
        min_score=min_score,
        limit=limit,
        dry_run=dry_run,
    )

    if background:
        console.print("[dim]Starting HackerNews signals workflow in background...[/dim]")
        workflow_id = run_signals(config, background=True)
        console.print(f"[green]\u2713 Workflow started:[/green] {workflow_id}")
        return

    console.print("[dim]Fetching from HackerNews...[/dim]")

    try:
        result = run_signals(config)

        if output_format == "json":
            print(json.dumps(result, indent=2, default=str))
        else:
            _display_signals(result, "HackerNews")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@signals_group.command("feeds")
@click.argument("feed_url")
@click.option("--keywords", default=None, help="Keywords to filter (comma-separated)")
@click.option("--limit", type=int, default=50, help="Maximum results")
@click.option("--background", is_flag=True, help="Run in background")
@click.option("--dry-run", is_flag=True, help="Execute but don't persist to DB")
@format_option
@track_command
def feeds_cmd(
    feed_url: str,
    keywords: str,
    limit: int,
    background: bool,
    dry_run: bool,
    output_format: str,
):
    """
    Monitor RSS/Atom feeds.

    \\b
    Examples:
        kurt signals feeds https://example.com/rss.xml
        kurt signals feeds https://blog.example.com/feed --keywords "AI,ML"
        kurt signals feeds https://news.site/rss --limit 20
    """
    from .config import SignalsConfig
    from .workflow import run_signals

    config = SignalsConfig(
        source="feeds",
        feed_url=feed_url,
        keywords=keywords,
        limit=limit,
        dry_run=dry_run,
    )

    if background:
        console.print("[dim]Starting feeds signals workflow in background...[/dim]")
        workflow_id = run_signals(config, background=True)
        console.print(f"[green]\u2713 Workflow started:[/green] {workflow_id}")
        return

    console.print(f"[dim]Fetching feed: {feed_url}...[/dim]")

    try:
        result = run_signals(config)

        if output_format == "json":
            print(json.dumps(result, indent=2, default=str))
        else:
            _display_signals(result, "RSS Feed")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


def _display_signals(result: dict, source_name: str):
    """Display signals in a table."""
    signals = result.get("signals", [])
    total = result.get("total_signals", len(signals))

    console.print()
    console.print(f"[bold]{source_name} Signals ({total} found)[/bold]")
    console.print()

    if not signals:
        console.print("[yellow]No signals found matching filters.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Score", style="green", justify="right", width=6)
    table.add_column("Comments", style="cyan", justify="right", width=8)
    table.add_column("Title", no_wrap=False)
    table.add_column("Source", style="dim", width=15)

    for signal in signals[:25]:  # Show max 25 in table
        title = signal.get("title", "")[:60]
        if len(signal.get("title", "")) > 60:
            title += "..."

        source_info = (
            signal.get("subreddit", "") or signal.get("domain", "") or signal.get("source", "")
        )

        table.add_row(
            str(signal.get("score", 0)),
            str(signal.get("comment_count", 0)),
            title,
            source_info[:15],
        )

    console.print(table)

    if total > 25:
        console.print(f"[dim]... and {total - 25} more. Use --format json to see all.[/dim]")

    console.print()

    # Persistence info
    if result.get("inserted"):
        console.print(f"[green]\u2713 {result['inserted']} new signals saved[/green]")
    if result.get("updated"):
        console.print(f"[dim]{result['updated']} signals updated[/dim]")

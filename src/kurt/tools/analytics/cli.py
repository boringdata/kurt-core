"""CLI command for analytics tool."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command
from kurt.tools.core import (
    add_background_options,
    create_pending_run,
    dry_run_option,
    format_option,
    print_json,
    run_tool_with_tracking,
    spawn_background_run,
)

console = Console()


@click.group()
def analytics_group():
    """
    Domain analytics commands.

    \b
    Commands:
      sync      Sync analytics metrics from PostHog/GA4/Plausible
    """
    pass


@analytics_group.command("sync")
@click.argument("domain")
@click.option(
    "--platform",
    default="posthog",
    type=click.Choice(["posthog", "ga4", "plausible"]),
    help="Analytics platform to use",
)
@click.option(
    "--period-days",
    default=60,
    type=click.IntRange(1, 365),
    help="Days of data to fetch (1-365)",
)
@add_background_options()
@dry_run_option
@format_option
@track_command
def sync_cmd(
    domain: str,
    platform: str,
    period_days: int,
    background: bool,
    priority: int,
    dry_run: bool,
    output_format: str,
):
    """
    Sync domain analytics from an analytics platform.

    \b
    Examples:
        kurt tool analytics sync example.com
        kurt tool analytics sync example.com --platform posthog
        kurt tool analytics sync example.com --period-days 30
        kurt tool analytics sync example.com --background
    """
    params: dict[str, object] = {
        "domain": domain,
        "platform": platform,
        "period_days": period_days,
        "dry_run": dry_run,
    }

    cli_command = "kurt " + " ".join(sys.argv[1:])

    if background:
        run_id = create_pending_run(
            "analytics",
            params,
            project_root=str(Path.cwd()),
            cli_command=cli_command,
            priority=priority,
        )
        spawn_background_run(
            "analytics",
            params,
            run_id=run_id,
            project_root=str(Path.cwd()),
            cli_command=cli_command,
            priority=priority,
        )
        if output_format == "json":
            print_json({"run_id": run_id, "background": True})
        else:
            console.print(f"[green]\u2713[/green] Analytics sync started (run_id: {run_id})")
            console.print("[dim]Use 'kurt logs <run_id>' to check progress[/dim]")
        return

    console.print(f"[dim]Syncing analytics for {domain} from {platform}...[/dim]")

    run_id, result = run_tool_with_tracking(
        "analytics",
        params,
        project_root=str(Path.cwd()),
        cli_command=cli_command,
        priority=priority,
    )

    if output_format == "json":
        print_json({"run_id": run_id, **result})
        return

    _display_analytics_result(result)


def _display_analytics_result(result: dict) -> None:
    """Display analytics result in a nice format."""
    if not result.get("success"):
        errors = result.get("errors", [])
        for error in errors:
            console.print(f"[red]Error:[/red] {error.get('message', 'Unknown error')}")
        return

    data = result.get("data", [])
    if not data:
        console.print("[yellow]No results returned[/yellow]")
        return

    item = data[0]

    console.print()
    console.print(f"[bold cyan]Domain:[/bold cyan] {item.get('domain', 'N/A')}")
    console.print(
        f"[dim]Platform: {item.get('platform', 'N/A')} | Period: {item.get('period_days', 60)} days[/dim]"
    )
    console.print()

    total_urls = item.get("total_urls", 0)
    total_pageviews = item.get("total_pageviews", 0)

    console.print("[bold]Summary:[/bold]")
    console.print(f"  URLs with data: {total_urls}")
    console.print(f"  Total pageviews (60d): {total_pageviews:,}")
    console.print()

    pages = item.get("pages", [])
    if not pages:
        console.print("[yellow]No page data found for this domain.[/yellow]")
        return

    # Sort by pageviews descending
    pages_sorted = sorted(pages, key=lambda p: p.get("pageviews_60d", 0), reverse=True)

    console.print(f"[bold]Top Pages ({min(len(pages_sorted), 20)} of {len(pages_sorted)}):[/bold]")
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Pageviews", style="green", justify="right", width=10)
    table.add_column("Visitors", style="cyan", justify="right", width=10)
    table.add_column("Trend", width=6)
    table.add_column("URL", no_wrap=False)

    for page in pages_sorted[:20]:
        pageviews = page.get("pageviews_60d", 0)
        visitors = page.get("unique_visitors_60d", 0)
        trend = page.get("pageviews_trend", "flat")
        url = page.get("url", "")

        # Format trend with emoji
        if trend == "up":
            trend_display = "[green]\u2191[/green]"
        elif trend == "down":
            trend_display = "[red]\u2193[/red]"
        else:
            trend_display = "[dim]-[/dim]"

        # Truncate URL if too long
        if len(url) > 60:
            url_display = url[:57] + "..."
        else:
            url_display = url

        table.add_row(
            f"{pageviews:,}",
            f"{visitors:,}",
            trend_display,
            url_display,
        )

    console.print(table)

    if len(pages_sorted) > 20:
        console.print(f"[dim]... and {len(pages_sorted) - 20} more. Use --format json to see all.[/dim]")

    console.print()

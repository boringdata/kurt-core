"""Stats command - Show document statistics."""

import click
from rich.console import Console

from kurt.commands.content._shared_options import add_filter_options

console = Console()


@click.command("stats")
@add_filter_options(ids=False, exclude=False)  # Stats doesn't need ids or exclude
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format",
)
@click.option(
    "--with-analytics",
    is_flag=True,
    help="Include analytics statistics (traffic distribution, trends)",
)
def stats_cmd(
    include_pattern: str,
    in_cluster: str,
    with_status: str,
    with_content_type: str,
    limit: int,
    output_format: str,
    with_analytics: bool,
):
    """
    Show document statistics.

    Examples:
        kurt content stats
        kurt content stats --include "*docs.dagster.io*"
        kurt content stats --format json
        kurt content stats --with-analytics
        kurt content stats --include "*docs.company.com*" --with-analytics
    """
    from kurt.admin.telemetry.analytics import get_analytics_stats
    from kurt.content.document import get_document_stats

    try:
        stats = get_document_stats(
            include_pattern=include_pattern,
            in_cluster=in_cluster,
            with_status=with_status,
            with_content_type=with_content_type,
            limit=limit,
        )

        # Get analytics stats if requested
        if with_analytics:
            analytics_stats = get_analytics_stats(include_pattern=include_pattern)
        else:
            analytics_stats = None

        if output_format == "json":
            import json

            result = {"document_stats": stats}
            if analytics_stats:
                result["analytics_stats"] = analytics_stats
            console.print(json.dumps(result, indent=2))
        else:
            console.print("\n[bold cyan]Document Statistics[/bold cyan]")
            console.print(f"[dim]{'─' * 40}[/dim]")
            if include_pattern:
                console.print(f"[dim]Filter: {include_pattern}[/dim]\n")
            console.print(f"Total Documents:     [bold]{stats['total']}[/bold]")
            console.print(f"  Not Fetched:       [yellow]{stats['not_fetched']}[/yellow]")
            console.print(f"  Fetched:           [green]{stats['fetched']}[/green]")
            console.print(f"  Error:             [red]{stats['error']}[/red]")

            # Show analytics stats if available
            if analytics_stats:
                console.print("\n[bold cyan]Traffic Statistics (30 days)[/bold cyan]")
                console.print(f"[dim]{'─' * 40}[/dim]")

                if analytics_stats["has_data"]:
                    console.print(
                        f"  Total Pageviews:   [bold]{analytics_stats['total_pageviews']:,}[/bold]"
                    )
                    console.print(
                        f"  Average:           {analytics_stats['avg_pageviews']:.1f} views/page"
                    )
                    console.print(
                        f"  Median:            {analytics_stats['median_pageviews']:.0f} views/page"
                    )
                    console.print(
                        f"  P75 (HIGH):        {analytics_stats['p75_pageviews']:.0f} views"
                    )
                    console.print(
                        f"  P25 (LOW):         {analytics_stats['p25_pageviews']:.0f} views"
                    )

                    console.print("\n[bold]Traffic Tiers:[/bold]")
                    zero = analytics_stats["tier_counts"]["zero"]
                    low = analytics_stats["tier_counts"]["low"]
                    medium = analytics_stats["tier_counts"]["medium"]
                    high = analytics_stats["tier_counts"]["high"]
                    total_with_analytics = zero + low + medium + high

                    if total_with_analytics > 0:
                        console.print(
                            f"  ZERO traffic:      {zero:3d} pages ({zero * 100 // total_with_analytics:2d}%)"
                        )
                        console.print(
                            f"  LOW:               {low:3d} pages ({low * 100 // total_with_analytics:2d}%)"
                        )
                        console.print(
                            f"  MEDIUM:            {medium:3d} pages ({medium * 100 // total_with_analytics:2d}%)"
                        )
                        console.print(
                            f"  HIGH:              {high:3d} pages ({high * 100 // total_with_analytics:2d}%)"
                        )

                    console.print("\n[bold]Trends:[/bold]")
                    inc = analytics_stats["trend_counts"]["increasing"]
                    dec = analytics_stats["trend_counts"]["decreasing"]
                    stable = analytics_stats["trend_counts"]["stable"]
                    trend_total = inc + dec + stable

                    if trend_total > 0:
                        console.print(
                            f"  Increasing ↑:      {inc} pages ({inc * 100 // trend_total}%)"
                        )
                        console.print(
                            f"  Stable →:          {stable} pages ({stable * 100 // trend_total}%)"
                        )
                        console.print(
                            f"  Decreasing ↓:      {dec} pages ({dec * 100 // trend_total}%)"
                        )
                else:
                    console.print("[yellow]No analytics data available[/yellow]")
                    console.print(
                        "[dim]Run [cyan]kurt integrations analytics sync[/cyan] to fetch data[/dim]"
                    )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

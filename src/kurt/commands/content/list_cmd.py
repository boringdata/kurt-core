"""List command - View all documents with filters."""

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.command("list")
@click.option(
    "--with-status",
    type=click.Choice(["NOT_FETCHED", "FETCHED", "ERROR"], case_sensitive=False),
    help="Filter by ingestion status (NOT_FETCHED | FETCHED | ERROR)",
)
@click.option(
    "--include",
    "include_pattern",
    type=str,
    help="Filter by URL/path pattern (glob matching source_url or content_path)",
)
@click.option(
    "--in-cluster",
    type=str,
    help="Filter by cluster name",
)
@click.option(
    "--with-content-type",
    type=str,
    help="Filter by content type (tutorial | guide | blog | etc)",
)
@click.option(
    "--max-depth",
    type=int,
    help="Filter by maximum URL depth (e.g., example.com/a/b has depth 2)",
)
@click.option("--limit", type=int, help="Limit number of results")
@click.option("--offset", type=int, default=0, help="Number of documents to skip (for pagination)")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format for AI agents",
)
@click.option(
    "--with-analytics",
    is_flag=True,
    help="Include analytics data (pageviews, trends)",
)
@click.option(
    "--order-by",
    type=click.Choice(["pageviews_30d", "pageviews_60d", "trend_percentage"], case_sensitive=False),
    help="Sort by analytics metric (requires --with-analytics)",
)
@click.option(
    "--min-pageviews",
    type=int,
    help="Minimum pageviews_30d (requires --with-analytics)",
)
@click.option(
    "--max-pageviews",
    type=int,
    help="Maximum pageviews_30d (requires --with-analytics)",
)
@click.option(
    "--trend",
    type=click.Choice(["increasing", "decreasing", "stable"], case_sensitive=False),
    help="Filter by traffic trend (requires --with-analytics)",
)
def list_documents_cmd(
    with_status: str,
    include_pattern: str,
    in_cluster: str,
    with_content_type: str,
    max_depth: int,
    limit: int,
    offset: int,
    output_format: str,
    with_analytics: bool,
    order_by: str,
    min_pageviews: int,
    max_pageviews: int,
    trend: str,
):
    """
    List all your documents.

    Examples:
        kurt content list
        kurt content list --with-status FETCHED
        kurt content list --include "*/docs/*"
        kurt content list --in-cluster "Tutorials"
        kurt content list --with-content-type tutorial
        kurt content list --max-depth 2
        kurt content list --limit 20 --format json

        # With analytics
        kurt content list --with-analytics
        kurt content list --with-analytics --order-by pageviews_30d --limit 10
        kurt content list --with-analytics --trend decreasing --min-pageviews 1000
        kurt content list --with-analytics --max-pageviews 0
    """
    from kurt.content.document import list_content

    try:
        # Validate analytics flags
        if not with_analytics and (order_by or min_pageviews or max_pageviews or trend):
            console.print(
                "[red]Error:[/red] Analytics flags (--order-by, --min-pageviews, "
                "--max-pageviews, --trend) require --with-analytics"
            )
            raise click.Abort()

        # Call ingestion layer function
        docs = list_content(
            with_status=with_status,
            include_pattern=include_pattern,
            in_cluster=in_cluster,
            with_content_type=with_content_type,
            max_depth=max_depth,
            limit=limit,
            offset=offset,
            with_analytics=with_analytics,
            order_by=order_by,
            min_pageviews=min_pageviews,
            max_pageviews=max_pageviews,
            trend=trend,
        )

        if not docs:
            console.print("[yellow]No documents found[/yellow]")
            return

        # Output formatting (presentation layer - stays in command)
        if output_format == "json":
            import json

            print(json.dumps(docs, indent=2, default=str))
        else:
            # Create table
            table = Table(title=f"Documents ({len(docs)} shown)")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Title", style="white")
            table.add_column("Status", style="green")

            # Add analytics columns if requested
            if with_analytics:
                table.add_column("Views (30d)", style="green", justify="right")
                table.add_column("Trend", style="yellow", justify="center")

            table.add_column("Depth", style="magenta", justify="right")
            table.add_column("Count", style="yellow", justify="right")
            table.add_column("URL", style="dim")

            # Calculate child counts for each document (from entire database, not just filtered results)
            from kurt.content.document import list_content
            from kurt.utils.url_utils import get_url_depth

            # Get ALL documents to calculate accurate child counts
            all_docs = list_content()

            # Build a map of URL -> child count
            child_counts = {}
            for doc in docs:
                if doc.source_url:
                    # Count how many docs in the entire database have URLs that start with this URL
                    count = sum(
                        1
                        for d in all_docs
                        if d.source_url
                        and d.source_url != doc.source_url
                        and d.source_url.startswith(doc.source_url.rstrip("/") + "/")
                    )
                    child_counts[doc.source_url] = count

            for doc in docs:
                # Truncate title and URL for display
                title = (
                    (doc.title or "Untitled")[:50] + "..."
                    if doc.title and len(doc.title) > 50
                    else (doc.title or "Untitled")
                )
                url = (
                    doc.source_url[:40] + "..."
                    if doc.source_url and len(doc.source_url) > 40
                    else doc.source_url
                )

                # Calculate URL depth
                depth = get_url_depth(doc.source_url)

                # Get child count
                child_count = child_counts.get(doc.source_url, 0)

                # Color status
                status_str = doc.ingestion_status.value
                if status_str == "FETCHED":
                    status_display = f"[green]{status_str}[/green]"
                elif status_str == "ERROR":
                    status_display = f"[red]{status_str}[/red]"
                else:
                    status_display = f"[yellow]{status_str}[/yellow]"

                # Build row based on whether analytics is included
                if with_analytics:
                    # Get analytics data (if present as dict in doc)
                    analytics = getattr(doc, "analytics", None)

                    if analytics:
                        # Format pageviews with commas
                        pageviews = analytics.get("pageviews_30d", 0) or 0
                        pageviews_str = f"{pageviews:,}"

                        # Trend symbol
                        trend_value = analytics.get("pageviews_trend", "stable")
                        trend_symbols = {
                            "increasing": "↑",
                            "decreasing": "↓",
                            "stable": "→",
                        }
                        trend_str = trend_symbols.get(trend_value, "→")
                    else:
                        pageviews_str = "-"
                        trend_str = "-"

                    table.add_row(
                        str(doc.id)[:8] + "...",
                        title,
                        status_display,
                        pageviews_str,
                        trend_str,
                        str(depth),
                        str(child_count),
                        url or "N/A",
                    )
                else:
                    table.add_row(
                        str(doc.id)[:8] + "...",
                        title,
                        status_display,
                        str(depth),
                        str(child_count),
                        url or "N/A",
                    )

            console.print(table)

            # Show tip for getting full details
            console.print(
                "\n[dim]Tip: Use [cyan]kurt content get <id>[/cyan] for full details[/dim]"
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

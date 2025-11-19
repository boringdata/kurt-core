"""Analytics management CLI commands."""

import json
from datetime import datetime

import click
from rich.console import Console

from kurt.integrations.analytics.service import AnalyticsService

console = Console()


@click.group()
def analytics():
    """Manage analytics integration (PostHog, etc.)."""
    pass


@analytics.command("onboard")
@click.argument("domain")
@click.option("--platform", default="posthog", help="Analytics platform (default: posthog)")
@click.option("--sync-now", is_flag=True, help="Run initial sync after onboarding")
def onboard(domain: str, platform: str, sync_now: bool):
    """
    Onboard a domain for analytics tracking.

    First run: Creates analytics config template in kurt.config
    Second run: Tests connection and registers domain

    Examples:
        kurt integrations analytics onboard docs.company.com
        kurt integrations analytics onboard docs.company.com --platform ga4
    """
    from kurt.config import get_config_file_path
    from kurt.db.database import get_session
    from kurt.db.models import AnalyticsDomain
    from kurt.integrations.analytics.config import (
        add_platform_config,
        analytics_config_exists,
        create_template_config,
        get_platform_config,
        platform_configured,
    )

    console.print(f"\n[bold green]Analytics Onboarding: {platform.capitalize()}[/bold green]\n")

    # Check if config exists
    if not analytics_config_exists():
        console.print("[yellow]No analytics configuration found.[/yellow]")
        console.print("Creating configuration template...\n")

        # Get template and save to config
        template = create_template_config(platform)
        add_platform_config(platform, template)

        config_path = get_config_file_path()
        console.print(f"[green]✓ Template created in:[/green] {config_path}")
        console.print()
        console.print("[yellow]Please fill in your analytics credentials:[/yellow]")
        console.print(f"  1. Open: [cyan]{config_path}[/cyan]")
        console.print(f"  2. Find the ANALYTICS_{platform.upper()}_* variables")
        console.print(f"  3. Replace placeholder values with your {platform} credentials")
        console.print(
            f"  4. Run this command again: [cyan]kurt integrations analytics onboard {domain}[/cyan]"
        )
        console.print()

        # Platform-specific instructions
        if platform == "posthog":
            console.print("[bold]PostHog Setup:[/bold]")
            console.print("  [cyan]ANALYTICS_POSTHOG_PROJECT_ID[/cyan]:")
            console.print("    • Numeric Project ID (e.g., 12345)")
            console.print(
                "    • Find in your PostHog URL: [dim]https://app.posthog.com/project/[cyan]12345[/cyan][/dim]"
            )
            console.print()
            console.print("  [cyan]ANALYTICS_POSTHOG_API_KEY[/cyan]:")
            console.print("    • Go to PostHog → Settings → Project → API Keys")
            console.print("    • Create a new [cyan]Personal API Key[/cyan] with scopes:")
            console.print("      - [cyan]project:read[/cyan] (read project information)")
            console.print("      - [cyan]query:read[/cyan] (query pageview events)")
            console.print()

        console.print("[dim]Note: kurt.config is gitignored and won't be committed.[/dim]")
        return

    # Check if platform configured
    if not platform_configured(platform):
        config_path = get_config_file_path()
        console.print(f"[yellow]{platform.capitalize()} not configured yet.[/yellow]")
        console.print()
        console.print(f"Please fill in credentials in: [cyan]{config_path}[/cyan]")
        console.print(
            f"Look for ANALYTICS_{platform.upper()}_* variables and replace placeholder values."
        )
        console.print(f"Then run: [cyan]kurt integrations analytics onboard {domain}[/cyan]")
        return

    # Load platform config
    try:
        platform_config = get_platform_config(platform)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise click.Abort()

    # Test connection using service
    console.print(f"[dim]Testing {platform} connection...[/dim]")

    try:
        if AnalyticsService.test_platform_connection(platform, platform_config):
            console.print(f"[green]✓ Connected to {platform.capitalize()}[/green]")
        else:
            console.print("[red]✗ Connection failed[/red]")
            console.print("[dim]Check your credentials in kurt.config[/dim]")
            raise click.Abort()

    except NotImplementedError as e:
        console.print(f"[yellow]⚠ {e}[/yellow]")
        console.print("[dim]Skipping connection test...[/dim]")
    except ImportError:
        console.print(
            f"[red]{platform.capitalize()} adapter not available (missing dependencies?)[/red]"
        )
        raise click.Abort()
    except ConnectionError as e:
        console.print("[red]✗ Connection failed[/red]")
        console.print()
        console.print(f"[yellow]{e}[/yellow]")
        console.print()
        console.print(f"[dim]Config file: {get_config_file_path()}[/dim]")
        raise click.Abort()
    except Exception as e:
        console.print("[red]✗ Connection test failed[/red]")
        console.print(f"[yellow]Error: {e}[/yellow]")
        raise click.Abort()

    # Save domain to database (metadata only, credentials in config file)
    console.print("\n[dim]Registering domain...[/dim]")

    with get_session() as session:
        # Check if domain already exists
        existing = session.query(AnalyticsDomain).filter(AnalyticsDomain.domain == domain).first()
        if existing:
            console.print(f"[yellow]Domain already registered: {domain}[/yellow]")
            if not click.confirm("Update registration?", default=False):
                console.print("[dim]Keeping existing registration[/dim]")
                return

        # Register or update domain using service
        AnalyticsService.register_domain(session, domain, platform)
        session.commit()

        console.print(f"[green]✓ Domain registered: {domain}[/green]")

    # Optionally run sync
    if sync_now or click.confirm("\nRun initial sync now?", default=True):
        console.print()
        # Run sync directly
        try:
            _run_sync_for_domain(domain, platform, period=60)
        except Exception as e:
            console.print(f"[yellow]⚠ Initial sync failed: {e}[/yellow]")
            console.print(
                "[dim]You can retry later with: [cyan]kurt integrations analytics sync {domain}[/cyan][/dim]"
            )


def _run_sync_for_domain(domain: str, platform: str = None, period: int = 60):
    """
    Internal helper to run sync for a specific domain.

    Args:
        domain: Domain to sync
        platform: Optional platform override (reads from DB if not provided)
        period: Number of days to sync (default: 60)
    """
    from kurt.db.database import get_session
    from kurt.db.models import AnalyticsDomain
    from kurt.integrations.analytics.config import get_platform_config, platform_configured

    with get_session() as session:
        # Get domain object
        domain_obj = session.query(AnalyticsDomain).filter(AnalyticsDomain.domain == domain).first()
        if not domain_obj:
            console.print(f"[red]Domain not configured: {domain}[/red]")
            console.print(
                f"[dim]Run [cyan]kurt integrations analytics onboard {domain}[/cyan] first[/dim]"
            )
            return

        console.print(f"[bold]Syncing analytics for {domain_obj.domain}[/bold]")

        # Get credentials from config file
        if not platform_configured(domain_obj.platform):
            console.print(
                f"[yellow]⚠ {domain_obj.platform.capitalize()} credentials not found in config file[/yellow]"
            )
            console.print("[dim]Add credentials to kurt.config and try again[/dim]")
            return

        try:
            platform_config = get_platform_config(domain_obj.platform)
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            return

        # Get adapter using service
        try:
            adapter = AnalyticsService.get_adapter_for_platform(
                domain_obj.platform, platform_config
            )
        except (ValueError, NotImplementedError) as e:
            console.print(f"[red]{e}[/red]")
            return
        except ImportError:
            console.print("[red]Analytics adapter not available[/red]")
            return

        # Sync using service
        console.print(
            f"[dim]Querying {domain_obj.platform} for analytics (period: {period} days)...[/dim]"
        )

        try:
            result = AnalyticsService.sync_domain_analytics(
                session, domain_obj, adapter, period_days=period
            )
            session.commit()

            # Always show summary, even if no URLs found
            console.print()
            if result["total_urls"] == 0:
                console.print(f"[yellow]No analytics data found for {domain_obj.domain}[/yellow]")
                console.print()
                console.print("[dim]This could mean:[/dim]")
                console.print(f"  • No pageviews in the last {period} days")
                console.print("  • The domain isn't receiving traffic yet")
                console.print()
            else:
                console.print(f"[dim]Found {result['total_urls']} URL(s) with analytics data[/dim]")
                if result["synced_count"] > 0:
                    console.print(
                        f"[green]✓ Synced analytics for {result['synced_count']} page(s)[/green]"
                    )
                    console.print(
                        f"[dim]Total pageviews (60d): {result['total_pageviews']:,}[/dim]"
                    )
                    console.print()
                    console.print("[dim]Tip: View analytics with:[/dim]")
                    console.print("  [cyan]kurt content list --with-analytics[/cyan]")
                else:
                    console.print("[yellow]Found URLs but couldn't sync analytics[/yellow]")
                console.print()

        except Exception as e:
            console.print(f"[red]Sync failed: {e}[/red]")
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            raise


@analytics.command("sync")
@click.argument("domain", required=False)
@click.option("--all", "sync_all", is_flag=True, help="Sync all configured domains")
@click.option("--force", is_flag=True, help="Re-sync even if recently synced")
@click.option("--period", type=int, default=60, help="Number of days to sync (default: 60)")
def sync(domain: str, sync_all: bool, force: bool, period: int):
    """
    Sync analytics data for a domain.

    Examples:
        kurt analytics sync docs.company.com
        kurt analytics sync --all
        kurt analytics sync docs.company.com --period 90
    """
    from kurt.db.database import get_session
    from kurt.db.models import AnalyticsDomain

    # Determine which domains to sync
    if sync_all:
        with get_session() as session:
            domains = session.query(AnalyticsDomain).all()
            if not domains:
                console.print("[yellow]No domains configured for analytics[/yellow]")
                console.print("[dim]Run [cyan]kurt analytics onboard <domain>[/cyan] first[/dim]")
                return
            # Sync each domain
            for domain_obj in domains:
                try:
                    console.print()
                    _run_sync_for_domain(domain_obj.domain, period=period)
                except Exception:
                    # Error already displayed by _run_sync_for_domain
                    continue
    elif domain:
        # Sync single domain
        _run_sync_for_domain(domain, period=period)
    else:
        console.print("[red]Error: Specify --all or provide a domain[/red]")
        raise click.Abort()


@analytics.command("list")
@click.option("--format", type=click.Choice(["table", "json"]), default="table")
def list_domains(format: str):
    """
    List all analytics-enabled domains.

    Examples:
        kurt analytics list
        kurt analytics list --format json
    """
    from kurt.db.database import get_session
    from kurt.db.models import AnalyticsDomain

    with get_session() as session:
        domains = session.query(AnalyticsDomain).all()

        if not domains:
            console.print("[yellow]No domains configured for analytics[/yellow]")
            console.print(
                "[dim]Run [cyan]kurt analytics onboard <domain>[/cyan] to get started[/dim]"
            )
            return

        if format == "json":
            result = []
            for domain in domains:
                days_since_sync = None
                if domain.last_synced_at:
                    days_since_sync = (datetime.utcnow() - domain.last_synced_at).days

                result.append(
                    {
                        "domain": domain.domain,
                        "platform": domain.platform,
                        "has_data": domain.has_data,
                        "last_synced_at": (
                            domain.last_synced_at.isoformat() if domain.last_synced_at else None
                        ),
                        "days_since_sync": days_since_sync,
                        "sync_period_days": domain.sync_period_days,
                    }
                )
            print(json.dumps(result, indent=2))
        else:
            # Table format
            console.print("\n[bold]Analytics-enabled domains:[/bold]\n")

            for domain in domains:
                console.print(f"[cyan]{domain.domain}[/cyan] ({domain.platform.title()})")

                if domain.last_synced_at:
                    days_ago = (datetime.utcnow() - domain.last_synced_at).days
                    if days_ago == 0:
                        sync_status = "today"
                    elif days_ago == 1:
                        sync_status = "yesterday"
                    else:
                        sync_status = f"{days_ago} days ago"

                    if days_ago > 7:
                        sync_status = f"[yellow]{sync_status} ⚠️[/yellow]"
                    else:
                        sync_status = f"[green]{sync_status}[/green]"

                    console.print(f"  Last synced: {sync_status}")
                else:
                    console.print("  Last synced: [dim]Never[/dim]")

                console.print(
                    f"  Has data: {'[green]Yes[/green]' if domain.has_data else '[dim]No[/dim]'}"
                )
                console.print()


@analytics.command("query")
@click.argument("domain")
@click.option("--url-contains", type=str, help="Filter by URL pattern (case-insensitive)")
@click.option(
    "--min-pageviews",
    type=int,
    help="Minimum pageviews (30d)",
)
@click.option(
    "--max-pageviews",
    type=int,
    help="Maximum pageviews (30d)",
)
@click.option(
    "--trend",
    type=click.Choice(["increasing", "decreasing", "stable"], case_sensitive=False),
    help="Filter by traffic trend",
)
@click.option(
    "--order-by",
    type=click.Choice(["pageviews_30d", "pageviews_60d", "trend_percentage"], case_sensitive=False),
    default="pageviews_30d",
    help="Sort by metric (default: pageviews_30d)",
)
@click.option("--limit", type=int, help="Limit number of results")
@click.option("--offset", type=int, default=0, help="Number of pages to skip (for pagination)")
@click.option(
    "--missing-docs",
    is_flag=True,
    help="Show only pages with analytics but no indexed documents (indexing completeness check)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format",
)
def query_analytics(
    domain: str,
    url_contains: str,
    min_pageviews: int,
    max_pageviews: int,
    trend: str,
    order_by: str,
    limit: int,
    offset: int,
    missing_docs: bool,
    output_format: str,
):
    """
    Query analytics data for a domain.

    Shows all pages with analytics, independent of whether they exist as documents.
    Useful for traffic analysis and indexing completeness checks.

    Examples:
        # All pages with analytics
        kurt integrations analytics query technically.dev

        # Top 10 pages by traffic
        kurt integrations analytics query technically.dev --limit 10

        # Pages with low traffic
        kurt integrations analytics query technically.dev --max-pageviews 100

        # Pages with high traffic
        kurt integrations analytics query technically.dev --min-pageviews 1000

        # Trending up (growing content)
        kurt integrations analytics query technically.dev --trend increasing

        # Filter by URL pattern
        kurt integrations analytics query technically.dev --url-contains "/docs/"

        # Indexing completeness: pages with traffic but not indexed yet
        kurt integrations analytics query technically.dev --missing-docs

        # High-traffic pages you haven't indexed yet
        kurt integrations analytics query technically.dev --missing-docs --min-pageviews 100

        # JSON output for AI agents
        kurt integrations analytics query technically.dev --format json
    """
    from rich.table import Table

    from kurt.db.database import get_session
    from kurt.db.models import AnalyticsDomain, Document, PageAnalytics
    from kurt.integrations.analytics.utils import normalize_url_for_analytics

    with get_session() as session:
        # Verify domain is registered
        domain_obj = session.query(AnalyticsDomain).filter(AnalyticsDomain.domain == domain).first()
        if not domain_obj:
            console.print(f"[red]Domain not configured: {domain}[/red]")
            console.print(
                f"[dim]Run [cyan]kurt integrations analytics onboard {domain}[/cyan] first[/dim]"
            )
            raise click.Abort()

        if not domain_obj.has_data:
            console.print(f"[yellow]No analytics data for {domain}[/yellow]")
            console.print(
                f"[dim]Run [cyan]kurt integrations analytics sync {domain}[/cyan] first[/dim]"
            )
            return

        # Build query
        query = session.query(PageAnalytics).filter(PageAnalytics.domain == domain)

        # If --missing-docs, filter for pages without indexed documents
        if missing_docs:
            # Get all documents to check which analytics URLs have no matching doc
            all_docs = session.query(Document).all()
            doc_urls = {
                normalize_url_for_analytics(doc.source_url) for doc in all_docs if doc.source_url
            }

            # We'll filter in Python after getting all PageAnalytics
            # (SQL JOIN on normalized URL is complex, easier to filter post-query)
            pages = query.all()
            pages = [p for p in pages if p.url not in doc_urls]

            # Apply other filters and sorting in Python
            if url_contains:
                pages = [p for p in pages if url_contains.lower() in p.url.lower()]
            if min_pageviews is not None:
                pages = [p for p in pages if p.pageviews_30d >= min_pageviews]
            if max_pageviews is not None:
                pages = [p for p in pages if p.pageviews_30d <= max_pageviews]
            if trend:
                pages = [p for p in pages if p.pageviews_trend == trend.lower()]

            # Sort
            if order_by == "pageviews_30d":
                pages.sort(key=lambda x: x.pageviews_30d, reverse=True)
            elif order_by == "pageviews_60d":
                pages.sort(key=lambda x: x.pageviews_60d, reverse=True)
            elif order_by == "trend_percentage":
                pages.sort(
                    key=lambda x: x.trend_percentage if x.trend_percentage else float("-inf"),
                    reverse=True,
                )

            # Pagination
            total_count = len(pages)
            if offset or limit:
                start = offset
                end = offset + limit if limit else None
                pages = pages[start:end]
        else:
            # Normal query path (SQL filters)
            # Apply filters
            if url_contains:
                query = query.filter(PageAnalytics.url.ilike(f"%{url_contains}%"))

            if min_pageviews is not None:
                query = query.filter(PageAnalytics.pageviews_30d >= min_pageviews)

            if max_pageviews is not None:
                query = query.filter(PageAnalytics.pageviews_30d <= max_pageviews)

            if trend:
                query = query.filter(PageAnalytics.pageviews_trend == trend.lower())

            # Apply ordering
            if order_by == "pageviews_30d":
                query = query.order_by(PageAnalytics.pageviews_30d.desc())
            elif order_by == "pageviews_60d":
                query = query.order_by(PageAnalytics.pageviews_60d.desc())
            elif order_by == "trend_percentage":
                query = query.order_by(PageAnalytics.trend_percentage.desc().nullslast())

            # Apply pagination
            total_count = query.count()
            query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            pages = query.all()

        if not pages:
            console.print("[yellow]No pages found matching filters[/yellow]")
            return

        # Output formatting
        if output_format == "json":
            result = []
            for page in pages:
                result.append(
                    {
                        "url": page.url,
                        "domain": page.domain,
                        "pageviews_30d": page.pageviews_30d,
                        "pageviews_60d": page.pageviews_60d,
                        "pageviews_previous_30d": page.pageviews_previous_30d,
                        "unique_visitors_30d": page.unique_visitors_30d,
                        "unique_visitors_60d": page.unique_visitors_60d,
                        "trend": page.pageviews_trend,
                        "trend_percentage": page.trend_percentage,
                        "bounce_rate": page.bounce_rate,
                        "avg_session_duration_seconds": page.avg_session_duration_seconds,
                        "period_start": page.period_start.isoformat()
                        if page.period_start
                        else None,
                        "period_end": page.period_end.isoformat() if page.period_end else None,
                        "synced_at": page.synced_at.isoformat() if page.synced_at else None,
                    }
                )
            print(json.dumps(result, indent=2))
        else:
            # Table format
            title_suffix = " - Not Indexed" if missing_docs else ""
            table = Table(
                title=f"Analytics for {domain}{title_suffix} ({len(pages)} shown, {total_count} total)"
            )
            table.add_column("URL", style="cyan", no_wrap=False)
            table.add_column("Views (30d)", style="green", justify="right")
            table.add_column("Views (60d)", style="green", justify="right")
            table.add_column("Trend", style="yellow", justify="center")

            for page in pages:
                # Truncate URL for display
                url_display = page.url[:80] + "..." if len(page.url) > 80 else page.url

                # Format pageviews with commas
                pv_30d = f"{page.pageviews_30d:,}"
                pv_60d = f"{page.pageviews_60d:,}"

                # Trend symbol
                trend_symbols = {
                    "increasing": "↑",
                    "decreasing": "↓",
                    "stable": "→",
                }
                trend_display = trend_symbols.get(page.pageviews_trend, "→")
                if page.trend_percentage is not None:
                    trend_display = f"{trend_display} {page.trend_percentage:+.1f}%"

                table.add_row(url_display, pv_30d, pv_60d, trend_display)

            console.print(table)
            console.print(
                "\n[dim]Tip: Use [cyan]--url-contains[/cyan], [cyan]--min-pageviews[/cyan], "
                "or [cyan]--trend[/cyan] to filter results[/dim]"
            )

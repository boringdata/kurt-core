"""CLI commands for domain analytics integration."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from kurt_new.cli.options import format_option, limit_option

console = Console()


@click.group()
def analytics_group():
    """
    Domain analytics integration commands.

    \b
    Commands:
      onboard   Configure analytics credentials
      sync      Sync analytics data for a domain
      list      List analytics-enabled domains
      query     Query analytics data
    """
    pass


@analytics_group.command("onboard")
@click.argument("domain")
@click.option("--platform", default="posthog", help="Analytics platform (posthog, ga4, plausible)")
@click.option("--sync-now", is_flag=True, help="Run initial sync after onboarding")
def onboard_cmd(domain: str, platform: str, sync_now: bool):
    """
    Configure analytics for a domain.

    \b
    Examples:
        kurt integrations analytics onboard docs.company.com
        kurt integrations analytics onboard docs.company.com --platform ga4
    """
    from kurt_new.config import get_config_file_path

    from . import test_platform_connection
    from .config import (
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

        template = create_template_config(platform)
        add_platform_config(platform, template)

        config_path = get_config_file_path()
        console.print(f"[green]✓ Template created in:[/green] {config_path}")
        console.print()
        console.print("[yellow]Please fill in your analytics credentials:[/yellow]")
        console.print(f"  1. Open: [cyan]{config_path}[/cyan]")
        console.print(f"  2. Find ANALYTICS_{platform.upper()}_* variables")
        console.print("  3. Replace placeholder values")
        console.print(f"  4. Run again: [cyan]kurt integrations analytics onboard {domain}[/cyan]")

        if platform == "posthog":
            console.print("\n[bold]PostHog Setup:[/bold]")
            console.print("  PROJECT_ID: Found in your PostHog URL")
            console.print("  API_KEY: Settings → Project → API Keys → Create Personal API Key")
        return

    # Check if platform configured
    if not platform_configured(platform):
        config_path = get_config_file_path()
        console.print(f"[yellow]{platform.capitalize()} not configured yet.[/yellow]")
        console.print(f"\nPlease fill in credentials in: [cyan]{config_path}[/cyan]")
        return

    # Test connection
    try:
        platform_config = get_platform_config(platform)
        console.print(f"[dim]Testing {platform} connection...[/dim]")

        if test_platform_connection(platform, platform_config):
            console.print(f"[green]✓ Connected to {platform.capitalize()}[/green]")
        else:
            console.print("[red]✗ Connection failed[/red]")
            raise click.Abort()

    except ConnectionError as e:
        console.print("[red]✗ Connection failed[/red]")
        console.print(f"[yellow]{e}[/yellow]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

    # Register domain in database
    console.print("\n[dim]Registering domain...[/dim]")

    from kurt_new.db import managed_session
    from kurt_new.db.models import AnalyticsDomain

    with managed_session() as session:
        existing = session.query(AnalyticsDomain).filter(AnalyticsDomain.domain == domain).first()
        if existing:
            console.print(f"[yellow]Domain already registered: {domain}[/yellow]")
            if not click.confirm("Update registration?", default=False):
                return

            existing.platform = platform
        else:
            domain_obj = AnalyticsDomain(domain=domain, platform=platform)
            session.add(domain_obj)

        session.commit()
        console.print(f"[green]✓ Domain registered: {domain}[/green]")

    # Optionally run sync
    if sync_now or click.confirm("\nRun initial sync now?", default=True):
        _run_sync(domain, platform)


def _run_sync(domain: str, platform: str = None, period: int = 60):
    """Internal helper to sync analytics for a domain."""
    from kurt_new.db import managed_session
    from kurt_new.db.models import AnalyticsDomain

    from . import get_adapter, sync_domain_metrics
    from .config import get_platform_config, platform_configured

    with managed_session() as session:
        domain_obj = session.query(AnalyticsDomain).filter(AnalyticsDomain.domain == domain).first()
        if not domain_obj:
            console.print(f"[red]Domain not configured: {domain}[/red]")
            return

        if not platform_configured(domain_obj.platform):
            console.print(f"[yellow]⚠ {domain_obj.platform} credentials not found[/yellow]")
            return

        console.print(f"[bold]Syncing analytics for {domain_obj.domain}[/bold]")

        try:
            platform_config = get_platform_config(domain_obj.platform)
            adapter = get_adapter(domain_obj.platform, platform_config)

            console.print(f"[dim]Querying {domain_obj.platform} (period: {period} days)...[/dim]")

            result = sync_domain_metrics(session, domain_obj, adapter, period_days=period)
            session.commit()

            if result["total_urls"] == 0:
                console.print(f"[yellow]No analytics data found for {domain}[/yellow]")
            else:
                console.print(f"[dim]Found {result['total_urls']} URL(s)[/dim]")
                if result["synced_count"] > 0:
                    console.print(f"[green]✓ Synced {result['synced_count']} page(s)[/green]")
                    console.print(
                        f"[dim]Total pageviews (60d): {result['total_pageviews']:,}[/dim]"
                    )

        except Exception as e:
            console.print(f"[red]Sync failed: {e}[/red]")
            raise


@analytics_group.command("sync")
@click.argument("domain", required=False)
@click.option("--all", "sync_all", is_flag=True, help="Sync all configured domains")
@click.option("--period", type=int, default=60, help="Days to sync (default: 60)")
def sync_cmd(domain: str, sync_all: bool, period: int):
    """
    Sync analytics data for a domain.

    \b
    Examples:
        kurt integrations analytics sync docs.company.com
        kurt integrations analytics sync --all
        kurt integrations analytics sync docs.company.com --period 90
    """
    from kurt_new.db import managed_session
    from kurt_new.db.models import AnalyticsDomain

    if sync_all:
        with managed_session() as session:
            domains = session.query(AnalyticsDomain).all()
            if not domains:
                console.print("[yellow]No domains configured[/yellow]")
                return

            for domain_obj in domains:
                try:
                    console.print()
                    _run_sync(domain_obj.domain, period=period)
                except Exception:
                    continue
    elif domain:
        _run_sync(domain, period=period)
    else:
        console.print("[red]Error: Specify --all or provide a domain[/red]")
        raise click.Abort()


@analytics_group.command("list")
@format_option
def list_cmd(output_format: str):
    """
    List analytics-enabled domains.

    \b
    Examples:
        kurt integrations analytics list
        kurt integrations analytics list --format json
    """
    from kurt_new.db import managed_session
    from kurt_new.db.models import AnalyticsDomain

    with managed_session() as session:
        domains = session.query(AnalyticsDomain).all()

        if not domains:
            console.print("[yellow]No domains configured[/yellow]")
            console.print(
                "[dim]Run [cyan]kurt integrations analytics onboard <domain>[/cyan][/dim]"
            )
            return

        if output_format == "json":
            result = []
            for d in domains:
                days_since = None
                if d.last_synced_at:
                    days_since = (datetime.utcnow() - d.last_synced_at).days
                result.append(
                    {
                        "domain": d.domain,
                        "platform": d.platform,
                        "has_data": d.has_data,
                        "last_synced_at": d.last_synced_at.isoformat()
                        if d.last_synced_at
                        else None,
                        "days_since_sync": days_since,
                    }
                )
            print(json.dumps(result, indent=2))
        else:
            console.print("\n[bold]Analytics-enabled domains:[/bold]\n")
            for d in domains:
                console.print(f"[cyan]{d.domain}[/cyan] ({d.platform.title()})")

                if d.last_synced_at:
                    days_ago = (datetime.utcnow() - d.last_synced_at).days
                    sync_status = "today" if days_ago == 0 else f"{days_ago} days ago"
                    if days_ago > 7:
                        sync_status = f"[yellow]{sync_status} ⚠[/yellow]"
                    else:
                        sync_status = f"[green]{sync_status}[/green]"
                    console.print(f"  Last synced: {sync_status}")
                else:
                    console.print("  Last synced: [dim]Never[/dim]")

                has_data = "[green]Yes[/green]" if d.has_data else "[dim]No[/dim]"
                console.print(f"  Has data: {has_data}")
                console.print()


@analytics_group.command("query")
@click.argument("domain")
@click.option("--url-contains", help="Filter by URL pattern")
@click.option("--min-pageviews", type=int, help="Minimum pageviews (30d)")
@click.option("--max-pageviews", type=int, help="Maximum pageviews (30d)")
@click.option(
    "--trend", type=click.Choice(["increasing", "decreasing", "stable"]), help="Traffic trend"
)
@click.option(
    "--order-by",
    type=click.Choice(["pageviews_30d", "pageviews_60d", "trend_percentage"]),
    default="pageviews_30d",
)
@limit_option
@format_option
def query_cmd(
    domain: str,
    url_contains: Optional[str],
    min_pageviews: Optional[int],
    max_pageviews: Optional[int],
    trend: Optional[str],
    order_by: str,
    limit: Optional[int],
    output_format: str,
):
    """
    Query analytics data for a domain.

    \b
    Examples:
        kurt integrations analytics query docs.company.com
        kurt integrations analytics query docs.company.com --limit 10
        kurt integrations analytics query docs.company.com --min-pageviews 1000
        kurt integrations analytics query docs.company.com --trend increasing
        kurt integrations analytics query docs.company.com --url-contains "/docs/"
    """
    from kurt_new.db import managed_session
    from kurt_new.db.models import AnalyticsDomain, PageAnalytics

    with managed_session() as session:
        domain_obj = session.query(AnalyticsDomain).filter(AnalyticsDomain.domain == domain).first()
        if not domain_obj:
            console.print(f"[red]Domain not configured: {domain}[/red]")
            raise click.Abort()

        if not domain_obj.has_data:
            console.print(f"[yellow]No analytics data for {domain}[/yellow]")
            console.print(f"[dim]Run [cyan]kurt integrations analytics sync {domain}[/cyan][/dim]")
            return

        # Build query
        query = session.query(PageAnalytics).filter(PageAnalytics.domain == domain)

        if url_contains:
            query = query.filter(PageAnalytics.url.ilike(f"%{url_contains}%"))
        if min_pageviews is not None:
            query = query.filter(PageAnalytics.pageviews_30d >= min_pageviews)
        if max_pageviews is not None:
            query = query.filter(PageAnalytics.pageviews_30d <= max_pageviews)
        if trend:
            query = query.filter(PageAnalytics.pageviews_trend == trend.lower())

        # Order
        if order_by == "pageviews_30d":
            query = query.order_by(PageAnalytics.pageviews_30d.desc())
        elif order_by == "pageviews_60d":
            query = query.order_by(PageAnalytics.pageviews_60d.desc())
        elif order_by == "trend_percentage":
            query = query.order_by(PageAnalytics.trend_percentage.desc().nullslast())

        total_count = query.count()
        if limit:
            query = query.limit(limit)

        pages = query.all()

        if not pages:
            console.print("[yellow]No pages found matching filters[/yellow]")
            return

        if output_format == "json":
            result = []
            for p in pages:
                result.append(
                    {
                        "url": p.url,
                        "pageviews_30d": p.pageviews_30d,
                        "pageviews_60d": p.pageviews_60d,
                        "trend": p.pageviews_trend,
                        "trend_percentage": p.trend_percentage,
                    }
                )
            print(json.dumps(result, indent=2))
        else:
            table = Table(title=f"Analytics for {domain} ({len(pages)} shown, {total_count} total)")
            table.add_column("URL", style="cyan", no_wrap=False)
            table.add_column("Views (30d)", style="green", justify="right")
            table.add_column("Views (60d)", style="green", justify="right")
            table.add_column("Trend", style="yellow", justify="center")

            for p in pages:
                url_display = p.url[:80] + "..." if len(p.url) > 80 else p.url
                trend_symbols = {"increasing": "↑", "decreasing": "↓", "stable": "→"}
                trend_display = trend_symbols.get(p.pageviews_trend, "→")
                if p.trend_percentage is not None:
                    trend_display = f"{trend_display} {p.trend_percentage:+.1f}%"

                table.add_row(
                    url_display, f"{p.pageviews_30d:,}", f"{p.pageviews_60d:,}", trend_display
                )

            console.print(table)

"""Analytics management CLI commands."""

import json
from datetime import datetime

import click
from rich.console import Console
from rich.table import Table

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

    First run: Creates .kurt/analytics-config.json template
    Second run: Tests connection and registers domain

    Examples:
        kurt analytics onboard docs.company.com
        kurt analytics onboard docs.company.com --platform ga4
    """
    from kurt.analytics.config import (
        analytics_config_exists,
        create_template_config,
        get_analytics_config_path,
        get_platform_config,
        platform_configured,
    )
    from kurt.db.database import get_session
    from kurt.db.models import AnalyticsDomain

    console.print(f"\n[bold green]Analytics Onboarding: {platform.capitalize()}[/bold green]\n")

    # Check if config exists
    if not analytics_config_exists():
        console.print("[yellow]No analytics configuration found.[/yellow]")
        console.print("Creating configuration file...\n")

        config_path = create_template_config(platform)
        console.print(f"[green]✓ Created:[/green] {config_path}")
        console.print()
        console.print("[yellow]Please fill in your analytics credentials:[/yellow]")
        console.print(f"  1. Open: [cyan]{config_path}[/cyan]")
        console.print(f"  2. Replace placeholder values with your {platform} credentials")
        console.print("  3. Run this command again: [cyan]kurt analytics onboard {domain}[/cyan]")
        console.print()
        console.print("[dim]Note: This file is gitignored and won't be committed.[/dim]")
        return

    # Check if platform configured
    if not platform_configured(platform):
        config_path = get_analytics_config_path()
        console.print(f"[yellow]{platform.capitalize()} not configured yet.[/yellow]")
        console.print()
        console.print(f"Please fill in credentials in: [cyan]{config_path}[/cyan]")
        console.print(f"Then run: [cyan]kurt analytics onboard {domain}[/cyan]")
        return

    # Load platform config
    try:
        platform_config = get_platform_config(platform)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise click.Abort()

    # Extract credentials based on platform
    if platform == "posthog":
        project_id = platform_config.get("project_id")
        api_key = platform_config.get("api_key")
    elif platform == "ga4":
        project_id = platform_config.get("property_id")
        api_key = platform_config.get("credentials_file")
    elif platform == "plausible":
        project_id = platform_config.get("site_id")
        api_key = platform_config.get("api_key")
    else:
        console.print(f"[red]Unsupported platform: {platform}[/red]")
        raise click.Abort()

    # Test connection
    console.print(f"[dim]Testing {platform} connection...[/dim]")

    try:
        if platform == "posthog":
            from kurt.analytics.adapters.posthog import PostHogAdapter

            adapter = PostHogAdapter(project_id, api_key)
            if not adapter.test_connection():
                console.print("[red]✗ Connection failed[/red]")
                console.print(
                    "[dim]Check your credentials in .kurt/analytics-config.json[/dim]"
                )
                raise click.Abort()

            console.print("[green]✓ Connected to PostHog[/green]")
        else:
            console.print(f"[yellow]⚠ Connection test not implemented for {platform}[/yellow]")
            console.print("[dim]Skipping connection test...[/dim]")

    except ImportError:
        console.print(f"[red]{platform.capitalize()} adapter not available (missing dependencies?)[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Connection test failed: {e}[/red]")
        raise click.Abort()

    # Save domain to database (metadata only, credentials in config file)
    console.print("\n[dim]Registering domain...[/dim]")

    session = get_session()

    # Check if domain already exists
    existing = session.get(AnalyticsDomain, domain)
    if existing:
        console.print(f"[yellow]Domain already registered: {domain}[/yellow]")
        if not click.confirm("Update registration?", default=False):
            console.print("[dim]Keeping existing registration[/dim]")
            return
        # Update existing
        existing.platform = platform
        existing.updated_at = datetime.utcnow()
        session.add(existing)
    else:
        # Create new
        analytics_domain = AnalyticsDomain(
            domain=domain,
            platform=platform,
            has_data=False,  # Will be set to True after first sync
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(analytics_domain)

    session.commit()

    console.print(f"[green]✓ Domain registered: {domain}[/green]")

    # Optionally run sync
    if sync_now or click.confirm("\nRun initial sync now?", default=True):
        console.print()
        # Import and run sync command
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(sync, [domain])
        if result.exit_code != 0:
            console.print("[yellow]⚠ Initial sync failed (you can retry later)[/yellow]")


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
    from kurt.db.models import AnalyticsDomain, Document, DocumentAnalytics

    session = get_session()

    # Determine which domains to sync
    if sync_all:
        domains = session.query(AnalyticsDomain).all()
        if not domains:
            console.print("[yellow]No domains configured for analytics[/yellow]")
            console.print("[dim]Run [cyan]kurt analytics onboard <domain>[/cyan] first[/dim]")
            return
    elif domain:
        domain_obj = session.get(AnalyticsDomain, domain)
        if not domain_obj:
            console.print(f"[red]Domain not configured: {domain}[/red]")
            console.print("[dim]Run [cyan]kurt analytics onboard {domain}[/cyan] first[/dim]")
            raise click.Abort()
        domains = [domain_obj]
    else:
        console.print("[red]Error: Specify --all or provide a domain[/red]")
        raise click.Abort()

    # Sync each domain
    for domain_obj in domains:
        console.print(f"\n[bold]Syncing analytics for {domain_obj.domain}[/bold]")

        # Get credentials from config file
        from kurt.analytics.config import get_platform_config, platform_configured

        if not platform_configured(domain_obj.platform):
            console.print(
                f"[yellow]⚠ {domain_obj.platform.capitalize()} credentials not found in config file[/yellow]"
            )
            console.print(
                f"[dim]Add credentials to .kurt/analytics-config.json and try again[/dim]"
            )
            continue

        try:
            platform_config = get_platform_config(domain_obj.platform)
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            continue

        # Get adapter with credentials from config
        try:
            if domain_obj.platform == "posthog":
                from kurt.analytics.adapters.posthog import PostHogAdapter

                adapter = PostHogAdapter(
                    platform_config["project_id"], platform_config["api_key"]
                )
            else:
                console.print(f"[red]Unknown platform: {domain_obj.platform}[/red]")
                continue
        except ImportError:
            console.print("[red]Analytics adapter not available[/red]")
            continue

        # Get all documents for this domain
        from kurt.analytics.utils import normalize_url_for_analytics

        docs = (
            session.query(Document)
            .filter(Document.source_url.startswith(f"https://{domain_obj.domain}"))
            .all()
        )

        # Also check http and www variants
        docs += (
            session.query(Document)
            .filter(Document.source_url.startswith(f"http://{domain_obj.domain}"))
            .all()
        )
        docs += (
            session.query(Document)
            .filter(Document.source_url.startswith(f"https://www.{domain_obj.domain}"))
            .all()
        )

        # Deduplicate by ID
        docs = list({doc.id: doc for doc in docs}.values())

        if not docs:
            console.print(f"[yellow]No documents found for {domain_obj.domain}[/yellow]")
            continue

        console.print(f"[dim]Found {len(docs)} documents[/dim]")

        # Sync metrics
        console.print(f"[dim]Querying {domain_obj.platform} (period: {period} days)...[/dim]")

        try:
            urls = [doc.source_url for doc in docs if doc.source_url]
            metrics_map = adapter.sync_metrics(urls, period_days=period)

            # Update or create DocumentAnalytics records
            synced_count = 0
            for doc in docs:
                if doc.source_url in metrics_map:
                    metrics = metrics_map[doc.source_url]

                    # Check if analytics record exists
                    existing = (
                        session.query(DocumentAnalytics)
                        .filter(DocumentAnalytics.document_id == doc.id)
                        .first()
                    )

                    if existing:
                        # Update existing
                        existing.pageviews_60d = metrics.pageviews_60d
                        existing.pageviews_30d = metrics.pageviews_30d
                        existing.pageviews_previous_30d = metrics.pageviews_previous_30d
                        existing.unique_visitors_60d = metrics.unique_visitors_60d
                        existing.unique_visitors_30d = metrics.unique_visitors_30d
                        existing.unique_visitors_previous_30d = (
                            metrics.unique_visitors_previous_30d
                        )
                        existing.avg_session_duration_seconds = (
                            metrics.avg_session_duration_seconds
                        )
                        existing.bounce_rate = metrics.bounce_rate
                        existing.pageviews_trend = metrics.pageviews_trend
                        existing.trend_percentage = metrics.trend_percentage
                        existing.period_start = metrics.period_start
                        existing.period_end = metrics.period_end
                        existing.synced_at = datetime.utcnow()
                        session.add(existing)
                    else:
                        # Create new
                        from uuid import uuid4

                        new_analytics = DocumentAnalytics(
                            id=uuid4(),
                            document_id=doc.id,
                            pageviews_60d=metrics.pageviews_60d,
                            pageviews_30d=metrics.pageviews_30d,
                            pageviews_previous_30d=metrics.pageviews_previous_30d,
                            unique_visitors_60d=metrics.unique_visitors_60d,
                            unique_visitors_30d=metrics.unique_visitors_30d,
                            unique_visitors_previous_30d=metrics.unique_visitors_previous_30d,
                            avg_session_duration_seconds=metrics.avg_session_duration_seconds,
                            bounce_rate=metrics.bounce_rate,
                            pageviews_trend=metrics.pageviews_trend,
                            trend_percentage=metrics.trend_percentage,
                            period_start=metrics.period_start,
                            period_end=metrics.period_end,
                            synced_at=datetime.utcnow(),
                        )
                        session.add(new_analytics)

                    synced_count += 1

            # Update domain last_synced_at
            domain_obj.last_synced_at = datetime.utcnow()
            domain_obj.has_data = True
            session.add(domain_obj)

            session.commit()

            console.print(f"[green]✓ Synced {synced_count} documents[/green]")

            # Show summary
            total_pageviews = sum(
                m.pageviews_60d for m in metrics_map.values() if m.pageviews_60d > 0
            )
            console.print(f"[dim]Total pageviews (60d): {total_pageviews:,}[/dim]")

        except Exception as e:
            console.print(f"[red]Sync failed: {e}[/red]")
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")


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

    session = get_session()
    domains = session.query(AnalyticsDomain).all()

    if not domains:
        console.print("[yellow]No domains configured for analytics[/yellow]")
        console.print("[dim]Run [cyan]kurt analytics onboard <domain>[/cyan] to get started[/dim]")
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

            console.print(f"  Has data: {'[green]Yes[/green]' if domain.has_data else '[dim]No[/dim]'}")
            console.print()

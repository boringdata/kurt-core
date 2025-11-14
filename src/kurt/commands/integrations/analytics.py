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

    First run: Creates .kurt/analytics-config.json template
    Second run: Tests connection and registers domain

    Examples:
        kurt integrations analytics onboard docs.company.com
        kurt integrations analytics onboard docs.company.com --platform ga4
    """
    from kurt.db.database import get_session
    from kurt.db.models import AnalyticsDomain
    from kurt.integrations.analytics.config import (
        analytics_config_exists,
        create_template_config,
        get_analytics_config_path,
        get_platform_config,
        platform_configured,
    )

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
        console.print(
            "  3. Run this command again: [cyan]kurt integrations analytics onboard {domain}[/cyan]"
        )
        console.print()
        console.print("[dim]Note: This file is gitignored and won't be committed.[/dim]")
        return

    # Check if platform configured
    if not platform_configured(platform):
        config_path = get_analytics_config_path()
        console.print(f"[yellow]{platform.capitalize()} not configured yet.[/yellow]")
        console.print()
        console.print(f"Please fill in credentials in: [cyan]{config_path}[/cyan]")
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
    except Exception as e:
        console.print(f"[red]Connection test failed: {e}[/red]")
        raise click.Abort()

    # Save domain to database (metadata only, credentials in config file)
    console.print("\n[dim]Registering domain...[/dim]")

    session = get_session()

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
    from kurt.db.models import AnalyticsDomain

    session = get_session()

    # Determine which domains to sync
    if sync_all:
        domains = session.query(AnalyticsDomain).all()
        if not domains:
            console.print("[yellow]No domains configured for analytics[/yellow]")
            console.print("[dim]Run [cyan]kurt analytics onboard <domain>[/cyan] first[/dim]")
            return
    elif domain:
        domain_obj = session.query(AnalyticsDomain).filter(AnalyticsDomain.domain == domain).first()
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
        from kurt.integrations.analytics.config import get_platform_config, platform_configured

        if not platform_configured(domain_obj.platform):
            console.print(
                f"[yellow]⚠ {domain_obj.platform.capitalize()} credentials not found in config file[/yellow]"
            )
            console.print("[dim]Add credentials to .kurt/analytics-config.json and try again[/dim]")
            continue

        try:
            platform_config = get_platform_config(domain_obj.platform)
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            continue

        # Get adapter using service
        try:
            adapter = AnalyticsService.get_adapter_for_platform(
                domain_obj.platform, platform_config
            )
        except (ValueError, NotImplementedError) as e:
            console.print(f"[red]{e}[/red]")
            continue
        except ImportError:
            console.print("[red]Analytics adapter not available[/red]")
            continue

        # Sync using service
        console.print(f"[dim]Querying {domain_obj.platform} (period: {period} days)...[/dim]")

        try:
            result = AnalyticsService.sync_domain_analytics(
                session, domain_obj, adapter, period_days=period
            )
            session.commit()

            if result["total_documents"] == 0:
                console.print(f"[yellow]No documents found for {domain_obj.domain}[/yellow]")
                continue

            console.print(f"[dim]Found {result['total_documents']} documents[/dim]")
            console.print(f"[green]✓ Synced {result['synced_count']} documents[/green]")
            console.print(f"[dim]Total pageviews (60d): {result['total_pageviews']:,}[/dim]")

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

            console.print(
                f"  Has data: {'[green]Yes[/green]' if domain.has_data else '[dim]No[/dim]'}"
            )
            console.print()

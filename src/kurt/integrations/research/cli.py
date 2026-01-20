"""CLI commands for research integration setup."""

from __future__ import annotations

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command

console = Console()


@click.group()
def research_group():
    """
    Research integration setup commands.

    \b
    Commands:
      onboard   Configure research API credentials
      status    Show configured research sources
    """
    pass


@research_group.command("onboard")
@click.option(
    "--source",
    default="perplexity",
    type=click.Choice(["perplexity", "apify"]),
    help="Research source to configure",
)
@track_command
def onboard_cmd(source: str):
    """
    Configure research API credentials.

    \b
    Examples:
        kurt integrations research onboard
        kurt integrations research onboard --source perplexity
    """
    from kurt.config import get_config_file_path

    from .config import (
        add_source_config,
        create_template_config,
        get_source_config,
        research_config_exists,
        source_configured,
    )

    console.print(f"\n[bold green]Research Onboarding: {source.capitalize()}[/bold green]\n")

    # Check if config exists
    if not research_config_exists() or not source_configured(source):
        console.print(f"[yellow]No configuration found for {source}.[/yellow]")
        console.print("Creating configuration template...\n")

        template = create_template_config(source)
        add_source_config(source, template)

        config_path = get_config_file_path()
        console.print(f"[green]\u2713 Template created in:[/green] {config_path}")
        console.print()
        console.print("[yellow]Please fill in your API credentials:[/yellow]")
        console.print(f"  1. Open: [cyan]{config_path}[/cyan]")
        console.print(f"  2. Find RESEARCH_{source.upper()}_* variables")
        console.print("  3. Replace placeholder values")
        console.print(
            f"  4. Run again: [cyan]kurt integrations research onboard --source {source}[/cyan]"
        )

        if source == "perplexity":
            console.print("\n[bold]Perplexity Setup:[/bold]")
            console.print("  API_KEY: Get from https://www.perplexity.ai/settings/api")
            console.print("  DEFAULT_MODEL: sonar-reasoning (recommended)")
        elif source == "apify":
            console.print("\n[bold]Apify Setup:[/bold]")
            console.print("  API_TOKEN: Get from https://console.apify.com/account/integrations")
            console.print("  DEFAULT_ACTOR: apidojo/tweet-scraper (Twitter/X search)")
        return

    # Test connection
    try:
        source_config = get_source_config(source)
        console.print(f"[dim]Testing {source} connection...[/dim]")

        if source == "perplexity":
            from .perplexity import PerplexityAdapter

            adapter = PerplexityAdapter(source_config)
            if adapter.test_connection():
                console.print(f"[green]\u2713 Connected to {source.capitalize()}[/green]")
            else:
                console.print("[red]\u2717 Connection failed[/red]")
                raise click.Abort()
        elif source == "apify":
            from .monitoring.apify import ApifyAdapter

            adapter = ApifyAdapter(source_config)
            if adapter.test_connection():
                console.print(f"[green]\u2713 Connected to {source.capitalize()}[/green]")
                # Show account info
                user_info = adapter.get_user_info()
                if user_info:
                    username = user_info.get("username", "unknown")
                    console.print(f"[dim]  Account: {username}[/dim]")
            else:
                console.print("[red]\u2717 Connection failed - check your API token[/red]")
                raise click.Abort()
        else:
            console.print(f"[yellow]No connection test available for {source}[/yellow]")

    except ValueError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Connection test failed:[/red] {e}")
        raise click.Abort()

    console.print(f"\n[green]\u2713 {source.capitalize()} is configured and ready![/green]")


@research_group.command("status")
@track_command
def status_cmd():
    """
    Show configured research sources.

    \b
    Examples:
        kurt integrations research status
    """
    from .config import list_sources, source_configured

    console.print("\n[bold]Research Sources Status[/bold]\n")

    sources = list_sources()

    if not sources:
        console.print("[yellow]No research sources configured.[/yellow]")
        console.print(
            "[dim]Run [cyan]kurt integrations research onboard[/cyan] to get started.[/dim]"
        )
        return

    # Check each known source
    known_sources = ["perplexity", "apify"]

    for source in known_sources:
        if source_configured(source):
            console.print(
                f"  [green]\u2713[/green] {source.capitalize()} - [green]Configured[/green]"
            )
        elif source in sources:
            console.print(
                f"  [yellow]![/yellow] {source.capitalize()} - [yellow]Needs configuration[/yellow]"
            )
        else:
            console.print(f"  [dim]-[/dim] {source.capitalize()} - [dim]Not configured[/dim]")

    console.print()


@research_group.command("apify")
@click.option("--query", "-q", required=True, help="Search term or hashtag")
@click.option(
    "--platform",
    "-p",
    type=click.Choice(["twitter", "linkedin", "threads"]),
    default="twitter",
    help="Social platform to search",
)
@click.option("--max-items", default=20, help="Maximum items to fetch")
@click.option("--output", "-o", type=click.Path(), help="Output file (JSON)")
@track_command
def apify_cmd(query: str, platform: str, max_items: int, output: str | None):
    """
    Search social media via Apify actors.

    \b
    Examples:
        kurt integrations research apify -q "AI agents"
        kurt integrations research apify -q "#devtools" --platform twitter
        kurt integrations research apify -q "machine learning" -p linkedin --max-items 50
        kurt integrations research apify -q "startup" -o results.json
    """
    import json

    from .config import get_source_config, source_configured
    from .monitoring.apify import ApifyAdapter

    # Check configuration
    if not source_configured("apify"):
        console.print("[yellow]Apify not configured.[/yellow]")
        console.print("Run: [cyan]kurt integrations research onboard --source apify[/cyan]")
        raise click.Abort()

    try:
        config = get_source_config("apify")
        adapter = ApifyAdapter(config)

        console.print(f"[dim]Searching {platform} for: {query}...[/dim]")

        # Use platform-specific method
        if platform == "twitter":
            signals = adapter.search_twitter(query, max_items=max_items)
        elif platform == "linkedin":
            signals = adapter.search_linkedin(query, max_items=max_items)
        elif platform == "threads":
            signals = adapter.search_threads(query, max_items=max_items)
        else:
            signals = adapter.fetch_signals(query, max_items=max_items)

        if not signals:
            console.print("[yellow]No results found.[/yellow]")
            return

        # Convert to output format
        results = [
            {
                "title": s.title[:80],
                "url": s.url,
                "score": s.score,
                "comments": s.comment_count,
                "relevance": round(s.relevance_score, 3),
                "author": s.author,
                "timestamp": s.timestamp.isoformat() if s.timestamp else None,
            }
            for s in signals
        ]

        if output:
            with open(output, "w") as f:
                json.dump(results, f, indent=2)
            console.print(f"[green]✓ Saved {len(results)} results to {output}[/green]")
        else:
            console.print(f"\n[bold]Found {len(signals)} results:[/bold]\n")
            for s in signals[:10]:
                score_str = f"[{s.relevance_score:.2f}]"
                title_str = s.title[:60] + "..." if len(s.title) > 60 else s.title
                console.print(f"  {score_str} {title_str}")
                if s.url:
                    console.print(f"       [dim]{s.url[:70]}[/dim]")

            if len(signals) > 10:
                console.print(f"\n  [dim]... and {len(signals) - 10} more[/dim]")

    except ValueError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

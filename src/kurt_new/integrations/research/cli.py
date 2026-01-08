"""CLI commands for research integration setup."""

from __future__ import annotations

import click
from rich.console import Console

from kurt_new.admin.telemetry.decorators import track_command

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
    type=click.Choice(["perplexity"]),
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
    from kurt_new.config import get_config_file_path

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
    known_sources = ["perplexity"]

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

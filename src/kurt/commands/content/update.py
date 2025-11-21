"""
Content update command - orchestrate map refresh and optional auto-fetch.
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command

console = Console()


@click.command("update")
@click.option(
    "--cms/--no-cms",
    default=True,
    help="Refresh CMS sources (default: True)",
)
@click.option(
    "--websites/--no-websites",
    default=True,
    help="Refresh website sources (default: True)",
)
@click.option(
    "--auto-fetch",
    is_flag=True,
    default=None,
    help="Enable auto-fetch (overrides config)",
)
@click.option(
    "--no-auto-fetch",
    "disable_auto_fetch",
    is_flag=True,
    default=False,
    help="Disable auto-fetch (overrides config)",
)
@click.option(
    "--max-concurrent",
    type=int,
    default=5,
    help="Max concurrent fetch operations (default: 5)",
)
@click.option(
    "--background",
    is_flag=True,
    help="Run update in background workflow",
)
@click.option(
    "--init-config",
    is_flag=True,
    help="Initialize/reconfigure update settings",
)
@track_command
def update_cmd(
    cms: bool,
    websites: bool,
    auto_fetch: bool,
    disable_auto_fetch: bool,
    max_concurrent: int,
    background: bool,
    init_config: bool,
):
    """
    Update content maps and optionally auto-fetch new documents.

    This command:
    1. Checks configured content sources (CMS, websites)
    2. Refreshes content maps to discover new documents
    3. Optionally auto-fetches new content based on configuration

    \b
    Examples:
        # Update all sources with default settings
        kurt content update

        # Update only CMS sources
        kurt content update --no-websites

        # Update and force auto-fetch
        kurt content update --auto-fetch

        # Update without auto-fetch
        kurt content update --no-auto-fetch

        # Run in background
        kurt content update --background

        # Configure update settings
        kurt content update --init-config
    """
    from kurt.content.map.config import init_update_config, load_update_config
    from kurt.workflows import ensure_worker_running

    # Handle config initialization
    if init_config:
        console.print()
        init_update_config(interactive=True)
        return

    # Determine auto-fetch setting
    auto_fetch_enabled = None
    if auto_fetch:
        auto_fetch_enabled = True
    elif disable_auto_fetch:
        auto_fetch_enabled = False
    # else: None = use config

    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]Content Map Update[/bold cyan]\n"
            "[dim]Refreshing content sources and discovering new documents[/dim]",
            border_style="cyan",
        )
    )
    console.print()

    # Load config to show settings
    config = load_update_config()
    auto_fetch_config = config.get("auto_fetch", {})

    # Show settings
    console.print("[bold]Update Settings:[/bold]")
    console.print(f"  CMS sources: [cyan]{'enabled' if cms else 'disabled'}[/cyan]")
    console.print(f"  Website sources: [cyan]{'enabled' if websites else 'disabled'}[/cyan]")

    if auto_fetch_enabled is not None:
        console.print(
            f"  Auto-fetch: [cyan]{'enabled' if auto_fetch_enabled else 'disabled'}[/cyan] (override)"
        )
    else:
        console.print(
            f"  Auto-fetch: [cyan]{'enabled' if auto_fetch_config.get('enabled') else 'disabled'}[/cyan] (from config)"
        )

    console.print(f"  Max concurrent: [cyan]{max_concurrent}[/cyan]")
    console.print()

    # Background mode
    if background:
        from kurt.content.map.workflow_update import enqueue_content_update

        console.print("[yellow]Starting background workflow...[/yellow]")

        # Ensure worker is running
        try:
            ensure_worker_running()
        except Exception as e:
            console.print(f"[red]✗ Could not start worker: {e}[/red]")
            console.print(
                "[yellow]Tip:[/yellow] Start worker with: [cyan]kurt workflows worker[/cyan]"
            )
            raise click.Abort()

        # Enqueue workflow
        workflow_id = enqueue_content_update(
            refresh_cms=cms,
            refresh_websites=websites,
            auto_fetch=auto_fetch_enabled,
            priority=10,
        )

        console.print("[green]✓ Workflow enqueued[/green]")
        console.print(f"  Workflow ID: [cyan]{workflow_id}[/cyan]\n")
        console.print("[bold]Monitor progress:[/bold]")
        console.print(f"  [cyan]kurt workflows status {workflow_id}[/cyan]")
        console.print(f"  [cyan]kurt workflows logs {workflow_id}[/cyan]")
        console.print()
        return

    # Foreground mode - run workflow directly
    console.print("[yellow]Starting update workflow...[/yellow]\n")

    try:
        # Ensure worker is running for foreground workflow too
        try:
            ensure_worker_running()
        except Exception as e:
            console.print(f"[red]✗ Could not start worker: {e}[/red]")
            console.print(
                "[yellow]Tip:[/yellow] Start worker with: [cyan]kurt workflows worker[/cyan]"
            )
            raise click.Abort()

        # Import and run workflow
        import asyncio

        from kurt.content.map.workflow_update import content_map_update_workflow
        from kurt.workflows import get_dbos

        # Initialize DBOS
        get_dbos()

        # Run workflow
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running content map update...", total=None)

            result = asyncio.run(
                content_map_update_workflow(
                    refresh_cms=cms,
                    refresh_websites=websites,
                    auto_fetch=auto_fetch_enabled,
                    max_concurrent_fetch=max_concurrent,
                )
            )

            progress.update(task, completed=True)

        console.print()
        console.print("[bold green]✓ Update Complete[/bold green]\n")

        # Display results
        _display_update_results(result)

    except Exception as e:
        console.print(f"\n[red]✗ Update failed: {e}[/red]")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise click.Abort()


def _display_update_results(result: dict):
    """Display formatted update results."""

    # Summary table
    summary_table = Table(title="Update Summary", show_header=False)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="bold")

    summary_table.add_row("Sources checked", str(result["sources_checked"]))
    summary_table.add_row("Total discovered", str(result["total_discovered"]))
    summary_table.add_row("New documents", str(result["total_new"]))

    if result["auto_fetch_enabled"]:
        summary_table.add_row(
            "Documents fetched", f"{result['documents_fetched']} [green]✓[/green]"
        )

    console.print(summary_table)
    console.print()

    # CMS results
    if result["cms_results"]:
        console.print("[bold]CMS Sources:[/bold]")
        cms_table = Table(show_header=True)
        cms_table.add_column("Platform", style="cyan")
        cms_table.add_column("Instance")
        cms_table.add_column("Total", justify="right")
        cms_table.add_column("New", justify="right", style="green")
        cms_table.add_column("Existing", justify="right", style="dim")

        for cms_result in result["cms_results"]:
            if "error" in cms_result:
                cms_table.add_row(
                    cms_result["platform"],
                    cms_result["instance"],
                    "[red]ERROR[/red]",
                    "-",
                    "-",
                )
            else:
                cms_table.add_row(
                    cms_result["platform"],
                    cms_result["instance"],
                    str(cms_result["total"]),
                    str(cms_result["new"]),
                    str(cms_result["existing"]),
                )

        console.print(cms_table)
        console.print()

    # Website results
    if result["website_results"]:
        console.print("[bold]Website Sources:[/bold]")
        web_table = Table(show_header=True)
        web_table.add_column("URL", style="cyan")
        web_table.add_column("Total", justify="right")
        web_table.add_column("New", justify="right", style="green")
        web_table.add_column("Existing", justify="right", style="dim")

        for web_result in result["website_results"]:
            if "error" in web_result:
                web_table.add_row(
                    web_result["url"],
                    "[red]ERROR[/red]",
                    "-",
                    "-",
                )
            else:
                web_table.add_row(
                    web_result["url"],
                    str(web_result["total"]),
                    str(web_result["new"]),
                    str(web_result["existing"]),
                )

        console.print(web_table)
        console.print()

    # Next steps
    if result["total_new"] > 0:
        console.print("[bold]Next Steps:[/bold]")

        if not result["auto_fetch_enabled"]:
            console.print(
                "  • Fetch new documents: [cyan]kurt content fetch --status NOT_FETCHED[/cyan]"
            )

        console.print("  • View documents: [cyan]kurt content list[/cyan]")
        console.print("  • Enable auto-fetch: [cyan]kurt content update --init-config[/cyan]")
        console.print()
    elif result["sources_checked"] == 0:
        console.print("[yellow]No sources configured.[/yellow]")
        console.print()
        console.print("[bold]Get started:[/bold]")
        console.print("  • Add CMS source: [cyan]kurt integrations cms onboard[/cyan]")
        console.print("  • Add website: [cyan]kurt content map <url>[/cyan]")
        console.print()


__all__ = ["update_cmd"]

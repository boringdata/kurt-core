"""Kurt status command - comprehensive project status."""

import json
from pathlib import Path

import click
from rich.console import Console

from kurt.config import config_exists, load_config
from kurt.services.status_service import (
    check_pending_migrations,
    generate_status_markdown,
    get_cluster_count,
    get_document_counts,
    get_documents_by_domain,
    get_project_summaries,
    is_kurt_plugin_installed,
)
from kurt.telemetry.decorators import track_command

console = Console()


# ============================================================================
# Status Command
# ============================================================================


@click.command()
@click.option(
    "--format",
    type=click.Choice(["pretty", "json"], case_sensitive=False),
    default="pretty",
    help="Output format",
)
@click.option(
    "--hook-cc",
    is_flag=True,
    help="Output in Claude Code hook format (systemMessage + additionalContext)",
)
@track_command
def status(format: str, hook_cc: bool):
    """
    Show comprehensive Kurt project status.

    Displays:
    - Initialization status
    - Document counts and sources
    - Topic clusters
    - Project summaries
    - Recommended next steps

    Examples:
        kurt status
        kurt status --format json
        kurt status --hook-cc  # For Claude Code hooks
    """
    # Check if Kurt is initialized
    if not config_exists():
        message = (
            "⚠ **Kurt project not initialized**\n\n"
            "You need to initialize Kurt before using it.\n\n"
            "Run: `kurt init`"
        )

        if hook_cc:
            output = {
                "systemMessage": message,
                "additionalContext": message,
            }
            print(json.dumps(output, indent=2))
        elif format == "json":
            output = {
                "initialized": False,
                "message": message,
            }
            print(json.dumps(output, indent=2))
        else:
            console.print(f"[yellow]{message}[/yellow]")
        return

    try:
        config = load_config()
        db_path = Path(config.PATH_DB)

        # Check if database exists
        if not db_path.exists():
            message = (
                "⚠ **Kurt project not fully initialized**\n\n"
                "Config exists but database missing.\n\n"
                "Run: `kurt init`"
            )

            if hook_cc:
                output = {
                    "systemMessage": message,
                    "additionalContext": message,
                }
                print(json.dumps(output, indent=2))
            elif format == "json":
                output = {
                    "initialized": False,
                    "config_exists": True,
                    "database_exists": False,
                    "message": message,
                }
                print(json.dumps(output, indent=2))
            else:
                console.print(f"[yellow]{message}[/yellow]")
            return

        # Handle --hook-cc flag: generate markdown and wrap in hook format
        if hook_cc:
            markdown_output = generate_status_markdown()
            hook_output = {
                "systemMessage": markdown_output,
                "additionalContext": markdown_output,
            }
            print(json.dumps(hook_output, indent=2))
            return

        # Gather all status information
        doc_counts = get_document_counts()
        domains = get_documents_by_domain()
        cluster_count = get_cluster_count()
        projects = get_project_summaries()

        if format == "json":
            migration_status = check_pending_migrations()
            output = {
                "initialized": True,
                "config_exists": True,
                "database_exists": True,
                "database_path": str(db_path),
                "migrations": {
                    "has_pending": migration_status["has_pending"],
                    "count": migration_status["count"],
                    "pending": migration_status["migrations"],
                },
                "claude_code_integration": {
                    "plugin_installed": is_kurt_plugin_installed(),
                },
                "documents": {
                    "total": doc_counts["total"],
                    "by_status": {
                        "not_fetched": doc_counts["not_fetched"],
                        "fetched": doc_counts["fetched"],
                        "error": doc_counts["error"],
                    },
                    "by_domain": domains,
                },
                "clusters": {
                    "total": cluster_count,
                },
                "projects": {
                    "total": len(projects),
                    "list": projects,
                },
            }
            print(json.dumps(output, indent=2))
        else:
            # Pretty format
            console.print("\n[bold cyan]Kurt Project Status[/bold cyan]")
            console.print(f"[dim]{'─' * 60}[/dim]\n")

            # Initialization status
            console.print("[green]✓ Kurt project initialized[/green]")
            console.print("- Config: [cyan]kurt.config[/cyan] found")
            console.print(f"- Database: [cyan]{db_path}[/cyan] exists")

            # Check for pending migrations
            migration_status = check_pending_migrations()
            if migration_status["has_pending"]:
                console.print(
                    f"\n[yellow]⚠ {migration_status['count']} pending database migration(s)[/yellow]"
                )
                console.print("- Run: [cyan]kurt migrate apply[/cyan] to update the database")
                for migration_name in migration_status["migrations"]:
                    console.print(f"  - [dim]{migration_name}[/dim]")
            console.print()

            # Claude Code integration status
            console.print("[bold]Claude Code Integration[/bold]")
            plugin_installed = is_kurt_plugin_installed()
            if plugin_installed:
                console.print("[green]✓ Kurt plugin installed[/green]")
                console.print("- Claude Code can interact with Kurt")
                console.print(
                    "- [bold cyan]Agent: Check if you can see /create-project command[/bold cyan]\n"
                )
            else:
                console.print("[yellow]⚠ Kurt plugin not detected[/yellow]")
                console.print("- Install from Claude Code plugin marketplace")
                console.print("- Use [cyan]/plugin[/cyan] command in Claude Code\n")

            # Documents section
            console.print("[bold]Documents[/bold]")
            if doc_counts["total"] > 0:
                console.print(f"Total documents ingested: [bold]{doc_counts['total']}[/bold]\n")

                if domains:
                    console.print("Documents by source:")
                    for domain_info in domains[:10]:  # Show top 10
                        console.print(
                            f"- [cyan]{domain_info['domain']}[/cyan]: {domain_info['count']} documents"
                        )
                    if len(domains) > 10:
                        console.print(f"[dim]... and {len(domains) - 10} more sources[/dim]")
                    console.print()
            else:
                console.print("[yellow]⚠ No documents ingested yet[/yellow]")
                console.print("- Run: [cyan]kurt content add <url>[/cyan] to add content\n")

            # Clusters section
            console.print("[bold]Topic Clusters[/bold]")
            if cluster_count > 0:
                console.print(f"[bold]{cluster_count}[/bold] topic clusters computed")
                console.print(
                    "- View with: [cyan]kurt content cluster --url-starts-with <url>[/cyan]\n"
                )
            else:
                if doc_counts["total"] > 0:
                    console.print("[yellow]⚠ No clusters computed yet[/yellow]")
                    console.print(
                        "- Run: [cyan]kurt content cluster --url-starts-with <url>[/cyan] to analyze content\n"
                    )
                else:
                    console.print("[dim]No clusters (no documents to analyze)[/dim]\n")

            # Projects section
            console.print("[bold]Projects[/bold]")
            if projects:
                console.print(f"Found [bold]{len(projects)}[/bold] project(s):\n")

                for proj in projects:
                    console.print(f"### [cyan]{proj['name']}[/cyan]")
                    if proj.get("title"):
                        console.print(f"[bold]{proj['title']}[/bold]")
                    if proj.get("goal"):
                        console.print(f"- Goal: {proj['goal']}")
                    if proj.get("intent"):
                        console.print(f"- Intent: {proj['intent']}")
                    console.print()
            else:
                console.print("[yellow]⚠ No projects created yet[/yellow]")
                console.print(
                    "- Create a project manually in the [cyan]projects/[/cyan] directory\n"
                )

            # Recommendations
            console.print(f"[dim]{'─' * 60}[/dim]")
            console.print("\n[bold]Recommended Next Steps[/bold]\n")

            if projects:
                console.print("[bold]You have existing projects.[/bold] Consider:")
                console.print("- View project status: [cyan]kurt project status[/cyan]")
                console.print("- Add more content: [cyan]kurt content add <url>[/cyan]")
            elif doc_counts["total"] > 0 and cluster_count > 0:
                console.print("[bold]Content ingested and analyzed.[/bold] Consider:")
                console.print("- Create a project in the [cyan]projects/[/cyan] directory")
                console.print("- View documents: [cyan]kurt content list[/cyan]")
            elif doc_counts["total"] > 0:
                console.print("[bold]Content ingested but not analyzed.[/bold] Next:")
                console.print(
                    "- Run: [cyan]kurt content cluster --url-starts-with <url>[/cyan] to discover topics"
                )
            else:
                console.print("[bold]Ready to start![/bold] Choose an approach:")
                console.print("- Add content: [cyan]kurt content add <url>[/cyan]")
                console.print("- Initialize: [cyan]kurt init[/cyan] (if needed)")

            console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise click.Abort()

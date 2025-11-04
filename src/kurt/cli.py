"""Kurt CLI - Main command-line interface."""

from pathlib import Path

import click
from rich.console import Console

from kurt import __version__
from kurt.commands.analytics import analytics
from kurt.commands.cluster_urls import cluster_urls_cmd
from kurt.commands.cms import cms
from kurt.commands.content import content
from kurt.commands.feedback import feedback
from kurt.commands.fetch import fetch_cmd
from kurt.commands.map import map_cmd
from kurt.commands.migrate import migrate
from kurt.commands.project import project
from kurt.commands.research import research
from kurt.commands.status import status
from kurt.commands.telemetry import telemetry
from kurt.config import config_exists, create_config, get_config_file_path
from kurt.db.database import init_database
from kurt.telemetry.decorators import track_command

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="kurt")
@click.pass_context
def main(ctx):
    """
    Kurt - Document intelligence CLI tool.

    Transform documents into structured knowledge graphs.
    """
    # Skip migration check for init and migrate commands
    if ctx.invoked_subcommand in ["init", "migrate"]:
        return

    # Check if project is initialized
    if not config_exists():
        return  # Let commands handle "not initialized" error

    # Check for pending migrations
    try:
        from kurt.db.migrations.utils import (
            apply_migrations,
            check_migrations_needed,
            get_pending_migrations,
        )

        if check_migrations_needed():
            pending = get_pending_migrations()
            console.print()
            console.print("[yellow]⚠ Database migrations are pending[/yellow]")
            console.print(f"[dim]{len(pending)} migration(s) need to be applied[/dim]")
            console.print()
            console.print("[dim]Run [cyan]kurt migrate apply[/cyan] to update your database[/dim]")
            console.print("[dim]Or run [cyan]kurt migrate status[/cyan] to see details[/dim]")
            console.print()

            # Ask if user wants to apply now
            from rich.prompt import Confirm

            if Confirm.ask("[bold]Apply migrations now?[/bold]", default=False):
                success = apply_migrations(auto_confirm=True)
                if not success:
                    raise click.Abort()
            else:
                console.print(
                    "[yellow]⚠ Proceeding without migration. Some features may not work.[/yellow]"
                )
                console.print()
    except ImportError:
        # Migration system not available (shouldn't happen but handle gracefully)
        pass
    except Exception:
        # Don't block CLI if migration check fails
        pass


@main.command()
@click.option(
    "--db-path",
    default=".kurt/kurt.sqlite",
    help="Path to database file relative to current directory (default: .kurt/kurt.sqlite)",
)
@click.option(
    "--sources-path",
    default="sources",
    help="Path to store fetched content relative to current directory (default: sources)",
)
@click.option(
    "--projects-path",
    default="projects",
    help="Path to store project-specific content relative to current directory (default: projects)",
)
@click.option(
    "--rules-path",
    default="rules",
    help="Path to store rules and configurations relative to current directory (default: rules)",
)
@track_command
def init(db_path: str, sources_path: str, projects_path: str, rules_path: str):
    """
    Initialize a new Kurt project in the current directory.

    Creates:
    - kurt.config file with project settings
    - .kurt/ directory
    - SQLite database with all tables

    Example:
        kurt init
        kurt init --db-path custom/path/db.sqlite
        kurt init --sources-path my_sources --projects-path my_projects
    """
    console.print("[bold green]Initializing Kurt project...[/bold green]\n")

    try:
        # Check if already initialized
        if config_exists():
            config_file = get_config_file_path()
            console.print(f"[yellow]Kurt project already initialized ({config_file})[/yellow]")
            overwrite = console.input("Reinitialize? (y/N): ")
            if overwrite.lower() != "y":
                console.print("[dim]Keeping existing configuration[/dim]")
                return

        # Step 1: Create kurt.config configuration file
        console.print("[dim]Creating configuration file...[/dim]")
        config = create_config(
            db_path=db_path,
            sources_path=sources_path,
            projects_path=projects_path,
            rules_path=rules_path,
        )
        config_file = get_config_file_path()
        console.print(f"[green]✓[/green] Created config: {config_file}")
        console.print(f"[dim]  PATH_DB={config.PATH_DB}[/dim]")
        console.print(f"[dim]  PATH_SOURCES={config.PATH_SOURCES}[/dim]")
        console.print(f"[dim]  PATH_PROJECTS={config.PATH_PROJECTS}[/dim]")
        console.print(f"[dim]  PATH_RULES={config.PATH_RULES}[/dim]")

        # Step 2: Create .env.example file
        console.print()
        console.print("[dim]Creating .env.example file...[/dim]")
        env_example_path = Path.cwd() / ".env.example"
        env_example_content = """# Kurt Environment Variables
# Copy this file to .env and fill in your API keys

# Firecrawl API Key (optional - for web scraping)
# Get your API key from: https://firecrawl.dev
# If not set, Kurt will use Trafilatura for web scraping
FIRECRAWL_API_KEY=your_firecrawl_api_key_here

# OpenAI API Key (required for LLM-based features)
OPENAI_API_KEY=your_openai_api_key_here
"""
        with open(env_example_path, "w") as f:
            f.write(env_example_content)
        console.print("[green]✓[/green] Created .env.example")

        # Step 3: Initialize database
        console.print()
        init_database()

        # Step 4: Install Kurt Claude Code plugin
        console.print()
        console.print("[dim]Installing Kurt plugin for Claude Code...[/dim]")

        try:
            import subprocess

            # Get the path to the kurt-core directory
            kurt_core_path = Path(__file__).parent.parent.parent.resolve()

            # Add marketplace
            result = subprocess.run(
                ["claude", "plugin", "marketplace", "add", str(kurt_core_path)],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                console.print("[green]✓[/green] Added kurt-marketplace")

                # Install plugin
                result = subprocess.run(
                    ["claude", "plugin", "install", "kurt"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0:
                    console.print("[green]✓[/green] Installed kurt plugin")
                else:
                    console.print("[yellow]⚠[/yellow] Could not install kurt plugin")
                    console.print(f"[dim]{result.stderr}[/dim]")
            else:
                console.print(
                    "[yellow]⚠[/yellow] Could not add marketplace (Claude Code may not be installed)"
                )
                console.print("[dim]You can manually add it later with:[/dim]")
                console.print(f"[dim]  claude plugin marketplace add {kurt_core_path}[/dim]")
                console.print("[dim]  claude plugin install kurt[/dim]")

        except FileNotFoundError:
            console.print("[yellow]⚠[/yellow] Claude Code CLI not found")
            console.print("[dim]Install Claude Code from: https://claude.ai/download[/dim]")
            console.print(f"[dim]Then run: claude plugin marketplace add {kurt_core_path}[/dim]")
            console.print("[dim]         claude plugin install kurt[/dim]")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Could not configure plugin: {e}")

        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. Copy .env.example to .env and add your API keys")
        console.print(
            "  2. Verify plugin installation: [cyan]claude plugin marketplace list[/cyan]"
        )
        console.print("  3. Open Claude Code and run [cyan]/create-project[/cyan]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


# Register command groups
main.add_command(analytics)
main.add_command(cms)
main.add_command(cluster_urls_cmd)
main.add_command(content)
main.add_command(feedback)
main.add_command(fetch_cmd, name="fetch")
main.add_command(map_cmd, name="map")
main.add_command(migrate)
main.add_command(project)
main.add_command(research)
main.add_command(status)
main.add_command(telemetry)


if __name__ == "__main__":
    main()

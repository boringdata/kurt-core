"""Kurt CLI - Main command-line interface."""

import json
import shutil
from pathlib import Path

import click
from rich.console import Console

from kurt import __version__
from kurt.admin.telemetry.decorators import track_command
from kurt.commands.admin import admin
from kurt.commands.content import content
from kurt.commands.integrations import integrations
from kurt.commands.status import status
from kurt.commands.workflows import workflows_group
from kurt.config.base import KurtConfig, config_file_exists, create_config, get_config_file_path
from kurt.db.database import init_database

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
    if not config_file_exists():
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
            console.print(
                "[dim]Run [cyan]kurt admin migrate apply[/cyan] to update your database[/dim]"
            )
            console.print("[dim]Or run [cyan]kurt admin migrate status[/cyan] to see details[/dim]")
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
    default=KurtConfig.DEFAULT_DB_PATH,
    help=f"Path to database file relative to current directory (default: {KurtConfig.DEFAULT_DB_PATH})",
)
@click.option(
    "--sources-path",
    default=KurtConfig.DEFAULT_SOURCES_PATH,
    help=f"Path to store fetched content relative to current directory (default: {KurtConfig.DEFAULT_SOURCES_PATH})",
)
@click.option(
    "--projects-path",
    default=KurtConfig.DEFAULT_PROJECTS_PATH,
    help=f"Path to store project-specific content relative to current directory (default: {KurtConfig.DEFAULT_PROJECTS_PATH})",
)
@click.option(
    "--rules-path",
    default=KurtConfig.DEFAULT_RULES_PATH,
    help=f"Path to store rules and configurations relative to current directory (default: {KurtConfig.DEFAULT_RULES_PATH})",
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
        if config_file_exists():
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

        # Step 3.5: Copy Claude Code instruction files
        console.print()
        console.print("[dim]Setting up Claude Code instruction files...[/dim]")
        try:
            # Get the source plugin directory from the package
            plugin_source = Path(__file__).parent / "claude_plugin"

            if plugin_source.exists():
                # Create .claude directory in current working directory
                claude_dir = Path.cwd() / ".claude"
                claude_dir.mkdir(exist_ok=True)

                # Check if CLAUDE.md exists and warn user
                claude_md_dest = claude_dir / "CLAUDE.md"
                if claude_md_dest.exists():
                    console.print(
                        "[yellow]⚠[/yellow] CLAUDE.md already exists and will be overwritten with latest Kurt instructions"
                    )
                    overwrite_claude = console.input("Overwrite CLAUDE.md? (y/N): ")
                    if overwrite_claude.lower() != "y":
                        console.print("[dim]Skipping CLAUDE.md update[/dim]")
                        skip_claude_md = True
                    else:
                        skip_claude_md = False
                else:
                    skip_claude_md = False

                # Copy files individually to preserve user customizations
                for item in plugin_source.iterdir():
                    if item.name == "CLAUDE.md":
                        # Copy CLAUDE.md to .claude/ (unless skipped)
                        if not skip_claude_md:
                            shutil.copy2(item, claude_dir / item.name)
                    elif item.name == "settings.json":
                        # Merge settings.json with existing settings
                        dest_settings = claude_dir / "settings.json"
                        with open(item) as f:
                            kurt_settings = json.load(f)

                        if dest_settings.exists():
                            # Load existing settings and merge
                            with open(dest_settings) as f:
                                existing_settings = json.load(f)
                            # Merge hooks (Kurt's hooks take precedence)
                            if "hooks" not in existing_settings:
                                existing_settings["hooks"] = {}
                            existing_settings["hooks"].update(kurt_settings.get("hooks", {}))
                            with open(dest_settings, "w") as f:
                                json.dump(existing_settings, f, indent=2)
                        else:
                            # Create new settings.json
                            with open(dest_settings, "w") as f:
                                json.dump(kurt_settings, f, indent=2)
                    elif item.name in ["instructions", "commands"]:
                        # Copy directory contents individually, preserving user files
                        dest_dir = claude_dir / item.name
                        dest_dir.mkdir(exist_ok=True)
                        for src_file in item.rglob("*"):
                            if src_file.is_file():
                                rel_path = src_file.relative_to(item)
                                dest_file = dest_dir / rel_path
                                dest_file.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(src_file, dest_file)
                    elif item.name == "kurt":
                        # Copy kurt/ contents individually, preserving user files
                        dest_dir = Path.cwd() / item.name
                        dest_dir.mkdir(exist_ok=True)
                        for src_file in item.rglob("*"):
                            if src_file.is_file():
                                rel_path = src_file.relative_to(item)
                                dest_file = dest_dir / rel_path
                                dest_file.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(src_file, dest_file)

                console.print("[green]✓[/green] Copied instruction files")
                console.print(
                    "[dim]  .claude/CLAUDE.md, .claude/settings.json, .claude/instructions/, .claude/commands/[/dim]"
                )
                console.print("[dim]  kurt/templates/[/dim]")
            else:
                console.print("[yellow]⚠[/yellow] Plugin files not found in package")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Could not copy instruction files: {e}")

        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. Copy .env.example to .env and add your API keys")
        console.print("  2. Open Claude Code in this directory")
        console.print("  3. Describe your content goals to Claude Code to create a project")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


# Register command groups
main.add_command(content)
main.add_command(integrations)
main.add_command(admin)
main.add_command(status)
main.add_command(workflows_group, name="workflows")


if __name__ == "__main__":
    main()

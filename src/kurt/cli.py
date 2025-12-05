"""Kurt CLI - Main command-line interface."""

import json
import shutil
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console

from kurt import __version__

# Load environment variables from .env file in current directory
# This must happen before any other imports that might use env vars
load_dotenv()
from kurt.admin.telemetry.decorators import track_command  # noqa: E402
from kurt.commands.admin import admin  # noqa: E402
from kurt.commands.content import content  # noqa: E402
from kurt.commands.integrations import integrations  # noqa: E402
from kurt.commands.show import show  # noqa: E402
from kurt.commands.status import status  # noqa: E402
from kurt.commands.update import update  # noqa: E402
from kurt.commands.workflows import workflows_group  # noqa: E402
from kurt.config.base import (  # noqa: E402
    KurtConfig,
    config_file_exists,
    create_config,
    get_config_file_path,
)
from kurt.db.database import init_database  # noqa: E402

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

    # Skip migration check if running in hook mode (--hook-cc flag)
    # Hooks should handle migrations silently within the command
    if "--hook-cc" in sys.argv:
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

            # Check if we're in an interactive terminal
            # If not (e.g., Cursor AI running commands), just warn without prompting
            is_interactive = sys.stdin.isatty() and sys.stdout.isatty()

            console.print()
            console.print("[yellow]⚠ Database migrations are pending[/yellow]")
            console.print(f"[dim]{len(pending)} migration(s) need to be applied[/dim]")
            console.print()
            console.print(
                "[dim]Run [cyan]kurt admin migrate apply[/cyan] to update your database[/dim]"
            )
            console.print("[dim]Or run [cyan]kurt admin migrate status[/cyan] to see details[/dim]")
            console.print()

            # Only prompt if in interactive terminal (not when Cursor AI is running commands)
            if is_interactive:
                from rich.prompt import Confirm

                if Confirm.ask("[bold]Apply migrations now?[/bold]", default=False):
                    result = apply_migrations(auto_confirm=True)
                    if not result["success"]:
                        raise click.Abort()
                else:
                    console.print(
                        "[yellow]⚠ Proceeding without migration. Some features may not work.[/yellow]"
                    )
                    console.print()
            else:
                # Non-interactive mode (Cursor, scripts, etc.) - auto-apply migrations
                result = apply_migrations(auto_confirm=True, silent=True)
                if result["success"] and result["applied"]:
                    console.print(f"[green]✓ Applied {result['count']} migration(s)[/green]")
                    console.print()
                elif not result["success"]:
                    # Migration failed - warn but don't block CLI
                    console.print(
                        f"[red]⚠ Migration failed: {result.get('error', 'Unknown error')}[/red]"
                    )
                    console.print("[dim]Database backup created. Some features may not work.[/dim]")
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
@click.option(
    "--ide",
    type=click.Choice(["claude", "cursor", "both"], case_sensitive=False),
    default="both",
    help="IDE to configure for (claude, cursor, or both; default: both)",
)
@track_command
def init(db_path: str, sources_path: str, projects_path: str, rules_path: str, ide: str):
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

        # Step 3.5: Set up unified agent instructions
        console.print()

        # Determine which IDEs to set up
        ides_to_setup = []
        if ide == "both":
            ides_to_setup = ["claude", "cursor"]
            console.print("[dim]Setting up unified agent instructions...[/dim]")
        else:
            ides_to_setup = [ide]
            ide_name = "Claude Code" if ide == "claude" else "Cursor"
            console.print(f"[dim]Setting up {ide_name} agent instructions...[/dim]")

        try:
            # Get the source AGENTS.md from the package
            agents_source = Path(__file__).parent / "agents" / "AGENTS.md"

            if agents_source.exists():
                # Create .agents directory and copy AGENTS.md
                agents_dir = Path.cwd() / ".agents"
                agents_dir.mkdir(exist_ok=True)
                agents_dest = agents_dir / "AGENTS.md"

                # Check if AGENTS.md exists and warn user
                if agents_dest.exists():
                    console.print(
                        "[yellow]⚠[/yellow] AGENTS.md already exists and will be overwritten"
                    )
                    overwrite_main = console.input("Overwrite AGENTS.md? (y/N): ")
                    if overwrite_main.lower() != "y":
                        console.print("[dim]Keeping existing AGENTS.md[/dim]")
                        agents_copied = False
                    else:
                        shutil.copy2(agents_source, agents_dest)
                        agents_copied = True
                else:
                    shutil.copy2(agents_source, agents_dest)
                    agents_copied = True

                if agents_copied:
                    console.print("[green]✓[/green] Copied unified agent instructions")
                    console.print("[dim]  .agents/AGENTS.md[/dim]")

                # Create IDE-specific symlinks
                for current_ide in ides_to_setup:
                    ide_dir_name = ".claude" if current_ide == "claude" else ".cursor"
                    ide_dir = Path.cwd() / ide_dir_name
                    ide_dir.mkdir(exist_ok=True)

                    if current_ide == "claude":
                        # Create main CLAUDE.md symlink (primary entry point)
                        claude_md_dest = ide_dir / "CLAUDE.md"
                        claude_md_target = Path("../.agents/AGENTS.md")

                        # Check if CLAUDE.md already exists
                        if claude_md_dest.exists() or claude_md_dest.is_symlink():
                            if claude_md_dest.is_symlink():
                                # Already a symlink, update target
                                claude_md_dest.unlink()
                                claude_md_dest.symlink_to(claude_md_target)
                                console.print("[green]✓[/green] Updated Claude Code symlink")
                            else:
                                # Regular file with user content
                                console.print(
                                    "[yellow]⚠[/yellow] CLAUDE.md already exists with custom content"
                                )
                                console.print("How would you like to proceed?")
                                console.print(
                                    "  1. Keep CLAUDE.md and add Kurt instructions in .claude/instructions/"
                                )
                                console.print(
                                    "  2. Replace with symlink (your content will be backed up)"
                                )
                                console.print("  3. Skip Claude Code setup")
                                choice = (
                                    console.input("Choice (1/2/3) [default: 1]: ").strip() or "1"
                                )

                                if choice == "1":
                                    # Keep existing CLAUDE.md, only create instructions symlink
                                    console.print("[dim]Keeping your existing CLAUDE.md[/dim]")
                                elif choice == "2":
                                    # Backup and replace
                                    backup_path = claude_md_dest.parent / "CLAUDE.md.backup"
                                    shutil.copy2(claude_md_dest, backup_path)
                                    claude_md_dest.unlink()
                                    claude_md_dest.symlink_to(claude_md_target)
                                    console.print(
                                        f"[green]✓[/green] Backed up to {backup_path.name}"
                                    )
                                    console.print("[green]✓[/green] Created Claude Code symlink")
                                else:
                                    console.print("[dim]Skipping Claude Code setup[/dim]")
                                    continue
                        else:
                            # Doesn't exist, create symlink
                            claude_md_dest.symlink_to(claude_md_target)
                            console.print("[green]✓[/green] Created Claude Code main file")

                        console.print("[dim]  .claude/CLAUDE.md → .agents/AGENTS.md[/dim]")

                        # Also create .claude/instructions/ directory with symlink for discoverability
                        instructions_dir = ide_dir / "instructions"
                        instructions_dir.mkdir(exist_ok=True)
                        instructions_symlink = instructions_dir / "AGENTS.md"
                        instructions_target = Path("../../.agents/AGENTS.md")

                        # Remove existing symlink or file
                        if instructions_symlink.exists() or instructions_symlink.is_symlink():
                            instructions_symlink.unlink()

                        # Create symlink
                        instructions_symlink.symlink_to(instructions_target)
                        console.print(
                            "[dim]  .claude/instructions/AGENTS.md → .agents/AGENTS.md[/dim]"
                        )

                        # Copy settings.json for Claude hooks
                        agents_dir_source = Path(__file__).parent / "agents"
                        settings_source = agents_dir_source / "claude-settings.json"
                        if settings_source.exists():
                            dest_settings = ide_dir / "settings.json"
                            with open(settings_source) as f:
                                kurt_settings = json.load(f)
                            if dest_settings.exists():
                                with open(dest_settings) as f:
                                    existing_settings = json.load(f)
                                if "hooks" not in existing_settings:
                                    existing_settings["hooks"] = {}
                                existing_settings["hooks"].update(kurt_settings.get("hooks", {}))
                                with open(dest_settings, "w") as f:
                                    json.dump(existing_settings, f, indent=2)
                            else:
                                with open(dest_settings, "w") as f:
                                    json.dump(kurt_settings, f, indent=2)
                            console.print("[green]✓[/green] Configured Claude Code hooks")

                    else:  # cursor
                        # Create .cursor/rules/ directory and symlink
                        rules_dir = ide_dir / "rules"
                        rules_dir.mkdir(exist_ok=True)
                        symlink_dest = rules_dir / "KURT.mdc"
                        symlink_target = Path("../../.agents/AGENTS.md")

                        # Check if KURT.mdc already exists
                        if symlink_dest.exists() or symlink_dest.is_symlink():
                            if symlink_dest.is_symlink():
                                # Already a symlink, update target
                                symlink_dest.unlink()
                                symlink_dest.symlink_to(symlink_target)
                                console.print("[green]✓[/green] Updated Cursor symlink")
                            else:
                                # Regular file (unusual, but handle it)
                                console.print("[yellow]⚠[/yellow] KURT.mdc already exists")
                                overwrite = console.input("Replace with symlink? (y/N): ")
                                if overwrite.lower() == "y":
                                    backup_path = symlink_dest.parent / "KURT.mdc.backup"
                                    shutil.copy2(symlink_dest, backup_path)
                                    symlink_dest.unlink()
                                    symlink_dest.symlink_to(symlink_target)
                                    console.print(
                                        f"[green]✓[/green] Backed up to {backup_path.name}"
                                    )
                                    console.print("[green]✓[/green] Created Cursor symlink")
                                else:
                                    console.print("[dim]Skipping Cursor setup[/dim]")
                                    continue
                        else:
                            # Doesn't exist, create symlink
                            symlink_dest.symlink_to(symlink_target)
                            console.print("[green]✓[/green] Created Cursor rule")

                        console.print("[dim]  .cursor/rules/KURT.mdc → .agents/AGENTS.md[/dim]")

            else:
                console.print("[yellow]⚠[/yellow] AGENTS.md not found in package")

        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Could not set up agent instructions: {e}")

        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. Copy .env.example to .env and add your API keys")
        if ide == "both":
            console.print("  2. Open in Claude Code or Cursor")
        elif ide == "claude":
            console.print("  2. Open Claude Code in this directory")
        else:  # cursor
            console.print("  2. Open Cursor in this directory")
        console.print("  3. Start working with the AI assistant!")
        console.print("     [dim](The assistant will guide you through any needed setup)[/dim]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


# Register command groups
main.add_command(content)
main.add_command(integrations)
main.add_command(admin)
main.add_command(status)
main.add_command(show)
main.add_command(update)
main.add_command(workflows_group, name="workflows")


if __name__ == "__main__":
    main()

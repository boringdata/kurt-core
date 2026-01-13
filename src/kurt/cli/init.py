"""Kurt init command - Initialize a new project."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command

console = Console()


@click.command()
@click.option(
    "--db-path",
    default=".kurt/kurt.sqlite",
    help="Path to database file relative to current directory",
)
@click.option(
    "--sources-path",
    default="sources",
    help="Path to store fetched content relative to current directory",
)
@click.option(
    "--projects-path",
    default="projects",
    help="Path to store project-specific content relative to current directory",
)
@click.option(
    "--rules-path",
    default="rules",
    help="Path to store rules and configurations relative to current directory",
)
@click.option(
    "--ide",
    type=click.Choice(["claude", "cursor", "both"], case_sensitive=False),
    default="both",
    help="IDE to configure for (claude, cursor, or both)",
)
@track_command
def init(db_path: str, sources_path: str, projects_path: str, rules_path: str, ide: str):
    """
    Initialize a new Kurt project in the current directory.

    Creates:
    - kurt.config file with project settings
    - .kurt/ directory
    - SQLite database with all tables
    """
    from kurt.config import config_file_exists, create_config, get_config_file_path
    from kurt.db import init_database

    console.print("[bold green]Initializing Kurt project...[/bold green]\n")

    try:
        if config_file_exists():
            config_file = get_config_file_path()
            console.print(f"[yellow]Kurt project already initialized ({config_file})[/yellow]")
            overwrite = console.input("Reinitialize? (y/N): ")
            if overwrite.lower() != "y":
                console.print("[dim]Keeping existing configuration[/dim]")
                return

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

        console.print()
        console.print("[dim]Creating .env.example file...[/dim]")
        _create_env_example()
        console.print("[green]✓[/green] Created .env.example")

        console.print()
        init_database()

        console.print()
        _setup_ide(ide)

        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. Copy .env.example to .env and add your API keys")
        if ide == "both":
            console.print("  2. Open in Claude Code or Cursor")
        elif ide == "claude":
            console.print("  2. Open Claude Code in this directory")
        else:
            console.print("  2. Open Cursor in this directory")
        console.print("  3. Start working with the AI assistant!")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


def _create_env_example():
    """Create .env.example file."""
    env_example_path = Path.cwd() / ".env.example"
    env_example_content = """# Kurt Environment Variables
# Copy this file to .env and fill in your API keys

# Firecrawl API Key (optional - for web scraping)
FIRECRAWL_API_KEY=your_firecrawl_api_key_here

# OpenAI API Key (required for LLM-based features)
OPENAI_API_KEY=your_openai_api_key_here
"""
    with open(env_example_path, "w") as f:
        f.write(env_example_content)


def _setup_ide(ide: str) -> None:
    """Setup IDE-specific files."""
    ides_to_setup = ["claude", "cursor"] if ide == "both" else [ide]

    if ide == "both":
        console.print("[dim]Setting up unified agent instructions...[/dim]")
    else:
        ide_name = "Claude Code" if ide == "claude" else "Cursor"
        console.print(f"[dim]Setting up {ide_name} agent instructions...[/dim]")

    try:
        agents_source = Path(__file__).parent.parent / "agents" / "AGENTS.md"

        if not agents_source.exists():
            console.print("[yellow]⚠[/yellow] AGENTS.md not found in package")
            return

        agents_dir = Path.cwd() / ".agents"
        agents_dir.mkdir(exist_ok=True)
        agents_dest = agents_dir / "AGENTS.md"

        if agents_dest.exists():
            console.print("[yellow]⚠[/yellow] AGENTS.md already exists")
            overwrite = console.input("Overwrite AGENTS.md? (y/N): ")
            if overwrite.lower() != "y":
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

        for current_ide in ides_to_setup:
            _setup_single_ide(current_ide, agents_source)

    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Could not set up agent instructions: {e}")


def _setup_single_ide(ide: str, agents_source: Path) -> None:
    """Setup a single IDE's configuration."""
    ide_dir_name = ".claude" if ide == "claude" else ".cursor"
    ide_dir = Path.cwd() / ide_dir_name
    ide_dir.mkdir(exist_ok=True)

    if ide == "claude":
        _setup_claude(ide_dir)
    else:
        _setup_cursor(ide_dir)


def _setup_claude(ide_dir: Path) -> None:
    """Setup Claude Code configuration."""
    claude_md_dest = ide_dir / "CLAUDE.md"
    claude_md_target = Path("../.agents/AGENTS.md")

    if claude_md_dest.exists() or claude_md_dest.is_symlink():
        if claude_md_dest.is_symlink():
            claude_md_dest.unlink()
            claude_md_dest.symlink_to(claude_md_target)
            console.print("[green]✓[/green] Updated Claude Code symlink")
        else:
            console.print("[yellow]⚠[/yellow] CLAUDE.md exists with custom content")
            console.print("  Keeping your existing CLAUDE.md")
    else:
        claude_md_dest.symlink_to(claude_md_target)
        console.print("[green]✓[/green] Created Claude Code main file")

    console.print("[dim]  .claude/CLAUDE.md → .agents/AGENTS.md[/dim]")

    instructions_dir = ide_dir / "instructions"
    instructions_dir.mkdir(exist_ok=True)
    instructions_symlink = instructions_dir / "AGENTS.md"
    instructions_target = Path("../../.agents/AGENTS.md")

    if instructions_symlink.exists() or instructions_symlink.is_symlink():
        instructions_symlink.unlink()
    instructions_symlink.symlink_to(instructions_target)
    console.print("[dim]  .claude/instructions/AGENTS.md → .agents/AGENTS.md[/dim]")

    settings_source = Path(__file__).parent.parent / "agents" / "claude-settings.json"
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


def _setup_cursor(ide_dir: Path) -> None:
    """Setup Cursor configuration."""
    rules_dir = ide_dir / "rules"
    rules_dir.mkdir(exist_ok=True)
    symlink_dest = rules_dir / "KURT.mdc"
    symlink_target = Path("../../.agents/AGENTS.md")

    if symlink_dest.exists() or symlink_dest.is_symlink():
        if symlink_dest.is_symlink():
            symlink_dest.unlink()
            symlink_dest.symlink_to(symlink_target)
            console.print("[green]✓[/green] Updated Cursor symlink")
        else:
            console.print("[yellow]⚠[/yellow] KURT.mdc already exists")
    else:
        symlink_dest.symlink_to(symlink_target)
        console.print("[green]✓[/green] Created Cursor rule")

    console.print("[dim]  .cursor/rules/KURT.mdc → .agents/AGENTS.md[/dim]")

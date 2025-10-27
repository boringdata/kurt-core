"""Kurt CLI - Main command-line interface."""

import click
from rich.console import Console

from kurt import __version__
from kurt.commands.cluster import cluster
from kurt.commands.cms import cms
from kurt.commands.document import document
from kurt.commands.index import index
from kurt.commands.ingest import ingest
from kurt.commands.research import research
from kurt.config import config_exists, create_config, get_config_file_path
from kurt.database import init_database

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="kurt")
def main():
    """
    Kurt - Document intelligence CLI tool.

    Transform documents into structured knowledge graphs.
    """
    pass


@main.command()
@click.option(
    "--project-path",
    default=".",
    help="Path to the Kurt project root (default: current directory)"
)
@click.option(
    "--db-path",
    default=".kurt/kurt.sqlite",
    help="Path to database file relative to project path (default: .kurt/kurt.sqlite)"
)
def init(project_path: str, db_path: str):
    """
    Initialize a new Kurt project.

    Creates:
    - .kurt configuration file with project settings
    - .kurt/ directory
    - SQLite database with all tables

    Example:
        kurt init
        kurt init --project-path /path/to/project
        kurt init --db-path custom/path/db.sqlite
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

        # Step 1: Create .kurt configuration file
        console.print("[dim]Creating configuration file...[/dim]")
        config = create_config(project_path=project_path, db_path=db_path)
        config_file = get_config_file_path()
        console.print(f"[green]✓[/green] Created config: {config_file}")
        console.print(f"[dim]  KURT_PROJECT_PATH={config.KURT_PROJECT_PATH}[/dim]")
        console.print(f"[dim]  KURT_DB={config.KURT_DB}[/dim]")

        # Step 2: Initialize database
        console.print()
        init_database()

        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. Discover and add URLs: [cyan]kurt ingest map https://example.com[/cyan]")
        console.print("  2. Fetch content: [cyan]kurt ingest fetch <doc-id>[/cyan]")
        console.print("  3. Or add single URL: [cyan]kurt ingest add https://example.com/page[/cyan]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


# Register command groups
main.add_command(cms)
main.add_command(cluster)
main.add_command(document)
main.add_command(index)
main.add_command(ingest)
main.add_command(research)


if __name__ == "__main__":
    main()

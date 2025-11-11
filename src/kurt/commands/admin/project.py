"""Project management CLI commands."""

import json
import re
from pathlib import Path

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command
from kurt.config import load_config
from kurt.utils import extract_section

console = Console()


# ============================================================================
# Command Group
# ============================================================================


@click.group()
def project():
    """Manage Kurt projects."""
    pass


# ============================================================================
# Project Status Command
# ============================================================================


@project.command("status")
@click.option(
    "--format",
    type=click.Choice(["pretty", "json"], case_sensitive=False),
    default="pretty",
    help="Output format",
)
@track_command
def project_status(format: str):
    """
    Show status of all projects.

    Scans the projects/ directory and extracts metadata from project.md files.

    Examples:
        kurt project status
        kurt project status --format json
    """
    try:
        config = load_config()
        projects_path = Path(config.PATH_PROJECTS)

        if not projects_path.exists():
            if format == "json":
                print(json.dumps({"projects": []}, indent=2))
            else:
                console.print("[yellow]No projects directory found[/yellow]")
            return

        # Find all project directories
        project_dirs = [d for d in projects_path.iterdir() if d.is_dir()]

        if not project_dirs:
            if format == "json":
                print(json.dumps({"projects": []}, indent=2))
            else:
                console.print("[yellow]No projects found[/yellow]")
            return

        projects_data = []

        for project_dir in sorted(project_dirs):
            project_name = project_dir.name
            project_md = project_dir / "project.md"

            project_info = {
                "name": project_name,
                "path": str(project_dir),
            }

            if project_md.exists():
                try:
                    content = project_md.read_text()

                    # Extract title from first H1
                    title_match = re.search(r"^# (.+)$", content, re.MULTILINE)
                    if title_match:
                        project_info["title"] = title_match.group(1)

                    # Extract goal
                    goal = extract_section(content, "Goal")
                    if goal:
                        project_info["goal"] = goal

                    # Extract intent category
                    intent = extract_section(content, "Intent Category")
                    if intent:
                        project_info["intent"] = intent

                except Exception as e:
                    project_info["error"] = f"Failed to read project.md: {e}"
            else:
                project_info["no_metadata"] = True

            projects_data.append(project_info)

        # Output results
        if format == "json":
            output = {
                "projects": projects_data,
                "total": len(projects_data),
            }
            print(json.dumps(output, indent=2))
        else:
            # Pretty format
            console.print(f"\n[bold cyan]Projects ({len(projects_data)} total)[/bold cyan]")
            console.print(f"[dim]{'─' * 60}[/dim]\n")

            for project in projects_data:
                console.print(f"### [cyan]{project['name']}[/cyan]")

                if project.get("title"):
                    console.print(f"[bold]{project['title']}[/bold]")

                if project.get("goal"):
                    console.print(f"- Goal: {project['goal']}")

                if project.get("intent"):
                    console.print(f"- Intent: {project['intent']}")

                if project.get("no_metadata"):
                    console.print("[dim]- No project.md found[/dim]")

                if project.get("error"):
                    console.print(f"[red]- Error: {project['error']}[/red]")

                console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

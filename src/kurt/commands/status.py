"""Kurt status command - comprehensive project status."""

import json
from pathlib import Path
from typing import Dict, List

import click
from rich.console import Console

from kurt.config import config_exists, load_config
from kurt.db.database import get_session
from kurt.db.models import Document, IngestionStatus

console = Console()


# ============================================================================
# Status Command
# ============================================================================


def get_document_counts() -> Dict[str, int]:
    """Get document counts by status."""
    try:
        session = get_session()

        total = session.query(Document).count()
        not_fetched = (
            session.query(Document)
            .filter(Document.ingestion_status == IngestionStatus.NOT_FETCHED)
            .count()
        )
        fetched = (
            session.query(Document)
            .filter(Document.ingestion_status == IngestionStatus.FETCHED)
            .count()
        )
        error = (
            session.query(Document)
            .filter(Document.ingestion_status == IngestionStatus.ERROR)
            .count()
        )

        return {
            "total": total,
            "not_fetched": not_fetched,
            "fetched": fetched,
            "error": error,
        }
    except Exception:
        return {
            "total": 0,
            "not_fetched": 0,
            "fetched": 0,
            "error": 0,
        }


def get_documents_by_domain() -> List[Dict[str, any]]:
    """Get document counts grouped by domain."""
    try:
        from collections import Counter
        from urllib.parse import urlparse

        session = get_session()
        docs = session.query(Document).all()

        domains = []
        for doc in docs:
            if doc.source_url:
                parsed = urlparse(doc.source_url)
                domains.append(parsed.netloc)

        domain_counts = Counter(domains)
        return [{"domain": domain, "count": count} for domain, count in domain_counts.most_common()]
    except Exception:
        return []


def get_cluster_count() -> int:
    """Get total number of topic clusters."""
    try:
        from kurt.db.models import TopicCluster

        session = get_session()
        return session.query(TopicCluster).count()
    except Exception:
        return 0


def get_project_summaries() -> List[Dict[str, str]]:
    """Get summary of all projects."""
    try:
        import re

        config = load_config()
        projects_path = Path(config.PATH_PROJECTS)

        if not projects_path.exists():
            return []

        project_dirs = [d for d in projects_path.iterdir() if d.is_dir()]
        projects = []

        for project_dir in sorted(project_dirs):
            project_name = project_dir.name
            project_md = project_dir / "project.md"

            project_info = {"name": project_name}

            if project_md.exists():
                try:
                    content = project_md.read_text()

                    # Extract title from first H1
                    title_match = re.search(r"^# (.+)$", content, re.MULTILINE)
                    if title_match:
                        project_info["title"] = title_match.group(1)

                    # Extract goal - first non-empty line after ## Goal
                    goal_match = re.search(
                        r"^## Goal\s*\n(.+?)(?=\n##|\Z)", content, re.MULTILINE | re.DOTALL
                    )
                    if goal_match:
                        goal_lines = goal_match.group(1).strip().split("\n")
                        project_info["goal"] = goal_lines[0].strip()

                    # Extract intent
                    intent_match = re.search(
                        r"^## Intent Category\s*\n(.+?)(?=\n##|\Z)",
                        content,
                        re.MULTILINE | re.DOTALL,
                    )
                    if intent_match:
                        intent_lines = intent_match.group(1).strip().split("\n")
                        project_info["intent"] = intent_lines[0].strip()

                except Exception:
                    pass

            projects.append(project_info)

        return projects

    except Exception:
        return []


def generate_status_markdown() -> str:
    """Generate status output as markdown string."""
    output_lines = []

    # Header
    output_lines.append("# Kurt Project Status\n")

    # Initialization status
    output_lines.append("✓ **Kurt project initialized**")
    output_lines.append("- Config: `kurt.config` found")
    output_lines.append("- Database: `.kurt/kurt.sqlite` exists\n")

    # Documents
    doc_counts = get_document_counts()
    domains = get_documents_by_domain()

    output_lines.append("## Documents")
    if doc_counts["total"] > 0:
        output_lines.append(f"**Total documents ingested: {doc_counts['total']}**\n")

        if domains:
            output_lines.append("Documents by source:")
            for domain_info in domains[:10]:
                output_lines.append(
                    f"- `{domain_info['domain']}`: {domain_info['count']} documents"
                )
            if len(domains) > 10:
                output_lines.append(f"... and {len(domains) - 10} more sources")
            output_lines.append("")
    else:
        output_lines.append("⚠ **No documents ingested yet**")
        output_lines.append("- Run: `kurt content add <url>` to add content\n")

    # Clusters
    cluster_count = get_cluster_count()
    output_lines.append("## Topic Clusters")
    if cluster_count > 0:
        output_lines.append(f"**{cluster_count} topic clusters computed**")
        output_lines.append("- View with: `kurt content cluster --url-starts-with <url>`\n")
    else:
        if doc_counts["total"] > 0:
            output_lines.append("⚠ **No clusters computed yet**")
            output_lines.append(
                "- Run: `kurt content cluster --url-starts-with <url>` to analyze content\n"
            )
        else:
            output_lines.append("No clusters (no documents to analyze)\n")

    # Projects
    projects = get_project_summaries()
    output_lines.append("## Projects")
    if projects:
        output_lines.append(f"**Found {len(projects)} project(s):**\n")

        for proj in projects:
            output_lines.append(f"### `{proj['name']}`")
            if proj.get("title"):
                output_lines.append(f"**{proj['title']}**")
            if proj.get("goal"):
                output_lines.append(f"- Goal: {proj['goal']}")
            if proj.get("intent"):
                output_lines.append(f"- Intent: {proj['intent']}")
            output_lines.append("")
    else:
        output_lines.append("⚠ **No projects created yet**")
        output_lines.append("- Create a project manually in the `projects/` directory\n")

    # Recommendations
    output_lines.append("---\n")
    output_lines.append("## Recommended Next Steps\n")

    if projects:
        output_lines.append("**You have existing projects.** Would you like to:")
        output_lines.append("- View project status: `kurt project status`")
        output_lines.append("- Add more content: `kurt content add <url>`")
    elif doc_counts["total"] > 0 and cluster_count > 0:
        output_lines.append("**Content ingested and analyzed.** Consider:")
        output_lines.append("- Create a project in the `projects/` directory")
        output_lines.append("- View documents: `kurt content list`")
    elif doc_counts["total"] > 0:
        output_lines.append("**Content ingested but not analyzed.** Next:")
        output_lines.append(
            "- Run: `kurt content cluster --url-starts-with <url>` to discover topics"
        )
    else:
        output_lines.append("**Ready to start!** Choose an approach:")
        output_lines.append("- Add content: `kurt content add <url>`")
        output_lines.append("- Initialize: `kurt init` (if needed)")

    return "\n".join(output_lines)


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
            output = {
                "initialized": True,
                "config_exists": True,
                "database_exists": True,
                "database_path": str(db_path),
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
            console.print(f"- Database: [cyan]{db_path}[/cyan] exists\n")

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

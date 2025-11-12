"""Search command - Semantic search through document content using ripgrep."""

import subprocess
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.command("search")
@click.argument("query")
@click.option(
    "--include",
    help="Glob pattern to filter files (e.g., '*/docs/*')",
)
@click.option(
    "--context",
    "-C",
    type=int,
    default=2,
    help="Lines of context before/after match (default: 2)",
)
@click.option(
    "--max-results",
    type=int,
    default=20,
    help="Maximum number of results to show (default: 20)",
)
@click.option(
    "--case-sensitive",
    is_flag=True,
    help="Case-sensitive search",
)
@click.option(
    "--regex",
    is_flag=True,
    help="Treat query as regex pattern",
)
def search_cmd(
    query: str,
    include: str,
    context: int,
    max_results: int,
    case_sensitive: bool,
    regex: bool,
):
    """
    Search through document content using ripgrep.

    Searches all fetched markdown documents for the given query.
    Uses ripgrep for fast, semantic search without database storage.

    Examples:
        kurt content search "API authentication"
        kurt content search "webhooks" --include "*/docs/*"
        kurt content search "function.*Error" --regex
        kurt content search "OAuth" --context 5 --max-results 10
    """
    from kurt.config import load_config

    try:
        config = load_config()
        sources_path = config.get_absolute_sources_path()

        if not sources_path.exists():
            console.print("[yellow]No sources directory found. Fetch some content first.[/yellow]")
            raise click.Abort()

        # Build ripgrep command
        rg_cmd = ["rg"]

        # Case sensitivity
        if not case_sensitive:
            rg_cmd.append("-i")

        # Context lines
        rg_cmd.extend(["-C", str(context)])

        # Max results
        rg_cmd.extend(["--max-count", str(max_results)])

        # Color output
        rg_cmd.append("--color=always")

        # Show line numbers
        rg_cmd.append("-n")

        # Only search markdown files
        rg_cmd.extend(["--type", "md"])

        # Add glob pattern if provided
        if include:
            rg_cmd.extend(["--glob", include])

        # Add query (as literal string unless --regex)
        if not regex:
            rg_cmd.append("-F")  # Fixed string (literal)
        rg_cmd.append(query)

        # Search in sources directory
        rg_cmd.append(str(sources_path))

        # Run ripgrep
        result = subprocess.run(
            rg_cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            # Found matches
            console.print(f"\n[bold cyan]Search Results for: {query}[/bold cyan]")
            console.print(f"[dim]{'─' * 60}[/dim]\n")
            console.print(result.stdout)

            # Count matches
            match_count = len([line for line in result.stdout.split("\n") if line.strip()])
            console.print(f"\n[dim]Found {match_count} matches[/dim]")

        elif result.returncode == 1:
            # No matches found
            console.print(f"\n[yellow]No matches found for: {query}[/yellow]")

            if include:
                console.print(f"[dim]Pattern: {include}[/dim]")

            console.print("\n[dim]Try:[/dim]")
            console.print("  • Broadening your search query")
            console.print("  • Removing the --include filter")
            console.print("  • Using --case-sensitive if needed")

        else:
            # Error occurred
            console.print(f"[red]Search error:[/red]\n{result.stderr}")
            raise click.Abort()

    except FileNotFoundError:
        console.print(
            "[red]Error:[/red] ripgrep (rg) not found. Install with: [cyan]brew install ripgrep[/cyan]"
        )
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@click.command("links")
@click.argument("document_id")
@click.option(
    "--direction",
    type=click.Choice(["outbound", "inbound"], case_sensitive=False),
    default="outbound",
    help="Link direction (outbound = from doc, inbound = to doc)",
)
@click.option(
    "--format",
    type=click.Choice(["pretty", "json"], case_sensitive=False),
    default="pretty",
    help="Output format",
)
def links_cmd(document_id: str, direction: str, format: str):
    """
    Show links from or to a document.

    Examples:
        kurt content links 550e8400
        kurt content links 550e8400 --direction inbound
        kurt content links 550e8400 --format json
    """
    from kurt.content.document import get_document_links

    try:
        links = get_document_links(document_id, direction=direction)

        if format == "json":
            import json

            print(json.dumps(links, indent=2))
        else:
            if not links:
                console.print(f"\n[yellow]No {direction} links found[/yellow]")
                return

            console.print(f"\n[bold cyan]{direction.capitalize()} Links[/bold cyan]")
            console.print(f"[dim]{'─' * 60}[/dim]\n")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Title", style="cyan")
            table.add_column("Anchor Text", style="green")

            for link in links:
                if direction == "outbound":
                    title = link["target_title"]
                else:
                    title = link["source_title"]

                anchor = link["anchor_text"] or "[no text]"
                table.add_row(title, anchor[:50])

            console.print(table)
            console.print(f"\n[dim]Total: {len(links)} links[/dim]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@click.command("prerequisites")
@click.argument("document_id")
@click.option(
    "--max-depth",
    type=int,
    default=2,
    help="Maximum link depth to traverse (default: 2)",
)
@click.option(
    "--format",
    type=click.Choice(["pretty", "json"], case_sensitive=False),
    default="pretty",
    help="Output format",
)
def prerequisites_cmd(document_id: str, max_depth: int, format: str):
    """
    Find prerequisite documents (docs to read first).

    Traverses inbound links to find documents that should be read
    before the target document.

    Examples:
        kurt content prerequisites 550e8400
        kurt content prerequisites 550e8400 --max-depth 3
        kurt content prerequisites 550e8400 --format json
    """
    from kurt.content.document import find_prerequisite_documents

    try:
        prereqs = find_prerequisite_documents(document_id, max_depth=max_depth)

        if format == "json":
            import json

            print(json.dumps(prereqs, indent=2))
        else:
            if not prereqs:
                console.print("\n[yellow]No prerequisite documents found[/yellow]")
                return

            console.print("\n[bold cyan]Prerequisite Documents[/bold cyan]")
            console.print(f"[dim]{'─' * 60}[/dim]\n")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Depth", style="yellow", justify="center")
            table.add_column("Title", style="cyan")
            table.add_column("Path", style="dim")

            for prereq in prereqs:
                path_str = " → ".join(prereq["path"])
                table.add_row(str(prereq["depth"]), prereq["title"], path_str[:50])

            console.print(table)
            console.print(f"\n[dim]Total: {len(prereqs)} prerequisites[/dim]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@click.command("related")
@click.argument("document_id")
@click.option(
    "--max-results",
    type=int,
    default=10,
    help="Maximum number of related docs to show (default: 10)",
)
@click.option(
    "--format",
    type=click.Choice(["pretty", "json"], case_sensitive=False),
    default="pretty",
    help="Output format",
)
def related_cmd(document_id: str, max_results: int, format: str):
    """
    Find related documents based on link analysis.

    Uses bidirectional link analysis to find documents related to
    the target document.

    Examples:
        kurt content related 550e8400
        kurt content related 550e8400 --max-results 20
        kurt content related 550e8400 --format json
    """
    from kurt.content.document import find_related_documents

    try:
        related = find_related_documents(document_id, max_results=max_results)

        if format == "json":
            import json

            print(json.dumps(related, indent=2))
        else:
            if not related:
                console.print("\n[yellow]No related documents found[/yellow]")
                return

            console.print("\n[bold cyan]Related Documents[/bold cyan]")
            console.print(f"[dim]{'─' * 60}[/dim]\n")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Score", style="yellow", justify="right")
            table.add_column("Title", style="cyan")
            table.add_column("Relationship", style="dim")

            for doc in related:
                table.add_row(
                    str(doc["relevance_score"]), doc["title"], doc["relationship"][:40]
                )

            console.print(table)
            console.print(f"\n[dim]Total: {len(related)} related documents[/dim]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

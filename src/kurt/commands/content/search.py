"""Search command - Search document content using ripgrep."""

import json
import shutil
import subprocess
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command

console = Console()


@click.command("search")
@track_command
@click.argument("query", type=str)
@click.option(
    "--include",
    "include_pattern",
    type=str,
    help="Filter by URL/path pattern (glob matching source_url or content_path)",
)
@click.option(
    "--case-sensitive",
    is_flag=True,
    help="Case-sensitive search (default: case-insensitive)",
)
@click.option(
    "--max-results",
    type=int,
    default=50,
    help="Maximum number of results to display (default: 50)",
)
@click.option(
    "--context",
    type=int,
    default=2,
    help="Number of context lines to show around matches (default: 2)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["summary", "detailed", "json"], case_sensitive=False),
    default="summary",
    help="Output format (summary: document list with match counts [default], detailed: full results with lines, json: JSON output)",
)
def search_cmd(
    query: str,
    include_pattern: str,
    case_sensitive: bool,
    max_results: int,
    context: int,
    output_format: str,
):
    """
    Search document content using ripgrep.

    Searches through all fetched document content for the given query.
    Returns matching documents with context and line numbers.

    Examples:
        kurt content search "authentication"
        kurt content search "API key" --include "*/docs/*"
        kurt content search "Error" --case-sensitive
        kurt content search "function" --format detailed --context 5
        kurt content search "TODO" --format json

    Requirements:
        Requires ripgrep (rg) to be installed:
        - macOS: brew install ripgrep
        - Ubuntu/Debian: apt-get install ripgrep
        - Other: https://github.com/BurntSushi/ripgrep#installation
    """
    from fnmatch import fnmatch

    from kurt.config.base import get_config_or_default
    from kurt.content.document import list_documents

    # Check if ripgrep is installed
    if not shutil.which("rg"):
        console.print("[red]Error:[/red] ripgrep (rg) is not installed")
        console.print()
        console.print("[bold]Installation:[/bold]")
        console.print("  macOS:         brew install ripgrep")
        console.print("  Ubuntu/Debian: apt-get install ripgrep")
        console.print("  Other:         https://github.com/BurntSushi/ripgrep#installation")
        raise click.Abort()

    # Get config to determine sources path
    config = get_config_or_default()
    sources_path = Path(config.PATH_SOURCES)

    if not sources_path.exists():
        console.print(f"[yellow]Warning:[/yellow] Sources directory does not exist: {sources_path}")
        console.print("[dim]Hint: Fetch some documents first with 'kurt content fetch'[/dim]")
        raise click.Abort()

    # Get all documents to filter by include pattern and map paths to documents
    all_docs = list_documents()

    if not all_docs:
        console.print("[yellow]No documents found in database[/yellow]")
        console.print("[dim]Hint: Fetch some documents first with 'kurt content fetch'[/dim]")
        raise click.Abort()

    # Apply include pattern filter if provided
    if include_pattern:
        filtered_docs = []
        for doc in all_docs:
            if (doc.source_url and fnmatch(doc.source_url, include_pattern)) or (
                doc.content_path and fnmatch(str(doc.content_path), include_pattern)
            ):
                filtered_docs.append(doc)
        docs_to_search = filtered_docs
    else:
        docs_to_search = all_docs

    if not docs_to_search:
        console.print(f"[yellow]No documents match pattern:[/yellow] {include_pattern}")
        raise click.Abort()

    # Build path to document ID mapping for lookup (only for files that exist)
    path_to_doc = {}
    for doc in docs_to_search:
        if doc.content_path:
            # content_path can be stored in different formats:
            # 1. Relative to sources_path: "example.com/index.md"
            # 2. Relative to cwd with sources: "sources/example.com/index.md"
            # 3. Absolute path
            abs_path = Path(doc.content_path)

            if abs_path.is_absolute():
                # Already absolute, use as-is
                pass
            elif doc.content_path.startswith(str(sources_path.name) + "/"):
                # Path includes sources/ prefix, resolve from cwd
                abs_path = Path.cwd() / doc.content_path
            else:
                # Path is relative to sources directory (most common case)
                abs_path = sources_path / doc.content_path

            # Only include files that actually exist on disk
            if abs_path.exists() and abs_path.is_file():
                path_to_doc[str(abs_path)] = doc

    if not path_to_doc:
        console.print("[yellow]No documents have content files to search[/yellow]")
        console.print("[dim]Hint: Some documents may not have been fetched yet[/dim]")
        raise click.Abort()

    # Build ripgrep command
    rg_cmd = ["rg"]

    # Case sensitivity
    if not case_sensitive:
        rg_cmd.append("-i")  # Case insensitive

    # Context lines
    if context > 0:
        rg_cmd.extend(["-C", str(context)])

    # Line numbers
    rg_cmd.append("-n")

    # Output with filename
    rg_cmd.append("-H")

    # Don't color output (we'll format it ourselves)
    rg_cmd.append("--color=never")

    # Max count per file (to avoid overwhelming output)
    max_per_file = max(1, max_results // len(path_to_doc)) if len(path_to_doc) > 0 else 10
    rg_cmd.extend(["-m", str(max_per_file)])

    # Query
    rg_cmd.append(query)

    # Search paths (all document content files)
    search_paths = list(path_to_doc.keys())
    rg_cmd.extend(search_paths)

    # Execute ripgrep
    try:
        result = subprocess.run(
            rg_cmd,
            capture_output=True,
            text=True,
            check=False,  # Don't raise on non-zero exit (no matches = exit code 1)
        )
    except Exception as e:
        console.print(f"[red]Error running ripgrep:[/red] {e}")
        raise click.Abort()

    # Parse results
    if result.returncode == 1:
        # No matches found
        console.print(f"[yellow]No matches found for:[/yellow] '{query}'")
        if include_pattern:
            console.print(f"[dim]in documents matching: {include_pattern}[/dim]")
        return

    if result.returncode != 0:
        # Some error occurred
        console.print(f"[red]Ripgrep error:[/red] {result.stderr}")
        raise click.Abort()

    # Parse output (format: filepath:line_number:content)
    matches = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue

        # Split on first two colons to get file:line:content
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue

        file_path = parts[0]
        line_number = parts[1]
        content = parts[2]

        # Look up document
        doc = path_to_doc.get(file_path)
        if not doc:
            continue

        matches.append(
            {
                "document_id": str(doc.id),
                "document_title": doc.title or "Untitled",
                "source_url": doc.source_url or "N/A",
                "content_path": doc.content_path or "N/A",
                "line_number": line_number,
                "content": content.strip(),
            }
        )

    # Limit total results
    if len(matches) > max_results:
        matches = matches[:max_results]

    # Output results
    if output_format == "json":
        output = {
            "query": query,
            "total_matches": len(matches),
            "matches": matches,
        }
        print(json.dumps(output, indent=2))
    elif output_format == "summary":
        # Summary table: documents with match counts (default)
        from collections import Counter

        # Count matches per document
        doc_match_counts = Counter(m["document_id"] for m in matches)

        # Build document summary list
        doc_summaries = []
        seen_docs = set()
        for match in matches:
            doc_id = match["document_id"]
            if doc_id not in seen_docs:
                seen_docs.add(doc_id)
                doc_summaries.append(
                    {
                        "document_id": doc_id,
                        "title": match["document_title"],
                        "url": match["source_url"],
                        "content_path": match["content_path"],
                        "matches": doc_match_counts[doc_id],
                    }
                )

        # Sort by match count (descending)
        doc_summaries.sort(key=lambda x: x["matches"], reverse=True)

        # Display summary table
        console.print()
        console.print("[bold cyan]Search Summary[/bold cyan]")
        console.print(f"[dim]Query: '{query}'[/dim]")
        if include_pattern:
            console.print(f"[dim]Pattern: {include_pattern}[/dim]")
        console.print(
            f"[dim]Found {len(matches)} matches across {len(doc_summaries)} documents[/dim]"
        )
        console.print()

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Matches", style="yellow", width=8, justify="right")
        table.add_column("Title", style="bold")
        table.add_column("Path", style="dim")
        table.add_column("ID", style="dim", width=12)

        for doc in doc_summaries:
            table.add_row(
                str(doc["matches"]),
                doc["title"][:60] + "..." if len(doc["title"]) > 60 else doc["title"],
                doc["content_path"][:50] + "..."
                if len(doc["content_path"]) > 50
                else doc["content_path"],
                doc["document_id"][:8] + "...",
            )

        console.print(table)
        console.print()
    else:
        # Detailed output with matching lines
        console.print()
        console.print(f"[bold cyan]Search Results[/bold cyan] (showing {len(matches)} matches)")
        console.print(f"[dim]Query: '{query}'[/dim]")
        if include_pattern:
            console.print(f"[dim]Pattern: {include_pattern}[/dim]")
        console.print()

        # Group by document for better readability
        from itertools import groupby

        for doc_id, doc_matches in groupby(matches, key=lambda m: m["document_id"]):
            doc_matches = list(doc_matches)
            first_match = doc_matches[0]

            console.print(f"[bold]{first_match['document_title']}[/bold]")
            console.print(f"[dim]{first_match['source_url']}[/dim]")
            console.print(f"[dim]Document ID: {doc_id[:8]}...[/dim]")
            console.print()

            for match in doc_matches:
                # Highlight query in content (case-insensitive if needed)
                highlighted_content = match["content"]
                if not case_sensitive:
                    # Case-insensitive highlight
                    import re

                    pattern = re.compile(re.escape(query), re.IGNORECASE)
                    highlighted_content = pattern.sub(
                        lambda m: f"[bold yellow]{m.group()}[/bold yellow]", highlighted_content
                    )
                else:
                    highlighted_content = highlighted_content.replace(
                        query, f"[bold yellow]{query}[/bold yellow]"
                    )

                console.print(f"  [cyan]Line {match['line_number']}:[/cyan] {highlighted_content}")

            console.print()

    if len(matches) >= max_results:
        console.print(
            f"[dim]Showing first {max_results} results. Use --max-results to see more.[/dim]"
        )


@click.command("links")
@click.argument("identifier", type=str)
@click.option(
    "--direction",
    type=click.Choice(["outbound", "inbound"], case_sensitive=False),
    default="outbound",
    help="Link direction: outbound (default) = links from doc, inbound = links to doc",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format",
)
def links_cmd(identifier: str, direction: str, output_format: str):
    """
    Show links from or to a document.

    Claude interprets anchor text to understand relationship types
    (prerequisites, related content, examples, references).

    Examples:
        kurt content links 550e8400                    # Show outbound links (default)
        kurt content links 550e8400 --direction inbound  # Show inbound links
        kurt content links 550e8400 --format json
    """
    from kurt.content.filtering import get_document_links

    try:
        links = get_document_links(identifier, direction=direction)

        if output_format == "json":
            print(json.dumps(links, indent=2))
        else:
            if not links:
                console.print(f"\n[yellow]No {direction} links found[/yellow]")
                return

            console.print(f"\n[bold cyan]{direction.capitalize()} Links[/bold cyan]")
            console.print(f"[dim]{'─' * 60}[/dim]\n")

            table = Table(show_header=True, header_style="bold magenta")

            if direction == "outbound":
                table.add_column("Target Title", style="cyan")
                table.add_column("Anchor Text", style="green")
                table.add_column("Target ID", style="dim", width=12)
            else:  # inbound
                table.add_column("Source Title", style="cyan")
                table.add_column("Anchor Text", style="green")
                table.add_column("Source ID", style="dim", width=12)

            for link in links:
                if direction == "outbound":
                    title = link["target_title"]
                    doc_id = link["target_id"][:8] + "..."
                else:  # inbound
                    title = link["source_title"]
                    doc_id = link["source_id"][:8] + "..."

                anchor = link["anchor_text"] or "[no text]"
                # Truncate long anchor text
                if len(anchor) > 50:
                    anchor = anchor[:47] + "..."

                table.add_row(title[:60], anchor, doc_id)

            console.print(table)
            console.print(f"\n[dim]Total: {len(links)} links[/dim]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

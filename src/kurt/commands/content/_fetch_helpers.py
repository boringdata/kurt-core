"""Helper functions for fetch command to reduce complexity.

These helpers break down the 731-line fetch_cmd() function into manageable pieces
while reusing existing utilities from filtering.py and _live_display.py.
"""

import os
from typing import Optional

import click
from rich.console import Console


def merge_identifier_into_filters(
    identifier: Optional[str],
    url: Optional[str],
    urls: Optional[str],
    file_path: Optional[str],
    files_paths: Optional[str],
    ids: Optional[str],
    console: Console,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Merge positional identifier and deprecated flags into filter strings.
    Uses existing utilities from kurt.content.filtering.

    Returns:
        Tuple of (urls, files_paths, ids) with merged values
    """
    # Handle positional identifier
    if identifier:
        if identifier.startswith(("http://", "https://")):
            urls = f"{identifier},{urls}" if urls else identifier
        elif (
            os.path.exists(identifier)
            or identifier.startswith(("./", "../", "/"))
            or "/" in identifier
        ):
            files_paths = f"{identifier},{files_paths}" if files_paths else identifier
        else:
            # Document ID - use existing utility
            from kurt.content.filtering import resolve_identifier_to_doc_id

            try:
                doc_id = resolve_identifier_to_doc_id(identifier)
                ids = f"{doc_id},{ids}" if ids else doc_id
            except ValueError as e:
                console.print(f"[red]Error:[/red] {e}")
                raise click.Abort()

    # Merge deprecated --url flag
    if url:
        console.print("[yellow]⚠️  --url is deprecated, use positional IDENTIFIER instead[/yellow]")
        console.print("[dim]Example: kurt content fetch https://example.com/article[/dim]")
        urls = f"{url},{urls}" if urls else url

    # Merge deprecated --file flag
    if file_path:
        console.print("[yellow]⚠️  --file is deprecated, use positional IDENTIFIER instead[/yellow]")
        console.print("[dim]Example: kurt content fetch ./docs/article.md[/dim]")
        files_paths = f"{file_path},{files_paths}" if files_paths else file_path

    return urls, files_paths, ids


def handle_force_flag(force: bool, yes_flag: bool, refetch: bool, console: Console) -> bool:
    """
    Handle --force deprecation warning and return effective refetch value.

    Returns:
        effective_refetch (bool)
    """
    if force and not yes_flag and not refetch:
        console.print(
            "[yellow]⚠️  --force is deprecated, use --yes/-y for confirmations "
            "and --refetch to re-fetch documents[/yellow]"
        )
    return refetch or force


def display_result_messages(result: dict, console: Console) -> None:
    """Display warnings and errors from select_documents_for_fetch result."""
    for warning in result["warnings"]:
        console.print(f"[yellow]Warning:[/yellow] {warning}")

    for error in result["errors"]:
        console.print(f"[red]Error:[/red] {error}")


def display_refetch_warning(refetch: bool, excluded_fetched_count: int, console: Console) -> None:
    """Display warning about re-fetching already FETCHED documents."""
    if refetch and excluded_fetched_count > 0:
        console.print(
            f"[yellow]⚠️  Note:[/yellow] {excluded_fetched_count} document(s) are already "
            "FETCHED and will be re-fetched (--refetch enabled)"
        )
        console.print(
            "[dim]This will re-download and re-index content, which may incur LLM costs[/dim]\n"
        )


def display_no_documents_help(
    excluded_fetched_count: int,
    in_cluster: Optional[str],
    include_pattern: Optional[str],
    urls: Optional[str],
    ids: Optional[str],
    console: Console,
) -> None:
    """Display helpful message when no documents found."""
    if excluded_fetched_count > 0:
        console.print(
            f"[yellow]Found {excluded_fetched_count} document(s), but all are already FETCHED[/yellow]"
        )
        console.print(
            "\n[dim]By default, 'kurt content fetch' skips documents that are already FETCHED.[/dim]"
        )
        console.print("[dim]To re-fetch these documents, use the --refetch flag:[/dim]")

        # Show appropriate example command
        if in_cluster:
            console.print(
                f"\n  [cyan]kurt content fetch --in-cluster '{in_cluster}' --refetch[/cyan]"
            )
        elif include_pattern:
            console.print(
                f"\n  [cyan]kurt content fetch --include '{include_pattern}' --refetch[/cyan]"
            )
        elif urls:
            console.print(f"\n  [cyan]kurt content fetch --urls '{urls}' --refetch[/cyan]")
        elif ids:
            id_list = ids.split(",")
            if len(id_list) == 1:
                console.print(f"\n  [cyan]kurt content fetch {id_list[0]} --refetch[/cyan]")
            else:
                console.print(f"\n  [cyan]kurt content fetch --ids '{ids}' --refetch[/cyan]")
        else:
            console.print("\n  [cyan]kurt content fetch <your-filters> --refetch[/cyan]")

        # Show view command
        console.print("\n[dim]To view already fetched content, use:[/dim]")
        if in_cluster:
            console.print(f"  [cyan]kurt content list --in-cluster '{in_cluster}'[/cyan]")
        else:
            console.print("  [cyan]kurt content list --with-status FETCHED[/cyan]")
    else:
        console.print("[yellow]No documents found matching filters[/yellow]")


def display_dry_run_preview(docs: list, concurrency: int, result: dict, console: Console) -> None:
    """Display dry-run preview with cost and time estimates."""
    console.print("[bold]DRY RUN - Preview only (no actual fetching)[/bold]\n")
    console.print(f"[cyan]Would fetch {len(docs)} documents:[/cyan]\n")

    for doc in docs[:10]:
        console.print(f"  • {doc.source_url or doc.content_path}")
    if len(docs) > 10:
        console.print(f"  [dim]... and {len(docs) - 10} more[/dim]")

    # Estimate time
    avg_fetch_time_seconds = 3
    estimated_time_seconds = (len(docs) / concurrency) * avg_fetch_time_seconds

    if estimated_time_seconds < 60:
        time_estimate = f"{int(estimated_time_seconds)} seconds"
    else:
        time_estimate = f"{int(estimated_time_seconds / 60)} minutes"

    console.print(f"\n[dim]Estimated cost: ${result['estimated_cost']:.2f} (LLM indexing)[/dim]")
    console.print(f"[dim]Estimated time: ~{time_estimate} (with concurrency={concurrency})[/dim]")


def check_guardrails(docs: list, concurrency: int, force_mode: bool, console: Console) -> bool:
    """
    Check safety guardrails and prompt for confirmation if needed.

    Returns:
        True if should proceed, False if user aborted
    """
    # Check concurrency limit
    if concurrency > 20 and not force_mode:
        console.print(
            f"[yellow]⚠️  High concurrency ({concurrency}) may trigger rate limits[/yellow]"
        )
        console.print("[dim]Use --yes/-y or set KURT_FORCE=1 to skip this warning[/dim]")
        if not click.confirm("Continue anyway?"):
            console.print("[dim]Aborted[/dim]")
            return False

    # Check document count
    if len(docs) > 100 and not force_mode:
        console.print(f"[yellow]⚠️  About to fetch {len(docs)} documents[/yellow]")
        if not click.confirm("Continue?"):
            console.print("[dim]Aborted[/dim]")
            return False

    return True


def get_engine_display(docs: list, engine: Optional[str]) -> str:
    """Determine engine display string based on document types."""
    from kurt.content.fetch import _get_fetch_engine

    cms_count = sum(1 for d in docs if d.cms_platform and d.cms_instance)
    web_count = len(docs) - cms_count
    has_cms = cms_count > 0
    has_web = web_count > 0

    resolved_engine = _get_fetch_engine(override=engine)
    engine_displays = {
        "trafilatura": "Trafilatura (free)",
        "firecrawl": "Firecrawl (API)",
        "httpx": "httpx (fetching) + trafilatura (extraction)",
    }

    if has_cms and has_web:
        web_engine_display = engine_displays.get(resolved_engine, f"{resolved_engine} (unknown)")
        return f"CMS API + {web_engine_display}"
    elif has_cms:
        return "CMS API"
    else:
        return engine_displays.get(resolved_engine, f"{resolved_engine} (unknown)")


def build_intro_messages(
    doc_count: int,
    concurrency: int,
    engine_display: str,
    skip_index: bool,
) -> list[str]:
    """Build intro block messages for fetch operation."""
    messages = [
        f"Fetching {doc_count} document(s) with {concurrency} parallel downloads",
        f"[dim]Engine: {engine_display}[/dim]",
    ]

    if not skip_index:
        messages.append(
            f"[dim]LLM Indexing: enabled (parallel with concurrency={concurrency})[/dim]\n"
        )
    else:
        messages.append("[dim]LLM Indexing: skipped[/dim]\n")

    return messages


def build_background_filter_desc(
    include_pattern: Optional[str],
    urls: Optional[str],
    in_cluster: Optional[str],
    with_status: Optional[str],
    with_content_type: Optional[str],
) -> Optional[str]:
    """Build filter description for background workflow display."""
    filter_desc = []
    if include_pattern:
        filter_desc.append(f"include: {include_pattern}")
    if urls:
        filter_desc.append(f"urls: {urls[:50]}...")
    if in_cluster:
        filter_desc.append(f"cluster: {in_cluster}")
    if with_status:
        filter_desc.append(f"status: {with_status}")
    if with_content_type:
        filter_desc.append(f"type: {with_content_type}")

    return " | ".join(filter_desc) if filter_desc else None


def display_json_output(docs: list, console: Console) -> bool:
    """
    Display JSON output and prompt for confirmation.

    Returns:
        True if user confirms, False if aborted
    """
    import json

    output = {
        "total": len(docs),
        "documents": [{"id": str(d.id), "url": d.source_url or d.content_path} for d in docs],
    }
    console.print(json.dumps(output, indent=2))
    if not click.confirm("\nProceed with fetch?"):
        return False
    return True


def display_fetch_errors(failed: list, console: Console) -> None:
    """Display error details for failed documents."""
    if not failed:
        return

    console.print("\n[bold red]Failed documents:[/bold red]")
    for result in failed:
        doc_id = result.get("document_id", "unknown")[:8]
        url = result.get("source_url", result.get("identifier", "unknown"))
        error = result.get("error", "Unknown error")
        console.print(f"  [red]✗[/red] [{doc_id}] {url}")
        console.print(f"    [dim red]Error: {error}[/dim red]")


def display_indexing_errors(extract_results: dict, console: Console) -> None:
    """Display error details for failed indexing."""
    index_failed = extract_results.get("failed", 0)
    if index_failed == 0:
        return

    index_errors = extract_results.get("errors", [])
    if not index_errors:
        return

    console.print("\n[bold red]Indexing errors:[/bold red]")
    for error_result in index_errors:
        doc_id = error_result.get("document_id", "unknown")[:8]
        error = error_result.get("error", "Unknown error")
        console.print(f"  [red]✗[/red] [{doc_id}]")
        console.print(f"    [dim red]Error: {error}[/dim red]")

"""Helper functions for fetch command to reduce complexity.

Simplified helpers that leverage kurt.core.display utilities.
"""

import json
import os
from typing import Optional

import click

from kurt.core.display import print_info, print_inline_table, print_warning


def merge_identifier_into_filters(
    identifier: Optional[str],
    url: Optional[str],
    urls: Optional[str],
    file_path: Optional[str],
    files_paths: Optional[str],
    ids: Optional[str],
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Merge positional identifier and deprecated flags into filter strings.

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
            from kurt.utils.filtering import resolve_identifier_to_doc_id

            try:
                doc_id = resolve_identifier_to_doc_id(identifier)
                ids = f"{doc_id},{ids}" if ids else doc_id
            except ValueError as e:
                print_warning(str(e))
                raise click.Abort()

    # Merge deprecated --url flag
    if url:
        print_warning("--url is deprecated, use positional IDENTIFIER instead")
        print_info("Example: kurt content fetch https://example.com/article")
        urls = f"{url},{urls}" if urls else url

    # Merge deprecated --file flag
    if file_path:
        print_warning("--file is deprecated, use positional IDENTIFIER instead")
        print_info("Example: kurt content fetch ./docs/article.md")
        files_paths = f"{file_path},{files_paths}" if files_paths else file_path

    return urls, files_paths, ids


def display_result_messages(result: dict) -> None:
    """Display warnings and errors from select_documents_for_fetch result."""
    for warning in result["warnings"]:
        print_warning(warning)
    for error in result["errors"]:
        print_warning(f"Error: {error}")


def display_no_documents_help(
    excluded_fetched_count: int,
    in_cluster: Optional[str],
    include_pattern: Optional[str],
    urls: Optional[str],
    ids: Optional[str],
) -> None:
    """Display helpful message when no documents found."""
    if excluded_fetched_count > 0:
        print_warning(f"Found {excluded_fetched_count} document(s), but all are already FETCHED")
        print_info("By default, 'kurt content fetch' skips documents that are already FETCHED.")
        print_info("To re-fetch these documents, use the --refetch flag:")

        # Show appropriate example command
        if in_cluster:
            print_info(f"  kurt content fetch --in-cluster '{in_cluster}' --refetch")
        elif include_pattern:
            print_info(f"  kurt content fetch --include '{include_pattern}' --refetch")
        elif urls:
            print_info(f"  kurt content fetch --urls '{urls}' --refetch")
        elif ids:
            id_list = ids.split(",")
            if len(id_list) == 1:
                print_info(f"  kurt content fetch {id_list[0]} --refetch")
            else:
                print_info(f"  kurt content fetch --ids '{ids}' --refetch")
        else:
            print_info("  kurt content fetch <your-filters> --refetch")

        print_info("To view already fetched content, use:")
        if in_cluster:
            print_info(f"  kurt content list --in-cluster '{in_cluster}'")
        else:
            print_info("  kurt content list --with-status FETCHED")
    else:
        print_warning("No documents found matching filters")


def display_dry_run_preview(docs: list, concurrency: int, result: dict) -> None:
    """Display dry-run preview with cost and time estimates using core tables."""
    print_info("DRY RUN - Preview only (no actual fetching)")
    print_info(f"Would fetch {len(docs)} documents:")

    # Use inline table for documents
    doc_items = [{"url": doc.source_url or doc.content_path, "id": str(doc.id)[:8]} for doc in docs]
    print_inline_table(doc_items, columns=["url", "id"], max_items=10)

    # Estimate time
    avg_fetch_time_seconds = 3
    estimated_time_seconds = (len(docs) / concurrency) * avg_fetch_time_seconds
    time_estimate = (
        f"{int(estimated_time_seconds)} seconds"
        if estimated_time_seconds < 60
        else f"{int(estimated_time_seconds / 60)} minutes"
    )

    print_info(f"Estimated cost: ${result['estimated_cost']:.2f} (LLM indexing)")
    print_info(f"Estimated time: ~{time_estimate} (with concurrency={concurrency})")


def check_guardrails(docs: list, concurrency: int, force_mode: bool) -> bool:
    """
    Check safety guardrails and prompt for confirmation if needed.

    Returns:
        True if should proceed, False if user aborted
    """
    # Check concurrency limit
    if concurrency > 20 and not force_mode:
        print_warning(f"High concurrency ({concurrency}) may trigger rate limits")
        print_info("Use --yes/-y or set KURT_FORCE=1 to skip this warning")
        if not click.confirm("Continue anyway?"):
            print_info("Aborted")
            return False

    # Check document count
    if len(docs) > 100 and not force_mode:
        print_warning(f"About to fetch {len(docs)} documents")
        if not click.confirm("Continue?"):
            print_info("Aborted")
            return False

    return True


def get_engine_display(docs: list, engine: Optional[str]) -> str:
    """Determine engine display string based on document types."""
    from kurt.utils.fetching import get_fetch_engine

    cms_count = sum(1 for d in docs if d.cms_platform and d.cms_instance)
    has_cms = cms_count > 0
    has_web = (len(docs) - cms_count) > 0

    resolved_engine = get_fetch_engine(override=engine)
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


def display_json_output(docs: list) -> bool:
    """
    Display JSON output and prompt for confirmation.

    Returns:
        True if user confirms, False if aborted
    """
    output = {
        "total": len(docs),
        "documents": [{"id": str(d.id), "url": d.source_url or d.content_path} for d in docs],
    }
    print(json.dumps(output, indent=2))
    if not click.confirm("\nProceed with fetch?"):
        return False
    return True

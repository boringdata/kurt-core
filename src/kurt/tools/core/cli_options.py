"""Shared CLI utilities for Kurt commands.

This module provides:
- Reusable Click options for consistency across commands
- Output formatting helpers (wraps kurt.core.status)
"""

from __future__ import annotations

import json
from typing import Any

import click

# =============================================================================
# Filter Options
# =============================================================================

include_option = click.option(
    "--include",
    "include_pattern",
    help="Filter documents by glob pattern (matches source_url or content_path)",
)

ids_option = click.option(
    "--ids",
    help="Comma-separated document IDs (supports partial UUIDs, URLs, file paths)",
)

limit_option = click.option(
    "--limit",
    type=int,
    help="Maximum number of documents to process/display",
)

exclude_option = click.option(
    "--exclude",
    "exclude_pattern",
    help="Exclude documents matching glob pattern",
)

in_cluster_option = click.option(
    "--in-cluster",
    help="Filter documents in specified cluster (not yet implemented)",
)

with_status_option = click.option(
    "--with-status",
    type=click.Choice(["NOT_FETCHED", "FETCHED", "ERROR"], case_sensitive=False),
    help="Filter by ingestion status",
)

with_content_type_option = click.option(
    "--with-content-type",
    help="Filter by content type (not yet implemented)",
)

# =============================================================================
# Advanced Filter Options
# =============================================================================

url_contains_option = click.option(
    "--url-contains",
    help="Filter URLs containing this substring (e.g., '/docs/', 'api')",
)

file_extension_option = click.option(
    "--file-ext",
    help="Filter by file extension (e.g., 'md', 'html', 'pdf')",
)

source_type_option = click.option(
    "--source-type",
    type=click.Choice(["url", "file", "cms"], case_sensitive=False),
    help="Filter by source type (url, file, or cms)",
)

has_content_option = click.option(
    "--has-content/--no-content",
    default=None,
    help="Filter documents with/without content",
)

min_content_length_option = click.option(
    "--min-content-length",
    type=int,
    help="Minimum content length in characters",
)

fetch_engine_option = click.option(
    "--fetch-engine",
    type=click.Choice(["trafilatura", "firecrawl", "httpx"], case_sensitive=False),
    help="Filter by fetch engine used",
)

offset_option = click.option(
    "--offset",
    type=int,
    help="Number of documents to skip (for pagination)",
)

sort_by_option = click.option(
    "--sort-by",
    type=click.Choice(["created_at", "source_url", "content_length"], case_sensitive=False),
    help="Sort results by field (default: created_at)",
)

sort_order_option = click.option(
    "--sort-order",
    type=click.Choice(["asc", "desc"], case_sensitive=False),
    default="asc",
    help="Sort order (asc or desc, default: asc)",
)

# =============================================================================
# Output Format Options
# =============================================================================

format_option = click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "text"], case_sensitive=False),
    default="text",
    help="Output format (json for AI agents, text for humans)",
)

format_table_option = click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "table"], case_sensitive=False),
    default="table",
    help="Output format (json for AI agents, table for humans)",
)

# =============================================================================
# Safety/Confirmation Options
# =============================================================================

dry_run_option = click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would happen without making changes",
)

yes_option = click.option(
    "--yes",
    "-y",
    "yes_flag",
    is_flag=True,
    help="Skip confirmation prompts (for automation/CI)",
)

# =============================================================================
# Background/Workflow Options
# =============================================================================

background_option = click.option(
    "--background",
    is_flag=True,
    help="Run as background workflow (non-blocking)",
)

priority_option = click.option(
    "--priority",
    type=int,
    default=10,
    help="Priority for background execution (1=highest, default=10)",
)


# =============================================================================
# Composed Decorators
# =============================================================================


def add_filter_options(
    include: bool = True,
    ids: bool = True,
    cluster: bool = True,
    status: bool = True,
    content_type: bool = True,
    limit: bool = True,
    exclude: bool = False,
    url_contains: bool = True,
    file_ext: bool = False,
    source_type: bool = False,
    has_content: bool = False,
    min_content_length: bool = False,
    offset: bool = False,
    sort_by: bool = False,
):
    """
    Decorator to add standard filter options to a command.

    Usage:
        @click.command("fetch")
        @add_filter_options()
        def fetch(include_pattern, ids, in_cluster, with_status, with_content_type, limit, url_contains):
            ...
    """

    def decorator(f):
        if sort_by:
            f = sort_order_option(f)
            f = sort_by_option(f)
        if offset:
            f = offset_option(f)
        if min_content_length:
            f = min_content_length_option(f)
        if has_content:
            f = has_content_option(f)
        if source_type:
            f = source_type_option(f)
        if file_ext:
            f = file_extension_option(f)
        if exclude:
            f = exclude_option(f)
        if limit:
            f = limit_option(f)
        if content_type:
            f = with_content_type_option(f)
        if status:
            f = with_status_option(f)
        if cluster:
            f = in_cluster_option(f)
        if ids:
            f = ids_option(f)
        if url_contains:
            f = url_contains_option(f)
        if include:
            f = include_option(f)
        return f

    return decorator


def add_output_options(table_format: bool = False):
    """Decorator to add output format option."""

    def decorator(f):
        if table_format:
            f = format_table_option(f)
        else:
            f = format_option(f)
        return f

    return decorator


def add_background_options():
    """Decorator to add --background and --priority options."""

    def decorator(f):
        f = priority_option(f)
        f = background_option(f)
        return f

    return decorator


def add_confirmation_options():
    """Decorator to add --yes/-y and --dry-run options."""

    def decorator(f):
        f = yes_option(f)
        f = dry_run_option(f)
        return f

    return decorator


# =============================================================================
# Output Formatting
# =============================================================================


def print_json(data: Any, envelope: bool = False) -> None:
    """Print JSON output for AI agents.

    Args:
        data: Data to serialize as JSON
        envelope: If True, wrap in robot success envelope (beads-style)

    Example:
        print_json({"count": 42})  # Raw JSON
        print_json({"count": 42}, envelope=True)  # {"success": true, "data": {...}}
    """
    if envelope:
        from kurt.cli.robot import robot_success

        print(robot_success(data))
    else:
        print(json.dumps(data, indent=2, default=str))


# =============================================================================
# Robot Mode Re-exports
# =============================================================================

# Re-export robot mode utilities for convenience
# Usage: from kurt.tools.core import OutputContext, robot_success, robot_error
try:
    from kurt.cli.robot import (
        ErrorCode,
        OutputContext,
        is_json_mode,
        is_tty,
        robot_error,
        robot_success,
    )

    __all__ = [
        # Filter options
        "include_option",
        "ids_option",
        "limit_option",
        "exclude_option",
        # Output options
        "format_option",
        "format_table_option",
        # Confirmation options
        "dry_run_option",
        "yes_option",
        # Background options
        "background_option",
        "priority_option",
        # Composed decorators
        "add_filter_options",
        "add_output_options",
        "add_background_options",
        "add_confirmation_options",
        # Output formatting
        "print_json",
        # Robot mode
        "OutputContext",
        "robot_success",
        "robot_error",
        "ErrorCode",
        "is_json_mode",
        "is_tty",
    ]
except ImportError:
    # Robot module not yet installed
    pass

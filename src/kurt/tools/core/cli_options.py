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


def print_workflow_status(workflow_id: str, *, as_json: bool = False) -> None:
    """Print live workflow status from Dolt observability tables."""
    from kurt.db.dolt import DoltDB

    db = DoltDB(".")
    if not db.exists():
        print(json.dumps({"error": "Database not available"}, indent=2))
        return

    result = db.query(
        "SELECT id, workflow, status, started_at, completed_at, error, metadata FROM workflow_runs WHERE id = ?",
        [workflow_id],
    )

    if not result.rows:
        print(json.dumps({"error": "Workflow not found"}, indent=2))
        return

    row = result.rows[0]
    status = {
        "workflow_id": row.get("id"),
        "workflow": row.get("workflow"),
        "status": row.get("status"),
        "started_at": str(row.get("started_at")) if row.get("started_at") else None,
        "completed_at": str(row.get("completed_at")) if row.get("completed_at") else None,
        "error": row.get("error"),
    }

    if as_json:
        print(json.dumps(status, indent=2, default=str))
    else:
        print(f"Workflow: {status['workflow']}")
        print(f"Status: {status['status']}")
        print(f"Started: {status['started_at']}")
        if status["completed_at"]:
            print(f"Completed: {status['completed_at']}")
        if status["error"]:
            print(f"Error: {status['error']}")


def print_workflow_logs(
    workflow_id: str,
    *,
    step_name: str | None = None,
    limit: int = 200,
) -> None:
    """Print workflow step logs from Dolt observability tables."""
    from kurt.db.dolt import DoltDB

    db = DoltDB(".")
    if not db.exists():
        print("Database not available")
        return

    sql = """
        SELECT step_id, step_type, status, started_at, completed_at, error_count, errors
        FROM step_logs
        WHERE run_id = ?
    """
    params: list[Any] = [workflow_id]

    if step_name:
        sql += " AND step_id = ?"
        params.append(step_name)

    sql += " ORDER BY started_at LIMIT ?"
    params.append(limit)

    result = db.query(sql, params)

    if not result.rows:
        print("No step logs found")
        return

    for row in result.rows:
        status_icon = {"completed": "[OK]", "failed": "[ERR]", "running": "[...]"}.get(
            row.get("status", ""), "[?]"
        )
        print(f"{status_icon} {row.get('step_id')}: {row.get('status')} ({row.get('step_type')})")
        if row.get("error_count", 0) > 0:
            print(f"    Errors: {row.get('error_count')}")


def print_json(data: Any) -> None:
    """Print JSON output for AI agents."""
    print(json.dumps(data, indent=2, default=str))


def poll_workflow_progress(
    workflow_id: str,
    *,
    step_name: str | None = None,
    since_offset: int | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Poll workflow progress for live updates from Dolt."""
    from kurt.db.dolt import DoltDB

    db = DoltDB(".")
    if not db.exists():
        return {"error": "Database not available", "events": [], "next_offset": 0}

    sql = """
        SELECT id, step_id, event_type, event_data, created_at
        FROM step_events
        WHERE run_id = ?
    """
    params: list[Any] = [workflow_id]

    if step_name:
        sql += " AND step_id = ?"
        params.append(step_name)

    if since_offset:
        sql += " AND id > ?"
        params.append(since_offset)

    sql += " ORDER BY id LIMIT ?"
    params.append(limit)

    result = db.query(sql, params)

    events = []
    next_offset = since_offset or 0
    for row in result.rows:
        event_id = row.get("id", 0)
        if event_id > next_offset:
            next_offset = event_id
        events.append({
            "id": event_id,
            "step_id": row.get("step_id"),
            "event_type": row.get("event_type"),
            "event_data": row.get("event_data"),
            "created_at": str(row.get("created_at")) if row.get("created_at") else None,
        })

    return {"events": events, "next_offset": next_offset}


def poll_workflow_logs(
    workflow_id: str,
    *,
    step_name: str | None = None,
    since_offset: int | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Poll workflow logs for live updates from Dolt."""
    # For logs, we just return the same as poll_workflow_progress
    # since step events contain the log information
    return poll_workflow_progress(
        workflow_id,
        step_name=step_name,
        since_offset=since_offset,
        limit=limit,
    )

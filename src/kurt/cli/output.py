"""Output formatting for CLI commands.

Thin wrappers around kurt.core.status for consistent CLI output.
"""

from __future__ import annotations

import json
from typing import Any

def print_workflow_status(workflow_id: str, *, as_json: bool = False) -> None:
    """Print live workflow status."""
    from kurt.core import format_live_status, get_live_status

    status = get_live_status(workflow_id)
    if as_json:
        print(json.dumps(status, indent=2, default=str))
    else:
        print(format_live_status(status))


def print_workflow_logs(
    workflow_id: str,
    *,
    step_name: str | None = None,
    limit: int = 200,
) -> None:
    """Print workflow logs."""
    from kurt.core import format_step_logs, get_step_logs

    logs = get_step_logs(workflow_id, step_name=step_name, limit=limit)
    print(format_step_logs(logs))


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
    """Poll workflow progress for live updates."""
    from kurt.core import get_progress_page

    return get_progress_page(
        workflow_id,
        step_name=step_name,
        since_offset=since_offset,
        limit=limit,
    )


def poll_workflow_logs(
    workflow_id: str,
    *,
    step_name: str | None = None,
    since_offset: int | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Poll workflow logs for live updates."""
    from kurt.core import get_step_logs_page

    return get_step_logs_page(
        workflow_id,
        step_name=step_name,
        since_offset=since_offset,
        limit=limit,
    )

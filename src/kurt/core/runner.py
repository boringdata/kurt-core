from __future__ import annotations

import os
import sys
from typing import Any, Callable

from dbos import DBOS

from kurt.core.background import start_background_workflow, workflow_path_for
from kurt.core.dbos import init_dbos


def _store_parent_workflow_id() -> None:
    """
    Store parent workflow ID from environment if available.

    This enables nested workflow display - when an agent workflow runs kurt commands,
    those child workflows will be linked to their parent agent workflow.
    """
    parent_id = os.environ.get("KURT_PARENT_WORKFLOW_ID")
    if parent_id:
        try:
            DBOS.set_event("parent_workflow_id", parent_id)
        except Exception:
            pass  # Don't fail workflow if event storage fails


def run_workflow(
    workflow_func: Callable[..., Any],
    *args: Any,
    background: bool = False,
    priority: int = 10,
    display: bool | None = None,
    **kwargs: Any,
) -> Any:
    """
    Run a workflow synchronously or in background.

    Args:
        workflow_func: The workflow function to run
        *args: Positional arguments to pass to the workflow
        background: If True, run in background worker process
        priority: Priority for background workflows (lower = higher priority)
        display: Show live console display. Default: True for foreground, False for background
        **kwargs: Keyword arguments to pass to the workflow
    """
    if background:
        workflow_path = workflow_path_for(workflow_func)
        return start_background_workflow(
            workflow_path,
            args=args,
            kwargs=kwargs,
            priority=priority,
        )

    # Foreground mode: enable display by default
    from kurt.core.display import set_display_enabled, set_display_mode

    show_display = display if display is not None else True
    use_rich = sys.stdout.isatty()

    try:
        if show_display:
            set_display_mode("rich" if use_rich else "plain")
        else:
            set_display_mode("rich")
        set_display_enabled(show_display)
        init_dbos()
        handle = DBOS.start_workflow(workflow_func, *args, **kwargs)
        # Store parent workflow relationship if running inside an agent workflow
        _store_parent_workflow_id()
        return handle.get_result()
    finally:
        set_display_enabled(False)
        set_display_mode("rich")

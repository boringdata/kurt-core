from __future__ import annotations

from typing import Any, Callable

from dbos import DBOS

from kurt_new.core.background import start_background_workflow, workflow_path_for
from kurt_new.core.dbos import init_dbos


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
    from kurt_new.core.display import set_display_enabled

    show_display = display if display is not None else True

    try:
        set_display_enabled(show_display)
        init_dbos()
        handle = DBOS.start_workflow(workflow_func, *args, **kwargs)
        return handle.get_result()
    finally:
        set_display_enabled(False)

"""
Background workflow worker process for kurt.

Runs a DBOS workflow in a detached process so CLI commands can return immediately.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable

from dbos import DBOS

from kurt.core.dbos import destroy_dbos, init_dbos


def _resolve_workflow(workflow_path: str) -> Callable[..., Any]:
    if ":" not in workflow_path:
        raise ValueError("workflow_path must be in module:function format")
    module_path, func_name = workflow_path.split(":", 1)
    module = importlib.import_module(module_path)
    workflow_func = getattr(module, func_name, None)
    if not callable(workflow_func):
        raise ValueError(f"Workflow function not found: {workflow_path}")
    return workflow_func


def _redirect_output(log_file: Path) -> None:
    log_fd = os.open(str(log_file), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.dup2(log_fd, sys.stdout.fileno())
    os.dup2(log_fd, sys.stderr.fileno())
    os.close(log_fd)


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


def run_workflow_worker(workflow_path: str, workflow_args_json: str, priority: int = 10) -> None:
    """
    Execute a workflow in a background worker process.
    """
    init_dbos()

    workflow_func = _resolve_workflow(workflow_path)
    payload = json.loads(workflow_args_json)
    args = payload.get("args", [])
    kwargs = payload.get("kwargs", {})

    log_dir = Path(".kurt/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    temp_log_file = log_dir / f"workflow-temp-{os.getpid()}.log"
    _redirect_output(temp_log_file)

    handle = DBOS.start_workflow(workflow_func, *args, **kwargs)

    # Store parent workflow relationship if running inside an agent workflow
    _store_parent_workflow_id()

    final_log_file = log_dir / f"workflow-{handle.workflow_id}.log"
    temp_log_file.rename(final_log_file)
    _redirect_output(final_log_file)

    id_file = os.environ.get("KURT_NEW_WORKFLOW_ID_FILE")
    if id_file:
        with open(id_file, "w") as handle_id:
            handle_id.write(handle.workflow_id)

    max_wait_time = 600
    start_time = time.time()
    poll_interval = 0.5

    while time.time() - start_time < max_wait_time:
        try:
            status = handle.get_status()
            if status.status in ["SUCCESS", "ERROR", "RETRIES_EXCEEDED", "CANCELLED"]:
                break
        except Exception:
            pass

        time.sleep(poll_interval)

    destroy_dbos()
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python -m kurt.core._worker <workflow_path> <workflow_args_json> [priority]",
            file=sys.stderr,
        )
        sys.exit(1)

    workflow_path_arg = sys.argv[1]
    workflow_args_arg = sys.argv[2]
    priority_arg = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    run_workflow_worker(workflow_path_arg, workflow_args_arg, priority_arg)

"""
Background workflow worker process.

This module provides a standalone worker that can execute workflows
in a completely independent process, allowing the parent CLI to exit immediately.
"""

import json
import os
import sys
import time

from kurt.workflows.logging_utils import setup_workflow_logging


def run_workflow_worker(workflow_name: str, workflow_args_json: str, priority: int = 10):
    """
    Execute a workflow in a background worker process.

    This function is called by subprocess.Popen from the CLI to run
    a workflow in a completely independent Python process.

    Args:
        workflow_name: Name of the workflow function (e.g., "map_url_workflow")
        workflow_args_json: JSON-encoded workflow arguments
        priority: Priority for workflow execution (1=highest, default=10)
    """
    # Initialize DBOS fresh in this process

    from kurt.workflows import get_dbos, init_dbos

    init_dbos()
    get_dbos()

    # Import workflow modules to register them
    from kurt.content.map import workflow as _map  # noqa
    from kurt.content.fetch import workflow as _fetch  # noqa
    from kurt.content.indexing import workflow_indexing as _indexing_workflow  # noqa

    # Get the workflow function
    workflow_func = None
    if workflow_name == "map_url_workflow":
        from kurt.content.map.workflow import map_url_workflow

        workflow_func = map_url_workflow
    elif workflow_name == "fetch_workflow":
        from kurt.content.fetch.workflow import fetch_workflow

        workflow_func = fetch_workflow
    elif workflow_name == "complete_indexing_workflow":
        from kurt.content.indexing.workflow_indexing import complete_indexing_workflow

        workflow_func = complete_indexing_workflow
    else:
        sys.exit(1)  # Unknown workflow

    # Parse arguments
    workflow_args = json.loads(workflow_args_json)

    # Set up a temporary log file BEFORE starting the workflow
    # This ensures logging is configured when the workflow starts executing
    from pathlib import Path

    log_dir = Path(".kurt/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create temporary log file for workflow (we'll rename it once we know the ID)
    temp_log_file = log_dir / f"workflow-temp-{os.getpid()}.log"

    # Configure Python logging early - before workflow starts
    setup_workflow_logging(temp_log_file)

    # Redirect stdout/stderr to the temp log file
    log_fd = os.open(str(temp_log_file), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.dup2(log_fd, sys.stdout.fileno())
    os.dup2(log_fd, sys.stderr.fileno())
    os.close(log_fd)

    # Start the workflow directly (not via queue) to ensure logging works
    # When using queues, the workflow runs in a worker thread that doesn't
    # have our logging configuration. Starting directly ensures logs are captured.
    from dbos import DBOS

    handle = DBOS.start_workflow(workflow_func, **workflow_args)

    # Now we know the workflow ID, rename the log file
    final_log_file = log_dir / f"workflow-{handle.workflow_id}.log"
    temp_log_file.rename(final_log_file)

    # Update logging to point to the renamed file
    setup_workflow_logging(final_log_file)

    # Redirect stdout/stderr to the final log file
    log_fd = os.open(str(final_log_file), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.dup2(log_fd, sys.stdout.fileno())
    os.dup2(log_fd, sys.stderr.fileno())
    os.close(log_fd)

    # Write workflow ID to a file so parent process can retrieve it
    # Use environment variable if provided
    id_file = os.environ.get("KURT_WORKFLOW_ID_FILE")
    if id_file:
        with open(id_file, "w") as f:
            f.write(handle.workflow_id)

    # Wait for workflow to complete by polling its status
    # This keeps the process alive AND the ThreadPoolExecutor running
    max_wait_time = 600  # 10 minutes max
    start_time = time.time()
    poll_interval = 0.5

    while (time.time() - start_time) < max_wait_time:
        try:
            # Get workflow status from handle
            status = handle.get_status()
            if status.status in ["SUCCESS", "ERROR", "RETRIES_EXCEEDED", "CANCELLED"]:
                # Workflow completed
                break
        except Exception:
            # If we can't get status, continue waiting
            pass

        time.sleep(poll_interval)

    # Exit cleanly
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python -m kurt.workflows._worker <workflow_name> <workflow_args_json> [priority]",
            file=sys.stderr,
        )
        sys.exit(1)

    workflow_name = sys.argv[1]
    workflow_args_json = sys.argv[2]
    priority = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    run_workflow_worker(workflow_name, workflow_args_json, priority)

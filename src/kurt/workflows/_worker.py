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
    from dbos import SetEnqueueOptions

    from kurt.workflows import get_dbos, init_dbos

    init_dbos()
    get_dbos()

    # Import workflow modules to register them
    from kurt.workflows import map as _map  # noqa
    from kurt.workflows import fetch as _fetch  # noqa
    from kurt.workflows import index as _index  # noqa

    # Get the workflow function
    workflow_func = None
    queue = None
    if workflow_name == "map_url_workflow":
        from kurt.workflows.map import get_map_queue, map_url_workflow

        workflow_func = map_url_workflow
        queue = get_map_queue()
    elif workflow_name == "fetch_batch_workflow":
        from kurt.workflows.fetch import fetch_batch_workflow, fetch_queue

        workflow_func = fetch_batch_workflow
        queue = fetch_queue
    elif workflow_name == "index_documents_workflow":
        from kurt.workflows.index import index_documents_workflow, index_queue

        workflow_func = index_documents_workflow
        queue = index_queue
    else:
        sys.exit(1)  # Unknown workflow

    # Parse arguments
    workflow_args = json.loads(workflow_args_json)

    # Temporarily redirect to /dev/null until we know the workflow ID
    # This prevents DBOS initialization logs from going to the wrong place
    devnull = os.open(os.devnull, os.O_RDWR)
    os.dup2(devnull, sys.stdout.fileno())
    os.dup2(devnull, sys.stderr.fileno())
    os.close(devnull)

    # Enqueue the workflow
    with SetEnqueueOptions(priority=priority):
        handle = queue.enqueue(workflow_func, **workflow_args)

    # Now we know the workflow ID, set up proper logging
    from pathlib import Path

    log_dir = Path(".kurt/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    final_log_file = log_dir / f"workflow-{handle.workflow_id}.log"

    # Write workflow ID to a file so parent process can retrieve it
    # Use environment variable if provided
    id_file = os.environ.get("KURT_WORKFLOW_ID_FILE")
    if id_file:
        with open(id_file, "w") as f:
            f.write(handle.workflow_id)

    # Redirect stdout/stderr to the workflow-specific log file
    log_fd = os.open(str(final_log_file), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.dup2(log_fd, sys.stdout.fileno())
    os.dup2(log_fd, sys.stderr.fileno())
    os.close(log_fd)

    # Configure Python logging to write to the log file
    setup_workflow_logging(final_log_file)

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

"""
Background workflow worker process.

This module provides a standalone worker that can execute workflows
in a completely independent process, allowing the parent CLI to exit immediately.
"""

import atexit
import json
import logging
import os
import sys
import time

from kurt.workflows.logging_utils import setup_workflow_logging


def flush_all_handlers():
    """Flush all logging handlers and their underlying file descriptors."""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        try:
            handler.flush()
            # Also flush the OS buffer to ensure logs reach disk
            if hasattr(handler, "stream") and hasattr(handler.stream, "fileno"):
                os.fsync(handler.stream.fileno())
        except (AttributeError, OSError, ValueError):
            # Handler doesn't have a stream or file descriptor, or it's closed
            pass


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
    # DEBUG: Write immediate debug info to understand CI environment
    import tempfile
    import traceback
    debug_file = tempfile.gettempdir() + f"/kurt_debug_{os.getpid()}.txt"
    final_log_file = None

    try:
        with open(debug_file, "w") as f:
            f.write(f"Worker started: PID={os.getpid()}\n")
            f.write(f"Workflow: {workflow_name}\n")
            f.write(f"Args: {workflow_args_json}\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"CWD: {os.getcwd()}\n")
            f.flush()
            os.fsync(f.fileno())

        # Initialize DBOS fresh in this process
        from dbos import SetEnqueueOptions

        from kurt.workflows import get_dbos, init_dbos

        init_dbos()
        get_dbos()

        # Import workflow modules to register them
        from kurt.content.map import workflow as _map  # noqa
        from kurt.content.fetch import workflow as _fetch  # noqa
        from kurt.content.indexing import workflow_indexing as _indexing_workflow  # noqa

        # Get the workflow function
        workflow_func = None
        queue = None
        if workflow_name == "map_url_workflow":
            from kurt.content.map.workflow import get_map_queue, map_url_workflow

            workflow_func = map_url_workflow
            queue = get_map_queue()
        elif workflow_name == "fetch_workflow":
            from kurt.content.fetch.workflow import fetch_queue, fetch_workflow

            workflow_func = fetch_workflow
            queue = fetch_queue
        elif workflow_name == "complete_indexing_workflow":
            from kurt.content.indexing.workflow_indexing import complete_indexing_workflow

            workflow_func = complete_indexing_workflow
            queue = None  # No queue needed for direct workflow invocation
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

        # DEBUG: Write to debug file about log file creation
        with open(debug_file, "a") as f:
            f.write(f"Creating temp log: {temp_log_file}\n")
            f.flush()

        # Configure Python logging early - before workflow starts
        setup_workflow_logging(temp_log_file)

        # DEBUG: Test that logging works immediately
        test_logger = logging.getLogger("kurt.test.debug")
        test_logger.info(f"DEBUG: Logger setup complete for PID {os.getpid()}")
        flush_all_handlers()

        # Register exit handler to ensure logs are flushed even on abrupt termination
        atexit.register(flush_all_handlers)

        # Redirect stdout/stderr to the temp log file
        log_fd = os.open(str(temp_log_file), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        os.dup2(log_fd, sys.stdout.fileno())
        os.dup2(log_fd, sys.stderr.fileno())
        os.close(log_fd)

        # DEBUG: Write to both stdout and logger after redirect
        print(f"DEBUG: Stdout redirected for PID {os.getpid()}")
        test_logger.info(f"DEBUG: After redirect for PID {os.getpid()}")
        flush_all_handlers()

        with open(debug_file, "a") as f:
            f.write(f"Log file setup complete, size: {temp_log_file.stat().st_size if temp_log_file.exists() else 'N/A'}\n")
            f.flush()

        # Enqueue the workflow (now logging is already configured)
        with SetEnqueueOptions(priority=priority):
            if queue:
                handle = queue.enqueue(workflow_func, **workflow_args)
            else:
                # For workflows without a queue, call directly
                from dbos import DBOS

                handle = DBOS.start_workflow(workflow_func, **workflow_args)

        # Now we know the workflow ID, rename the log file
        # Note: We DON'T recreate the FileHandler after renaming because:
        # 1. The OS file descriptor remains valid after rename (points to same inode)
        # 2. Creating a new handler would create a NEW file, leaving logs in the renamed temp file
        # 3. The logging handler and stdout/stderr are already correctly configured
        final_log_file = log_dir / f"workflow-{handle.workflow_id}.log"

        # DEBUG: Log before rename
        with open(debug_file, "a") as f:
            f.write(f"Before rename - temp file size: {temp_log_file.stat().st_size if temp_log_file.exists() else 'N/A'}\n")
            f.write(f"Renaming {temp_log_file} -> {final_log_file}\n")
            f.flush()

        temp_log_file.rename(final_log_file)

        # DEBUG: Log after rename
        test_logger.info(f"DEBUG: After rename - workflow ID: {handle.workflow_id}")
        print(f"DEBUG: After rename print - workflow ID: {handle.workflow_id}")
        flush_all_handlers()

        with open(debug_file, "a") as f:
            f.write(f"After rename - final file size: {final_log_file.stat().st_size if final_log_file.exists() else 'N/A'}\n")
            f.flush()

        # Write workflow ID to a file so parent process can retrieve it
        # Use environment variable if provided
        id_file = os.environ.get("KURT_WORKFLOW_ID_FILE")
        if id_file:
            with open(id_file, "w") as f:
                f.write(handle.workflow_id)

        # DEBUG: Log before entering polling loop
        with open(debug_file, "a") as f:
            f.write(f"Entering polling loop for workflow {handle.workflow_id}\n")
            f.flush()
            os.fsync(f.fileno())

        # Wait for workflow to complete by polling its status
        # This keeps the process alive AND the ThreadPoolExecutor running
        max_wait_time = 600  # 10 minutes max
        start_time = time.time()
        poll_interval = 0.5
        last_flush_time = start_time
        poll_count = 0

        while (time.time() - start_time) < max_wait_time:
            poll_count += 1

            # DEBUG: Log every 10 polls (5 seconds)
            if poll_count % 10 == 1:
                with open(debug_file, "a") as f:
                    f.write(f"Poll #{poll_count} at {time.time() - start_time:.1f}s\n")
                    f.flush()
                    os.fsync(f.fileno())

            try:
                # Get workflow status from handle
                status = handle.get_status()
                if poll_count == 1:
                    # DEBUG: Log first status
                    with open(debug_file, "a") as f:
                        f.write(f"First status check: {status.status if status else 'None'}\n")
                        f.flush()

                if status.status in ["SUCCESS", "ERROR", "RETRIES_EXCEEDED", "CANCELLED"]:
                    # Workflow completed
                    with open(debug_file, "a") as f:
                        f.write(f"Workflow completed with status: {status.status}\n")
                        f.flush()
                    break
            except Exception as e:
                # If we can't get status, continue waiting
                if poll_count == 1:
                    with open(debug_file, "a") as f:
                        f.write(f"Error getting status: {e}\n")
                        f.flush()

            time.sleep(poll_interval)

            # Flush logs every 5 seconds to ensure they're written even for long-running workflows
            current_time = time.time()
            if current_time - last_flush_time >= 5.0:
                flush_all_handlers()
                last_flush_time = current_time

        # Flush all logging handlers and file descriptors before exit
        flush_all_handlers()

        # DEBUG: Final debug info
        with open(debug_file, "a") as f:
            f.write(f"Worker exiting - final log size: {final_log_file.stat().st_size if final_log_file.exists() else 'N/A'}\n")
            f.write(f"Worker complete at {time.time()}\n")
            f.flush()
            os.fsync(f.fileno())

    except Exception as e:
        # Write exception to debug file
        with open(debug_file, "a") as f:
            f.write(f"\n\nEXCEPTION in worker PID {os.getpid()}:\n")
            f.write(f"Error: {str(e)}\n")
            f.write(f"Traceback:\n{traceback.format_exc()}\n")
            f.write(f"Final log file: {final_log_file}\n")
            f.flush()
            os.fsync(f.fileno())

        # Also try to log to the workflow log if it exists
        if final_log_file:
            try:
                error_logger = logging.getLogger("kurt.worker.error")
                error_logger.error(f"Worker crashed: {e}", exc_info=True)
                flush_all_handlers()
            except Exception:
                pass

        # Re-raise to maintain original exit behavior
        raise

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

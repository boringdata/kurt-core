"""
Background workflow worker process.

This module provides a standalone worker that can execute workflows
in a completely independent process, allowing the parent CLI to exit immediately.
"""

import atexit
import json
import logging
import os
import signal
import sys
import time

from kurt.workflows.logging_utils import setup_workflow_logging


def ignore_signal(signum, frame):
    """Ignore signals that would terminate the process."""
    pass


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
    final_log_file = None
    dbos_instance = None

    try:
        # Set up signal handlers to prevent termination from parent
        # But still allow direct SIGINT/SIGKILL for debugging
        signal.signal(signal.SIGHUP, signal.SIG_IGN)  # Ignore hangup signal
        signal.signal(signal.SIGTERM, signal.SIG_IGN)  # Ignore termination from parent

        # Initialize DBOS fresh in this process
        from dbos import DBOS, SetEnqueueOptions

        from kurt.workflows import get_dbos, init_dbos

        # Initialize DBOS and ensure it's ready
        init_dbos()
        dbos_instance = get_dbos()  # Store for cleanup

        # Critical: Prime the DBOS thread pool to ensure executor threads are running
        # This forces thread creation which may not happen automatically in subprocess
        import uuid

        prime_logger = logging.getLogger("kurt.worker.prime")
        prime_logger.info("Priming DBOS thread pool...")

        # Submit a dummy workflow to force thread pool initialization
        def dummy_workflow():
            """Dummy workflow to prime thread pool."""
            return {"status": "primed"}

        try:
            # Use unique ID to avoid deduplication
            dummy_id = f"prime-{os.getpid()}-{uuid.uuid4().hex[:8]}"
            dummy_handle = DBOS.start_workflow(dummy_workflow, workflow_id=dummy_id)

            # Wait for dummy to complete (proves threads are working)
            max_prime_wait = 3  # Reduced to 3 seconds for faster CI startup
            prime_start = time.time()
            while (time.time() - prime_start) < max_prime_wait:
                status = dummy_handle.get_status()
                if status and status.status in ["SUCCESS", "ERROR"]:
                    prime_logger.info(f"Thread pool primed successfully (status={status.status})")
                    break
                time.sleep(0.1)  # Check more frequently
            else:
                prime_logger.warning("Thread pool priming timed out but continuing anyway")
        except Exception as e:
            prime_logger.warning(f"Thread pool priming failed but continuing: {e}")

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

        # Configure Python logging early - before workflow starts
        setup_workflow_logging(temp_log_file)

        # Register exit handler to ensure logs are flushed even on abrupt termination
        atexit.register(flush_all_handlers)

        # Redirect stdout/stderr to the temp log file
        log_fd = os.open(str(temp_log_file), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        os.dup2(log_fd, sys.stdout.fileno())
        os.dup2(log_fd, sys.stderr.fileno())
        os.close(log_fd)

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

        temp_log_file.rename(final_log_file)

        # Write workflow ID to a file so parent process can retrieve it
        # Use environment variable if provided
        id_file = os.environ.get("KURT_WORKFLOW_ID_FILE")
        if id_file:
            with open(id_file, "w") as f:
                f.write(handle.workflow_id)

        # Give the queue processing thread time to dequeue the workflow
        # DBOS polls the queue periodically (about every 1 second)
        time.sleep(3)  # Wait for queue thread to dequeue in CI environment

        # Force multiple status checks to trigger DBOS executor threads
        # This helps ensure the workflow transitions from PENDING to RUNNING
        status_logger = logging.getLogger("kurt.worker.status")
        for i in range(10):  # More attempts in CI environment
            try:
                initial_status = handle.get_status()
                if initial_status:
                    status_logger.info(
                        f"Initial workflow status check {i+1}: {initial_status.status}"
                    )
                    # If the workflow has started executing, we're good
                    if initial_status.status not in ["PENDING", "ENQUEUED"]:
                        break
            except Exception:
                pass
            time.sleep(1)

        # Wait for workflow to complete by polling its status
        # This keeps the process alive AND the ThreadPoolExecutor running
        max_wait_time = 600  # 10 minutes max
        start_time = time.time()
        poll_interval = 0.5
        last_flush_time = start_time
        poll_count = 0

        # Log to the workflow log file that we're monitoring
        monitor_logger = logging.getLogger("kurt.worker.monitor")
        monitor_logger.info(f"Worker process monitoring workflow {handle.workflow_id}")

        while (time.time() - start_time) < max_wait_time:
            poll_count += 1

            # Log to workflow log file every 5 seconds
            if poll_count % 10 == 1:
                monitor_logger.info(
                    f"Still monitoring workflow (poll #{poll_count}, {time.time() - start_time:.1f}s elapsed)"
                )

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

            # Flush logs every 5 seconds to ensure they're written even for long-running workflows
            current_time = time.time()
            if current_time - last_flush_time >= 5.0:
                flush_all_handlers()
                last_flush_time = current_time

        # Flush all logging handlers and file descriptors before exit
        flush_all_handlers()

    except Exception as e:
        # Log to the workflow log if it exists
        if final_log_file:
            try:
                error_logger = logging.getLogger("kurt.worker.error")
                error_logger.error(f"Worker crashed: {e}", exc_info=True)
                flush_all_handlers()
            except Exception:
                pass

        # Exit with error code
        sys.exit(1)

    finally:
        # Clean shutdown of DBOS
        if dbos_instance is not None:
            try:
                shutdown_logger = logging.getLogger("kurt.worker.shutdown")
                shutdown_logger.info("Shutting down DBOS...")
                # Give workflows 5 seconds to complete gracefully
                DBOS.destroy(workflow_completion_timeout_sec=5)
                shutdown_logger.info("DBOS shutdown complete")
            except Exception as e:
                # Log but don't fail - we're exiting anyway
                try:
                    shutdown_logger = logging.getLogger("kurt.worker.shutdown")
                    shutdown_logger.warning(f"Error during DBOS shutdown: {e}")
                except Exception:
                    pass

        # Final flush of all logs
        try:
            flush_all_handlers()
        except Exception:
            pass

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

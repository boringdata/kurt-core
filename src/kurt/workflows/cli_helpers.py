"""
CLI Helper Functions for Background Workflows

This module provides helper functions to integrate DBOS workflows
with existing CLI commands without major refactoring.
"""

import contextlib
import gc
import logging
import sys
import threading
import time
from typing import Any, Callable, Dict, Optional

from rich.console import Console

from kurt.core import run_pipeline_workflow
from kurt.utils.filtering import DocumentFilters
from kurt.workflows import get_dbos

console = Console()
logger = logging.getLogger(__name__)


@contextlib.contextmanager
def dbos_cleanup_context():
    """
    Context manager for proper DBOS cleanup after pipeline execution.

    This handles cleanup of DBOS resources and thread pools to prevent
    hanging after command completion.

    Usage:
        with dbos_cleanup_context():
            result = run_pipeline_simple(...)
            # process result
    """
    try:
        yield
    finally:
        # Force garbage collection
        gc.collect()

        # Ensure DBOS is cleaned up if it was initialized
        try:
            dbos = get_dbos()
            # Force immediate DBOS cleanup
            dbos.destroy(workflow_completion_timeout_sec=0)
        except Exception:
            pass  # Ignore if DBOS wasn't initialized

        # Workaround for DBOS and other executor bugs
        # Force any non-daemon ThreadPoolExecutor threads to become daemons
        time.sleep(0.1)  # Brief pause for normal cleanup
        for thread in threading.enumerate():
            if thread.name.startswith("ThreadPoolExecutor-") and not thread.daemon:
                thread.daemon = True  # Make it daemon so it won't block exit

        # Flush output buffers
        sys.stdout.flush()
        sys.stderr.flush()


def run_with_background_support(
    workflow_func: Callable,
    workflow_args: dict[str, Any],
    background: bool = False,
    workflow_id: str | None = None,
    priority: int = 10,
    log_file: str | None = None,
) -> Any:
    """
    Execute a workflow with optional background mode.

    This helper function provides a standard pattern for CLI commands
    to support --background and --workflow-id flags.

    Args:
        workflow_func: The DBOS workflow function to execute
        workflow_args: Arguments to pass to the workflow
        background: If True, run in background and return workflow ID
        workflow_id: If provided, resume/check this workflow instead
        priority: Priority for background execution (1=highest, default=10)

    Returns:
        - If background=True: workflow ID (str)
        - If workflow_id provided: workflow result (dict)
        - Otherwise: workflow result (dict)

    Example:
        from kurt.core import run_pipeline_workflow
        from kurt.workflows.cli_helpers import run_with_background_support

        result = run_with_background_support(
            workflow_func=run_pipeline_workflow,
            workflow_args={"target": "landing.fetch", "filters": filters},
            background=background_flag,
            workflow_id=workflow_id_arg,
            priority=priority_arg
        )
    """
    dbos = get_dbos()  # noqa: F841

    # Case 1: Resume/check existing workflow
    if workflow_id:
        console.print(f"[blue]Checking workflow {workflow_id}...[/blue]")

        try:
            # Query workflow status from database
            from kurt.db.database import get_session

            with get_session() as session:
                sql = """
                    SELECT workflow_uuid, workflow_class_name, status, output, error
                    FROM dbos_workflow_status
                    WHERE workflow_uuid LIKE :workflow_id || '%'
                    LIMIT 1
                """
                result = session.execute(sql, {"workflow_id": workflow_id})
                wf = result.fetchone()

            if not wf:
                console.print(f"[red]Workflow {workflow_id} not found[/red]")
                return None

            wf_id, wf_name, status, output, error = wf

            console.print(f"[bold]Workflow:[/bold] {wf_name}")
            console.print(f"[bold]Status:[/bold] {status}")

            if status == "SUCCESS" and output:
                import base64
                import json
                import pickle

                try:
                    # DBOS stores results as pickled objects (base64-encoded)
                    decoded = base64.b64decode(output)
                    result_data = pickle.loads(decoded)
                except Exception:  # noqa: S110
                    # Fallback: try JSON parsing
                    try:
                        result_data = json.loads(output)
                    except Exception:  # noqa: S110
                        result_data = output

                console.print("\n[green]Result:[/green]")
                console.print(json.dumps(result_data, indent=2, default=str))
                return result_data
            elif error:
                console.print(f"\n[red]Error:[/red] {error}")
                return None
            else:
                console.print(f"\n[yellow]Workflow is {status}[/yellow]")
                return None

        except Exception as e:
            console.print(f"[red]Error checking workflow: {e}[/red]")
            return None

    # Case 2: Start new workflow in background
    if background:
        console.print("[dim]Enqueueing workflow...[/dim]")

        # Spawn a completely independent background worker process
        # This allows the CLI to exit immediately while the workflow executes
        import json
        import subprocess
        import sys
        import tempfile
        import time
        from pathlib import Path

        # Serialize workflow arguments to JSON
        workflow_args_json = json.dumps(workflow_args, default=str)

        # Determine workflow name
        workflow_name = workflow_func.__name__

        # Create temporary file for workflow ID communication
        id_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".workflow_id")
        id_file_path = id_file.name
        id_file.close()

        # Spawn worker process
        cmd = [
            sys.executable,
            "-m",
            "kurt.workflows._worker",
            workflow_name,
            workflow_args_json,
            str(priority),
        ]

        # Start completely detached process
        import os

        env = os.environ.copy()
        env["KURT_WORKFLOW_ID_FILE"] = id_file_path

        subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )

        # Wait briefly for the worker to write the workflow ID (max 5 seconds)
        workflow_id = None
        for _ in range(50):  # 50 * 0.1s = 5s max
            if Path(id_file_path).exists() and Path(id_file_path).stat().st_size > 0:
                with open(id_file_path, "r") as f:
                    workflow_id = f.read().strip()
                if workflow_id:
                    break
            time.sleep(0.1)

        # Clean up temp file
        try:
            os.unlink(id_file_path)
        except Exception:  # noqa: S110
            pass

        if workflow_id:
            console.print(f"\n[green]✓ Workflow started in background: {workflow_id}[/green]")
            console.print(f"[dim]Check status: kurt workflows status {workflow_id}[/dim]")
            console.print("[dim]List all: kurt workflows list[/dim]")
            console.print(f"[dim]Follow progress: kurt workflows follow {workflow_id} --wait[/dim]")
            console.print(f"[dim]Logs: .kurt/logs/workflow-{workflow_id}.log[/dim]")
            return workflow_id
        else:
            console.print("\n[green]✓ Workflow starting in background...[/green]")
            console.print("[dim]Check status: kurt workflows list[/dim]")
            console.print("[dim]Follow progress: kurt workflows follow <workflow-id> --wait[/dim]")
            console.print("[dim]Logs will be in: .kurt/logs/workflow-<id>.log[/dim]")
            return None

    # Case 3: Execute synchronously (blocking) WITHOUT workflow system
    # For synchronous execution, we skip the workflow decorator entirely
    # and call the underlying function directly to preserve progress UI
    console.print("[dim]Running synchronously (use --background for non-blocking)...[/dim]")

    # NOTE: This is a bit of a hack - we're bypassing the workflow system
    # for synchronous execution to preserve progress bars and interactive UI.
    # For true durability in sync mode, we'd need to find workflow_func's underlying function
    return None  # Signal to caller that they should handle sync execution themselves


def run_pipeline_simple(
    target: str,
    filters: Optional[DocumentFilters] = None,
    model_configs: Optional[Dict[str, Any]] = None,
    background: bool = False,
    priority: int = 10,
    incremental_mode: str = "full",
    reprocess_unchanged: bool = False,
    verbose: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Simplified helper to run a pipeline workflow.

    Handles DBOS initialization, background mode, and returns the result.
    Display is automatically handled by the framework.

    Args:
        target: Pipeline target (e.g., "landing.discovery", "staging")
        filters: Document filters (defaults to empty filters)
        model_configs: Optional dict mapping model names to config instances
        background: If True, run in background and return workflow ID
        priority: Priority for background execution
        incremental_mode: Processing mode ("full" or "delta")
        reprocess_unchanged: If True, reprocess unchanged documents
        verbose: If True, display detailed tables during step execution
        metadata: Optional dict of metadata to pass to pipeline context (e.g., {"query": "..."})

    Returns:
        Workflow result dict (or workflow ID if background=True)

    Example:
        from kurt.models.landing.discovery import DiscoveryConfig
        from kurt.workflows.cli_helpers import run_pipeline_simple

        config = DiscoveryConfig(source_url="https://example.com")
        result = run_pipeline_simple(
            target="landing.discovery",
            model_configs={"landing.discovery": config},
        )
    """
    get_dbos()  # Initialize DBOS

    if filters is None:
        filters = DocumentFilters()

    # Build metadata dict with verbose flag and any custom metadata
    ctx_metadata = {"verbose": verbose}
    if metadata:
        ctx_metadata.update(metadata)

    if background:
        console.print("[dim]Enqueueing workflow...[/dim]\n")
        return run_with_background_support(
            workflow_func=run_pipeline_workflow,
            workflow_args={
                "target": target,
                "filters": filters,
                "incremental_mode": incremental_mode,
                "reprocess_unchanged": reprocess_unchanged,
                "model_configs": model_configs,
                "metadata": ctx_metadata,
            },
            background=True,
            workflow_id=None,
            priority=priority,
        )

    # Foreground mode
    from dbos import DBOS

    handle = DBOS.start_workflow(
        run_pipeline_workflow,
        target=target,
        filters=filters,
        incremental_mode=incremental_mode,
        reprocess_unchanged=reprocess_unchanged,
        model_configs=model_configs,
        metadata=ctx_metadata,
    )

    return handle.get_result()


__all__ = ["run_with_background_support", "run_pipeline_simple", "dbos_cleanup_context"]

"""
Tool runner with workflow observability.

Runs a single tool with workflow_runs/step_logs/step_events tracking.
Supports a subprocess entrypoint for background execution.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from kurt.db.dolt import DoltDB, check_schema_exists, init_observability_schema
from kurt.observability import WorkflowLifecycle
from kurt.observability.tracking import track_event
from kurt.tools.core.base import SubstepEvent
from kurt.tools.core.context import load_tool_context
from kurt.tools.core.registry import execute_tool, get_tool

# Import tools module to ensure all tools are registered via @register_tool decorators
import kurt.tools  # noqa: F401


def _get_project_root(project_root: str | None = None) -> Path:
    if project_root:
        return Path(project_root).resolve()
    return Path.cwd().resolve()


def _get_dolt_db(project_root: Path | None = None) -> DoltDB:
    """Get DoltDB client, initializing observability schema if needed.

    Uses get_database_client() to respect DATABASE_URL environment variable.

    Args:
        project_root: Optional project root (unused, kept for backwards compatibility).
    """
    from kurt.db import get_database_client

    db = get_database_client()

    # For local/embedded mode, check if initialization is needed
    if db.mode == "embedded":
        if not db.exists():
            db.init()
            init_observability_schema(db)
        else:
            schema_status = check_schema_exists(db)
            if not all(schema_status.values()):
                init_observability_schema(db)
    else:
        # Server mode - check schema exists
        schema_status = check_schema_exists(db)
        if not all(schema_status.values()):
            init_observability_schema(db)

    return db


def _summarize_inputs(params: dict[str, Any]) -> dict[str, Any]:
    summary = dict(params)
    for key in ("inputs", "input_data"):
        value = summary.get(key)
        if isinstance(value, list):
            summary[key] = {"count": len(value)}
    return summary


def _infer_input_count(params: dict[str, Any]) -> int | None:
    for key in ("inputs", "input_data"):
        value = params.get(key)
        if isinstance(value, list):
            return len(value)
    return None


def _build_progress_handler(
    *,
    db: DoltDB,
    run_id: str,
    step_id: str,
) -> callable[[SubstepEvent], None]:
    def on_progress(event: SubstepEvent) -> None:
        status = event.status
        if status not in ("running", "progress", "completed", "failed"):
            status = "progress"

        track_event(
            run_id=run_id,
            step_id=step_id,
            substep=event.substep,
            status=status,
            current=event.current,
            total=event.total,
            message=event.message,
            metadata=event.metadata,
            db=db,
        )

    return on_progress


def run_tool_with_tracking(
    tool_name: str,
    params: dict[str, Any],
    *,
    run_id: str | None = None,
    project_root: str | None = None,
    metadata: dict[str, Any] | None = None,
    cli_command: str | None = None,
    priority: int | None = None,
) -> tuple[str, dict[str, Any]]:
    project_dir = _get_project_root(project_root)
    db = _get_dolt_db(project_dir)
    lifecycle = WorkflowLifecycle(db)

    run_metadata = dict(metadata or {})
    if priority is not None:
        run_metadata["priority"] = priority
    if cli_command:
        run_metadata["cli_command"] = cli_command

    if run_id is None:
        run_id = lifecycle.create_run(
            workflow=tool_name,
            inputs=_summarize_inputs(params),
            metadata=run_metadata,
            status="running",
        )
    else:
        lifecycle.update_status(run_id, "running", metadata=run_metadata)

    tool_class = get_tool(tool_name)
    step_id = tool_name
    lifecycle.create_step_log(
        run_id=run_id,
        step_id=step_id,
        tool=tool_class.__name__,
        input_count=_infer_input_count(params),
        metadata={"tool": tool_name},
    )

    context = load_tool_context(project_dir, init_db=False, init_http=True, init_llm=True)
    context.settings["project_root"] = str(project_dir)

    on_progress = _build_progress_handler(db=db, run_id=run_id, step_id=step_id)

    try:
        result = asyncio.run(execute_tool(tool_name, params, context=context, on_progress=on_progress))
        step_status = "completed" if result.success else "failed"
        lifecycle.update_step_log(
            run_id,
            step_id,
            status=step_status,
            output_count=len(result.data),
            error_count=len(result.errors),
            errors=[e.to_dict() for e in result.errors],
        )
        if result.success:
            lifecycle.update_status(run_id, "completed")
        else:
            lifecycle.update_status(run_id, "failed", error="tool_failed")
        return run_id, result.to_dict()
    except Exception as exc:
        lifecycle.update_step_log(
            run_id,
            step_id,
            status="failed",
            error_count=1,
            errors=[{"row_idx": None, "error_type": "exception", "message": str(exc)}],
        )
        lifecycle.update_status(run_id, "failed", error=str(exc))
        raise


def create_pending_run(
    tool_name: str,
    params: dict[str, Any],
    *,
    project_root: str | None = None,
    metadata: dict[str, Any] | None = None,
    cli_command: str | None = None,
    priority: int | None = None,
) -> str:
    project_dir = _get_project_root(project_root)
    db = _get_dolt_db(project_dir)
    lifecycle = WorkflowLifecycle(db)

    run_metadata = dict(metadata or {})
    if priority is not None:
        run_metadata["priority"] = priority
    if cli_command:
        run_metadata["cli_command"] = cli_command

    return lifecycle.create_run(
        workflow=tool_name,
        inputs=_summarize_inputs(params),
        metadata=run_metadata,
        status="pending",
    )


def run_tool_from_file(payload_path: str) -> None:
    payload = json.loads(Path(payload_path).read_text())
    run_id = payload.get("run_id")
    tool_name = payload["tool"]
    params = payload.get("params", {})
    project_root = payload.get("project_root")
    metadata = payload.get("metadata")
    cli_command = payload.get("cli_command")
    priority = payload.get("priority")

    run_tool_with_tracking(
        tool_name,
        params,
        run_id=run_id,
        project_root=project_root,
        metadata=metadata,
        cli_command=cli_command,
        priority=priority,
    )


def spawn_background_run(
    tool_name: str,
    params: dict[str, Any],
    *,
    run_id: str,
    project_root: str | None = None,
    metadata: dict[str, Any] | None = None,
    cli_command: str | None = None,
    priority: int | None = None,
) -> None:
    payload = {
        "run_id": run_id,
        "tool": tool_name,
        "params": params,
        "project_root": project_root,
        "metadata": metadata,
        "cli_command": cli_command,
        "priority": priority,
    }

    payload_file = tempfile.NamedTemporaryFile("w", delete=False, suffix=".json")
    with payload_file as handle:
        json.dump(payload, handle)

    cmd = [sys.executable, "-m", "kurt.tools.core.runner", "--payload", payload_file.name]
    subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=_get_project_root(project_root),
        start_new_session=True,
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a tool with observability tracking.")
    parser.add_argument("--payload", required=True, help="Path to JSON payload file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    try:
        run_tool_from_file(args.payload)
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

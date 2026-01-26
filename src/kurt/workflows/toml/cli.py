"""Unified workflow CLI commands for running and managing workflows.

Supports both TOML-based workflows (engine-driven) and MD/TOML agent workflows.

Commands:
    kurt workflow run <workflow> [--input key=value]...  - Run workflow (TOML or MD)
    kurt workflow logs <run_id> [--json]                 - View step logs for workflow run
    kurt workflow logs <run_id> --tail                   - Stream progress events
    kurt workflow cancel <run_id>                        - Cancel running workflow
    kurt workflow status <run_id>                        - Show workflow status
    kurt workflow test <workflow.toml>                   - Test workflow with fixtures
    kurt workflow list                                   - List all workflow definitions
    kurt workflow show <name>                            - Show workflow details
    kurt workflow validate [file]                        - Validate workflow file(s)
    kurt workflow history <name>                         - Show run history for a workflow
    kurt workflow init                                   - Initialize with example workflows
    kurt workflow create                                 - Create a new workflow definition
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command

console = Console()


def _parse_input(input_str: str) -> tuple[str, Any]:
    """Parse a key=value input string.

    Handles type coercion:
    - "true"/"false" -> bool
    - integers -> int
    - floats -> float
    - everything else -> string

    Args:
        input_str: String in "key=value" format.

    Returns:
        Tuple of (key, parsed_value).

    Raises:
        click.BadParameter: If format is invalid.
    """
    if "=" not in input_str:
        raise click.BadParameter(f"Input must be in key=value format: {input_str}")

    key, value = input_str.split("=", 1)
    key = key.strip()
    value = value.strip()

    # Type coercion
    if value.lower() == "true":
        return key, True
    elif value.lower() == "false":
        return key, False
    elif value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return key, int(value)
    else:
        try:
            return key, float(value)
        except ValueError:
            return key, value


def _get_dolt_db():
    """Get or create DoltDB instance."""
    import os

    # DOLT_PATH should point to the repo root (containing .dolt), not .dolt itself
    dolt_path = os.environ.get("DOLT_PATH", ".")
    from kurt.db.dolt import DoltDB

    db = DoltDB(dolt_path)
    if not db.exists():
        console.print("[red]Error: Dolt database not initialized[/red]")
        console.print("[dim]Run 'kurt init' to initialize the project[/dim]")
        raise click.Abort()
    return db


@click.command(name="run")
@click.argument("workflow_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--input",
    "-i",
    "inputs",
    multiple=True,
    help="Input values in key=value format (can specify multiple)",
)
@click.option(
    "--background",
    "-b",
    is_flag=True,
    help="Run in background and return immediately",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Parse and validate workflow without executing",
)
@track_command
def run_cmd(workflow_path: Path, inputs: tuple[str, ...], background: bool, dry_run: bool):
    """Run a workflow from a TOML file.

    Parses the workflow, merges inputs with defaults, and executes.
    Outputs JSON with run_id and status.

    Examples:
        kurt run workflows/pipeline.toml
        kurt run workflows/pipeline.toml --input url=https://example.com
        kurt run workflows/pipeline.toml -i url=https://example.com -i max_pages=100
        kurt run workflows/pipeline.toml --background
    """
    from kurt.workflows.toml import parse_workflow
    from kurt.workflows.toml.executor import execute_workflow

    # Parse inputs
    parsed_inputs: dict[str, Any] = {}
    for input_str in inputs:
        key, value = _parse_input(input_str)
        parsed_inputs[key] = value

    # Parse workflow
    try:
        workflow_def = parse_workflow(workflow_path)
    except FileNotFoundError:
        console.print(f"[red]Error: Workflow file not found: {workflow_path}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error parsing workflow: {e}[/red]")
        raise click.Abort()

    # Dry run mode
    if dry_run:
        output = _build_dry_run_output(workflow_def, parsed_inputs, workflow_path)
        print(json.dumps(output, indent=2, default=str))
        return

    # Merge inputs with defaults
    merged_inputs: dict[str, Any] = {}
    for name, input_def in workflow_def.inputs.items():
        if name in parsed_inputs:
            merged_inputs[name] = parsed_inputs[name]
        elif input_def.default is not None:
            merged_inputs[name] = input_def.default
        elif input_def.required:
            console.print(f"[red]Error: Required input '{name}' not provided[/red]")
            console.print(f"[dim]Add --input {name}=<value>[/dim]")
            raise click.Abort()

    # Include any extra inputs
    for name, value in parsed_inputs.items():
        if name not in merged_inputs:
            merged_inputs[name] = value

    # Get DoltDB for tracking and tool context
    db = _get_dolt_db()

    # Execute workflow with database in context
    from kurt.tools.core import ToolContext

    context = ToolContext(db=db)

    if background:
        # Background execution: start and return immediately
        import uuid

        run_id = str(uuid.uuid4())

        # Create run record
        from kurt.observability import WorkflowLifecycle

        lifecycle = WorkflowLifecycle(db)
        lifecycle.create_run(
            workflow=workflow_def.workflow.name,
            inputs=merged_inputs,
            run_id=run_id,
            status="pending",
        )

        output = {
            "run_id": run_id,
            "status": "pending",
            "workflow": workflow_def.workflow.name,
            "started_at": datetime.utcnow().isoformat(),
            "background": True,
        }
        print(json.dumps(output, indent=2))

        # Note: Actual background execution would require a separate process
        # For now, we just create the record. Full implementation would use
        # subprocess or a task queue.
        console.print(
            "\n[yellow]Note: Background execution creates run record only.[/yellow]"
        )
        console.print("[dim]Use 'kurt logs {run_id}' to check progress.[/dim]")
        return

    # Foreground execution
    # Look for tools.py in the same directory as the workflow file
    tools_path = workflow_path.parent / "tools.py"
    result = asyncio.run(
        execute_workflow(
            workflow=workflow_def,
            inputs=merged_inputs,
            context=context,
            tools_path=tools_path if tools_path.exists() else None,
        )
    )

    # Output result
    output = {
        "run_id": result.run_id,
        "status": result.status,
        "workflow": workflow_def.workflow.name,
        "started_at": result.started_at,
        "completed_at": result.completed_at,
        "steps": [
            {
                "step_id": step_id,
                "status": step_result.status,
                "output_count": len(step_result.output_data),
            }
            for step_id, step_result in result.step_results.items()
        ],
        "error": result.error,
        "exit_code": result.exit_code,
    }
    print(json.dumps(output, indent=2, default=str))

    # Exit with workflow exit code
    sys.exit(result.exit_code)


@click.command(name="status")
@click.argument("run_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--follow", "-f", is_flag=True, help="Stream progress events until completion")
@track_command
def status_cmd(run_id: str, output_json: bool, follow: bool):
    """Show workflow status.

    Without --follow, shows current status snapshot.
    With --follow, streams progress events until the workflow completes.

    Examples:
        kurt status abc-123-def
        kurt status abc-123-def --json
        kurt status abc-123-def --follow
    """
    db = _get_dolt_db()

    if follow:
        _follow_workflow(db, run_id)
        return

    # Get status snapshot
    from kurt.observability import WorkflowLifecycle

    lifecycle = WorkflowLifecycle(db)
    run = lifecycle.get_run(run_id)

    if run is None:
        if output_json:
            print(json.dumps({"run_id": run_id, "status": "not_found", "error": "Workflow not found"}))
        else:
            console.print(f"[red]Workflow not found: {run_id}[/red]")
        return

    # Get step logs
    step_logs = lifecycle.get_step_logs(run_id)

    # Calculate completed steps
    completed_steps = sum(1 for s in step_logs if s.get("status") in ("completed", "failed", "canceled"))
    total_steps = len(step_logs)

    if output_json:
        output = {
            "run_id": run_id,
            "status": run.get("status"),
            "workflow": run.get("workflow"),
            "started_at": str(run.get("started_at")) if run.get("started_at") else None,
            "completed_at": str(run.get("completed_at")) if run.get("completed_at") else None,
            "steps": [
                {
                    "step_id": s.get("step_id"),
                    "status": s.get("status"),
                    "output_count": s.get("output_count"),
                }
                for s in step_logs
            ],
            "error": run.get("error"),
        }
        print(json.dumps(output, indent=2))
        return

    # Text output
    console.print(f"\n[bold]Run:[/bold] {run_id}")
    console.print(f"[bold]Workflow:[/bold] {run.get('workflow')}")

    status = run.get("status", "unknown")
    if status == "completed":
        console.print(f"[bold]Status:[/bold] [green]{status}[/green]")
    elif status in ("failed", "canceled"):
        console.print(f"[bold]Status:[/bold] [red]{status}[/red]")
    elif status in ("running", "canceling"):
        console.print(f"[bold]Status:[/bold] [yellow]{status}[/yellow]")
    else:
        console.print(f"[bold]Status:[/bold] {status}")

    if run.get("started_at"):
        console.print(f"[bold]Started:[/bold] {run.get('started_at')}")

    if run.get("completed_at"):
        console.print(f"[bold]Completed:[/bold] {run.get('completed_at')}")

    console.print(f"[bold]Steps:[/bold] {completed_steps}/{total_steps} completed")

    if run.get("error"):
        console.print(f"\n[bold red]Error:[/bold red] {run.get('error')}")

    # Show steps table
    if step_logs:
        console.print()
        table = Table(box=None, show_edge=False)
        table.add_column("Step", style="cyan")
        table.add_column("Status")
        table.add_column("Output", justify="right")

        for step in step_logs:
            step_status = step.get("status", "unknown")
            if step_status == "completed":
                status_display = f"[green]{step_status}[/green]"
            elif step_status in ("failed", "canceled"):
                status_display = f"[red]{step_status}[/red]"
            elif step_status == "running":
                status_display = f"[yellow]{step_status}[/yellow]"
            else:
                status_display = step_status

            output_count = step.get("output_count")
            output_str = str(output_count) if output_count is not None else "-"

            table.add_row(step.get("step_id", "-"), status_display, output_str)

        console.print(table)
    console.print()


def _follow_workflow(db, run_id: str):
    """Stream workflow progress events until completion.

    Uses the StatusStreamer from kurt.observability.streaming.
    """
    from kurt.observability import format_event, stream_events

    console.print(f"[bold]Following workflow:[/bold] {run_id}\n")

    try:
        for event in stream_events(db, run_id):
            formatted = format_event(event)
            console.print(formatted)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        return

    # Get final status
    from kurt.observability import WorkflowLifecycle

    lifecycle = WorkflowLifecycle(db)
    run = lifecycle.get_run(run_id)

    if run:
        status = run.get("status")
        if status == "completed":
            console.print("\n[green]Workflow completed successfully[/green]")
        elif status == "failed":
            error = run.get("error", "Unknown error")
            console.print(f"\n[red]Workflow failed: {error}[/red]")
        elif status == "canceled":
            console.print("\n[yellow]Workflow canceled[/yellow]")


@click.command(name="logs")
@click.argument("run_id")
@click.option("--step", "step_filter", default=None, help="Filter by step name")
@click.option("--substep", "substep_filter", default=None, help="Filter by substep name")
@click.option("--status", "status_filter", default=None, help="Filter by status (running|progress|completed|failed)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON lines")
@click.option("--tail", "-f", is_flag=True, help="Stream new events as they arrive (like tail -f)")
@click.option("--limit", default=100, help="Maximum number of log entries to show")
@track_command
def logs_cmd(
    run_id: str,
    step_filter: str | None,
    substep_filter: str | None,
    status_filter: str | None,
    output_json: bool,
    tail: bool,
    limit: int,
):
    """View step logs for a workflow run.

    Shows step_logs entries with status, timing, and counts, plus recent
    step_events for each step.

    Examples:
        kurt logs abc-123-def
        kurt logs abc-123-def --step=fetch
        kurt logs abc-123-def --status=failed
        kurt logs abc-123-def --json
        kurt logs abc-123-def --tail
    """
    db = _get_dolt_db()

    # Check if run exists
    from kurt.observability import WorkflowLifecycle

    lifecycle = WorkflowLifecycle(db)
    run = lifecycle.get_run(run_id)

    if run is None:
        if output_json:
            print(json.dumps({"run_id": run_id, "error": "Workflow run not found"}))
        else:
            console.print(f"[red]Workflow run not found: {run_id}[/red]")
        sys.exit(1)

    if tail:
        _tail_logs(db, run_id, step_filter, substep_filter, status_filter, output_json)
        return

    # Fetch step logs
    step_logs = _fetch_step_logs(db, run_id, step_filter)

    # Fetch step events
    step_events = _fetch_step_events(
        db, run_id, step_filter, substep_filter, status_filter, limit
    )

    if output_json:
        _output_logs_json(step_logs, step_events)
    else:
        _output_logs_text(run, step_logs, step_events)


def _fetch_step_logs(
    db, run_id: str, step_filter: str | None
) -> list[dict[str, Any]]:
    """Fetch step logs from the database."""
    sql = "SELECT * FROM step_logs WHERE run_id = ?"
    params: list[Any] = [run_id]

    if step_filter:
        sql += " AND step_id = ?"
        params.append(step_filter)

    sql += " ORDER BY started_at ASC"
    result = db.query(sql, params)
    return result.rows


def _fetch_step_events(
    db,
    run_id: str,
    step_filter: str | None,
    substep_filter: str | None,
    status_filter: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    """Fetch step events from the database with filters."""
    sql = "SELECT * FROM step_events WHERE run_id = ?"
    params: list[Any] = [run_id]

    if step_filter:
        sql += " AND step_id = ?"
        params.append(step_filter)

    if substep_filter:
        sql += " AND substep = ?"
        params.append(substep_filter)

    if status_filter:
        sql += " AND status = ?"
        params.append(status_filter)

    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    result = db.query(sql, params)
    # Reverse to get chronological order (oldest first)
    return list(reversed(result.rows))


def _output_logs_json(
    step_logs: list[dict[str, Any]], step_events: list[dict[str, Any]]
):
    """Output logs as JSON lines."""
    for event in step_events:
        output = {
            "timestamp": str(event.get("created_at")) if event.get("created_at") else None,
            "step": event.get("step_id"),
            "substep": event.get("substep"),
            "status": event.get("status"),
            "current": event.get("current"),
            "total": event.get("total"),
            "message": event.get("message"),
        }
        print(json.dumps(output))


def _output_logs_text(
    run: dict[str, Any],
    step_logs: list[dict[str, Any]],
    step_events: list[dict[str, Any]],
):
    """Output logs in human-readable format."""
    console.print(f"\n[bold]Workflow:[/bold] {run.get('workflow')} ({run.get('id')})")
    console.print(f"[bold]Status:[/bold] {run.get('status')}")
    console.print()

    # Show step summaries
    if step_logs:
        console.print("[bold]Steps:[/bold]")
        table = Table(box=None, show_edge=False)
        table.add_column("Step", style="cyan")
        table.add_column("Tool")
        table.add_column("Status")
        table.add_column("Input", justify="right")
        table.add_column("Output", justify="right")
        table.add_column("Errors", justify="right")
        table.add_column("Duration")

        for step in step_logs:
            step_status = step.get("status", "unknown")
            if step_status == "completed":
                status_display = f"[green]{step_status}[/green]"
            elif step_status in ("failed", "canceled"):
                status_display = f"[red]{step_status}[/red]"
            elif step_status == "running":
                status_display = f"[yellow]{step_status}[/yellow]"
            else:
                status_display = step_status

            # Calculate duration
            duration_str = "-"
            if step.get("started_at") and step.get("completed_at"):
                try:
                    started = datetime.fromisoformat(str(step["started_at"]).replace("Z", "+00:00"))
                    completed = datetime.fromisoformat(str(step["completed_at"]).replace("Z", "+00:00"))
                    duration = completed - started
                    duration_str = f"{duration.total_seconds():.1f}s"
                except (ValueError, TypeError):
                    pass

            input_str = str(step.get("input_count")) if step.get("input_count") is not None else "-"
            output_str = str(step.get("output_count")) if step.get("output_count") is not None else "-"
            error_str = str(step.get("error_count")) if step.get("error_count") else "-"

            table.add_row(
                step.get("step_id", "-"),
                step.get("tool", "-"),
                status_display,
                input_str,
                output_str,
                error_str,
                duration_str,
            )

        console.print(table)
        console.print()

    # Show recent events
    if step_events:
        console.print("[bold]Recent Events:[/bold]")
        for event in step_events:
            _print_event(event)
    else:
        console.print("[dim]No events found[/dim]")

    console.print()


def _print_event(event: dict[str, Any]):
    """Print a single event in formatted text."""
    # Format timestamp
    created_at = event.get("created_at")
    if created_at:
        try:
            if isinstance(created_at, str):
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            else:
                dt = created_at
            timestamp = dt.strftime("%H:%M:%S")
        except (ValueError, AttributeError):
            timestamp = datetime.now().strftime("%H:%M:%S")
    else:
        timestamp = datetime.now().strftime("%H:%M:%S")

    # Format step path
    step_id = event.get("step_id", "unknown")
    substep = event.get("substep")
    if substep:
        step_path = f"{step_id}/{substep}"
    else:
        step_path = step_id

    # Format status with color
    status = event.get("status", "progress")
    if status == "completed":
        status_display = f"[green]{status}[/green]"
    elif status == "failed":
        status_display = f"[red]{status}[/red]"
    elif status == "running":
        status_display = f"[yellow]{status}[/yellow]"
    else:
        status_display = status

    # Format progress
    current = event.get("current")
    total = event.get("total")
    if current is not None and total is not None:
        progress = f" [{current}/{total}]"
    elif current is not None:
        progress = f" [{current}]"
    else:
        progress = ""

    # Format message
    message = event.get("message")
    message_part = f" {message}" if message else ""

    console.print(f"[dim][{timestamp}][/dim] {step_path}: {status_display}{progress}{message_part}")


def _tail_logs(
    db,
    run_id: str,
    step_filter: str | None,
    substep_filter: str | None,
    status_filter: str | None,
    output_json: bool,
):
    """Stream logs in tail mode until workflow completes."""
    from kurt.observability import TERMINAL_STATUSES

    console.print(f"[bold]Following logs for workflow:[/bold] {run_id}\n")

    cursor_id = 0

    try:
        while True:
            # Fetch new events since cursor
            sql = "SELECT * FROM step_events WHERE run_id = ? AND id > ?"
            params: list[Any] = [run_id, cursor_id]

            if step_filter:
                sql += " AND step_id = ?"
                params.append(step_filter)

            if substep_filter:
                sql += " AND substep = ?"
                params.append(substep_filter)

            if status_filter:
                sql += " AND status = ?"
                params.append(status_filter)

            sql += " ORDER BY id ASC"
            result = db.query(sql, params)

            for row in result.rows:
                cursor_id = row.get("id", cursor_id)
                if output_json:
                    output = {
                        "timestamp": str(row.get("created_at")) if row.get("created_at") else None,
                        "step": row.get("step_id"),
                        "substep": row.get("substep"),
                        "status": row.get("status"),
                        "current": row.get("current"),
                        "total": row.get("total"),
                        "message": row.get("message"),
                    }
                    print(json.dumps(output))
                else:
                    _print_event(row)

            # Check if workflow terminated
            run_result = db.query_one(
                "SELECT status FROM workflow_runs WHERE id = ?", [run_id]
            )
            if run_result and run_result.get("status") in TERMINAL_STATUSES:
                # Fetch any final events
                final_result = db.query(sql, params)
                for row in final_result.rows:
                    if row.get("id", 0) > cursor_id:
                        if output_json:
                            output = {
                                "timestamp": str(row.get("created_at")) if row.get("created_at") else None,
                                "step": row.get("step_id"),
                                "substep": row.get("substep"),
                                "status": row.get("status"),
                                "current": row.get("current"),
                                "total": row.get("total"),
                                "message": row.get("message"),
                            }
                            print(json.dumps(output))
                        else:
                            _print_event(row)

                if not output_json:
                    final_status = run_result.get("status")
                    if final_status == "completed":
                        console.print("\n[green]Workflow completed[/green]")
                    elif final_status == "failed":
                        console.print("\n[red]Workflow failed[/red]")
                    elif final_status == "canceled":
                        console.print("\n[yellow]Workflow canceled[/yellow]")
                break

            # No new events - wait before next poll
            if not result.rows:
                time.sleep(0.5)

    except KeyboardInterrupt:
        if not output_json:
            console.print("\n[yellow]Interrupted[/yellow]")


@click.command(name="cancel")
@click.argument("run_id")
@click.option("--timeout", default=5.0, help="Maximum wait time in seconds")
@track_command
def cancel_cmd(run_id: str, timeout: float):
    """Cancel a running workflow.

    Sends cancel signal and waits for acknowledgment.
    Returns cancel confirmation or timeout error.

    Examples:
        kurt cancel abc-123-def
        kurt cancel abc-123-def --timeout 10
    """
    db = _get_dolt_db()

    from kurt.observability import WorkflowLifecycle

    lifecycle = WorkflowLifecycle(db)
    run = lifecycle.get_run(run_id)

    if run is None:
        console.print(f"[red]Workflow not found: {run_id}[/red]")
        raise click.Abort()

    status = run.get("status")

    # Check if already in terminal state
    if status in ("completed", "failed", "canceled"):
        output = {
            "run_id": run_id,
            "success": False,
            "error": f"Workflow already in terminal state: {status}",
        }
        print(json.dumps(output, indent=2))
        return

    # Update to canceling then canceled
    try:
        if status == "running":
            lifecycle.update_status(run_id, "canceling")

        # Wait briefly for any running tasks
        start = time.time()
        while time.time() - start < timeout:
            run = lifecycle.get_run(run_id)
            if run and run.get("status") in ("completed", "failed", "canceled"):
                break
            time.sleep(0.5)

        # Force to canceled if still canceling
        run = lifecycle.get_run(run_id)
        if run and run.get("status") == "canceling":
            lifecycle.update_status(run_id, "canceled")

        output = {
            "run_id": run_id,
            "success": True,
            "status": "canceled",
            "message": f"Workflow {run_id} canceled",
        }
        print(json.dumps(output, indent=2))
        console.print(f"\n[green]Workflow {run_id} canceled[/green]")

    except Exception as e:
        output = {
            "run_id": run_id,
            "success": False,
            "error": str(e),
        }
        print(json.dumps(output, indent=2))
        console.print(f"[red]Error canceling workflow: {e}[/red]")
        raise click.Abort()


def _build_dry_run_output(
    workflow_def,
    parsed_inputs: dict[str, Any],
    workflow_path: Path | None = None,
) -> dict[str, Any]:
    """
    Build enhanced dry-run output with execution plan and config validation.

    Includes:
    - Workflow metadata
    - Input validation
    - Execution plan from DAG builder
    - Config validation against tool schemas
    """
    from kurt.workflows.toml.dag import CycleDetectedError, build_dag
    from kurt.workflows.toml.interpolation import interpolate_step_config
    from kurt.tools.core import TOOLS, get_tool

    # Build execution plan
    plan_output: dict[str, Any] = {}
    try:
        plan = build_dag(workflow_def.steps)
        plan_output = {
            "levels": plan.levels,
            "total_steps": plan.total_steps,
            "parallelizable": plan.parallelizable,
            "critical_path": plan.critical_path,
        }
    except CycleDetectedError as e:
        plan_output = {
            "error": str(e),
            "cycle": e.cycle,
        }

    # Merge inputs with defaults for validation
    merged_inputs: dict[str, Any] = {}
    for name, input_def in workflow_def.inputs.items():
        if name in parsed_inputs:
            merged_inputs[name] = parsed_inputs[name]
        elif input_def.default is not None:
            merged_inputs[name] = input_def.default

    # Include extra inputs
    for name, value in parsed_inputs.items():
        if name not in merged_inputs:
            merged_inputs[name] = value

    # Validate step configs against tool schemas
    config_validation: dict[str, dict[str, Any]] = {}
    workflow_input_names = set(workflow_def.inputs.keys())

    # Check for tools.py if any function steps exist
    tools_path = workflow_path.parent / "tools.py" if workflow_path else None
    tools_module = None
    if tools_path and tools_path.exists():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("tools", tools_path)
            if spec and spec.loader:
                tools_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(tools_module)
        except Exception:
            pass

    for step_name, step_def in workflow_def.steps.items():
        step_validation: dict[str, Any] = {
            "tool": step_def.type,
            "valid": True,
            "errors": [],
        }

        # Handle function-type steps
        if step_def.type == "function":
            if not step_def.function:
                step_validation["valid"] = False
                step_validation["errors"].append("Missing 'function' field for function step")
            elif not tools_path or not tools_path.exists():
                step_validation["valid"] = False
                step_validation["errors"].append(
                    f"tools.py not found at {tools_path or 'unknown path'}"
                )
            elif tools_module and not hasattr(tools_module, step_def.function):
                step_validation["valid"] = False
                step_validation["errors"].append(
                    f"Function '{step_def.function}' not found in tools.py"
                )
            else:
                step_validation["function"] = step_def.function
        # Check if tool is registered
        elif step_def.type not in TOOLS:
            step_validation["valid"] = False
            step_validation["errors"].append(f"Tool '{step_def.type}' not registered")
        else:
            # Try to validate config against tool's InputModel
            try:
                tool_class = get_tool(step_def.type)

                # Interpolate config with inputs
                interpolated_config = interpolate_step_config(
                    step_def.config,
                    merged_inputs,
                    workflow_input_names=workflow_input_names,
                    step_name=step_name,
                )

                # Build params like executor does
                params = {
                    "input_data": [],  # Empty for validation
                    **interpolated_config,
                }

                # Validate against InputModel
                tool_class.InputModel.model_validate(params)
                step_validation["interpolated_config"] = interpolated_config

            except Exception as e:
                step_validation["valid"] = False
                step_validation["errors"].append(str(e))

        config_validation[step_name] = step_validation

    # Check for missing required inputs
    missing_inputs = []
    for name, input_def in workflow_def.inputs.items():
        if input_def.required and name not in merged_inputs:
            missing_inputs.append(name)

    return {
        "workflow": workflow_def.workflow.name,
        "description": workflow_def.workflow.description,
        "dry_run": True,
        "inputs": {
            name: {
                "type": inp.type,
                "required": inp.required,
                "default": inp.default,
                "provided": name in parsed_inputs,
                "value": parsed_inputs.get(name, inp.default),
            }
            for name, inp in workflow_def.inputs.items()
        },
        "missing_inputs": missing_inputs,
        "execution_plan": plan_output,
        "steps": {
            name: {
                "type": step.type,
                "depends_on": step.depends_on,
                "config": step.config,
                "validation": config_validation.get(name, {}),
            }
            for name, step in workflow_def.steps.items()
        },
        "valid": (
            len(missing_inputs) == 0
            and "error" not in plan_output
            and all(v["valid"] for v in config_validation.values())
        ),
    }


@click.command(name="test")
@click.argument("workflow_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--fixtures",
    "-f",
    "fixtures_path",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to fixtures directory containing step output files",
)
@click.option(
    "--input",
    "-i",
    "inputs",
    multiple=True,
    help="Input values in key=value format (can specify multiple)",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Require fixtures for all steps (fail if any missing)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON",
)
@track_command
def test_cmd(
    workflow_path: Path,
    fixtures_path: Path,
    inputs: tuple[str, ...],
    strict: bool,
    output_json: bool,
):
    """Test a workflow using fixture data.

    Loads fixture files matching step names and reports which steps would
    use fixtures vs would execute. Validates the workflow without running
    actual tools.

    Fixture files should be named: {step_name}.output.jsonl

    Examples:
        kurt test workflows/pipeline.toml --fixtures=tests/fixtures/
        kurt test workflows/pipeline.toml -f fixtures/ --strict
        kurt test workflows/pipeline.toml -f fixtures/ -i url=https://example.com
    """
    from kurt.workflows.toml import parse_workflow
    from kurt.workflows.toml.dag import build_dag
    from kurt.workflows.toml.fixtures import (
        FixtureLoadError,
        FixtureNotFoundError,
        analyze_fixture_coverage,
        load_fixtures,
    )

    # Parse inputs
    parsed_inputs: dict[str, Any] = {}
    for input_str in inputs:
        key, value = _parse_input(input_str)
        parsed_inputs[key] = value

    # Parse workflow
    try:
        workflow_def = parse_workflow(workflow_path)
    except FileNotFoundError:
        console.print(f"[red]Error: Workflow file not found: {workflow_path}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error parsing workflow: {e}[/red]")
        raise click.Abort()

    # Load fixtures
    step_names = list(workflow_def.steps.keys())
    try:
        fixture_set = load_fixtures(
            fixtures_path,
            step_names=step_names,
            strict=strict,
        )
    except FixtureNotFoundError as e:
        if output_json:
            print(json.dumps({
                "success": False,
                "error": str(e),
                "step": e.step_name,
            }))
        else:
            console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()
    except FixtureLoadError as e:
        if output_json:
            print(json.dumps({
                "success": False,
                "error": str(e),
                "step": e.step_name,
                "path": str(e.path),
            }))
        else:
            console.print(f"[red]Error loading fixture: {e}[/red]")
        raise click.Abort()

    # Analyze coverage
    coverage = analyze_fixture_coverage(step_names, fixture_set)

    # Build execution plan
    try:
        plan = build_dag(workflow_def.steps)
        plan_valid = True
        plan_error = None
    except Exception as e:
        plan_valid = False
        plan_error = str(e)

    # Build dry-run output for validation
    dry_run_output = _build_dry_run_output(workflow_def, parsed_inputs)

    if output_json:
        output = {
            "workflow": workflow_def.workflow.name,
            "fixtures_path": str(fixtures_path),
            "fixture_coverage": coverage.to_dict(),
            "execution_plan": dry_run_output.get("execution_plan", {}),
            "validation": {
                "workflow_valid": dry_run_output.get("valid", False),
                "plan_valid": plan_valid,
                "plan_error": plan_error,
                "missing_inputs": dry_run_output.get("missing_inputs", []),
            },
            "steps": {
                name: {
                    "has_fixture": name in coverage.steps_with_fixtures,
                    "fixture_path": str(coverage.fixture_paths.get(name, "")) or None,
                    "fixture_records": len(fixture_set.get_output_data(name)),
                    "would_execute": name in coverage.steps_without_fixtures,
                    "tool": workflow_def.steps[name].type,
                    "config_valid": dry_run_output.get("steps", {}).get(name, {}).get("validation", {}).get("valid", False),
                }
                for name in step_names
            },
            "success": True,
        }
        print(json.dumps(output, indent=2, default=str))
    else:
        # Rich text output
        console.print(f"\n[bold]Workflow:[/bold] {workflow_def.workflow.name}")
        console.print(f"[bold]Fixtures:[/bold] {fixtures_path}")
        console.print()

        # Coverage summary
        total = len(step_names)
        with_fixtures = len(coverage.steps_with_fixtures)
        len(coverage.steps_without_fixtures)
        pct = (with_fixtures / max(1, total)) * 100

        console.print(f"[bold]Coverage:[/bold] {with_fixtures}/{total} steps ({pct:.0f}%)")
        console.print()

        # Steps table
        table = Table(box=None, show_edge=False)
        table.add_column("Step", style="cyan")
        table.add_column("Tool")
        table.add_column("Fixture")
        table.add_column("Records", justify="right")
        table.add_column("Config Valid")

        for step_name in step_names:
            step_def = workflow_def.steps[step_name]
            has_fixture = step_name in coverage.steps_with_fixtures
            records = len(fixture_set.get_output_data(step_name))
            config_valid = dry_run_output.get("steps", {}).get(step_name, {}).get("validation", {}).get("valid", False)

            fixture_display = "[green]Yes[/green]" if has_fixture else "[yellow]No (would execute)[/yellow]"
            records_display = str(records) if has_fixture else "-"
            valid_display = "[green]Yes[/green]" if config_valid else "[red]No[/red]"

            table.add_row(
                step_name,
                step_def.type,
                fixture_display,
                records_display,
                valid_display,
            )

        console.print(table)
        console.print()

        # Execution plan
        if plan_valid:
            console.print("[bold]Execution Plan:[/bold]")
            for level_idx, level in enumerate(plan.levels):
                level_str = ", ".join(level)
                console.print(f"  Level {level_idx}: {level_str}")
            console.print(f"  [dim]Critical path: {' -> '.join(plan.critical_path)}[/dim]")
        else:
            console.print(f"[red]Execution plan error: {plan_error}[/red]")

        console.print()

        # Validation status
        if dry_run_output.get("valid"):
            console.print("[green]Workflow is valid[/green]")
        else:
            console.print("[red]Workflow has validation errors[/red]")
            if dry_run_output.get("missing_inputs"):
                console.print(f"  Missing inputs: {', '.join(dry_run_output['missing_inputs'])}")

        console.print()


# Command group for workflow management (alternative entry point)
@click.group(name="workflow")
def workflow_group():
    """
    Manage workflows (both TOML and Markdown formats).

    \\b
    This unified group handles:
    - TOML engine-driven workflows (with DAG steps)
    - MD/TOML agent workflows (Claude Code execution)

    \\b
    Core Commands:
      run        Run a workflow (handles both formats)
      status     Show workflow status
      logs       View step logs for a workflow run
      cancel     Cancel a running workflow
      test       Test a workflow with fixtures

    \\b
    Definition Commands (from agents):
      list       List all workflow definitions
      show       Show workflow definition details
      validate   Validate workflow file(s)
      history    Show run history for a workflow
      init       Initialize with example workflows
      create     Create a new workflow definition
    """
    pass


# Core TOML workflow commands
workflow_group.add_command(run_cmd, name="run")
workflow_group.add_command(status_cmd, name="status")
workflow_group.add_command(logs_cmd, name="logs")
workflow_group.add_command(cancel_cmd, name="cancel")
workflow_group.add_command(test_cmd, name="test")

# Import and add agent workflow commands (at end to avoid circular imports)
from kurt.workflows.agents.cli import create_cmd as agents_create_cmd  # noqa: E402
from kurt.workflows.agents.cli import history_cmd as agents_history_cmd  # noqa: E402
from kurt.workflows.agents.cli import init_cmd as agents_init_cmd  # noqa: E402
from kurt.workflows.agents.cli import list_cmd as agents_list_cmd  # noqa: E402
from kurt.workflows.agents.cli import show_cmd as agents_show_cmd  # noqa: E402
from kurt.workflows.agents.cli import validate_cmd as agents_validate_cmd  # noqa: E402

workflow_group.add_command(agents_list_cmd, name="list")
workflow_group.add_command(agents_show_cmd, name="show")
workflow_group.add_command(agents_validate_cmd, name="validate")
workflow_group.add_command(agents_history_cmd, name="history")
workflow_group.add_command(agents_init_cmd, name="init")
workflow_group.add_command(agents_create_cmd, name="create")

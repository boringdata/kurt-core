"""Workflow management CLI commands."""

from __future__ import annotations

import json
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from kurt_new.admin.telemetry.decorators import track_command

console = Console()


def _check_dbos_available() -> bool:
    """Check if DBOS is available."""
    try:
        from dbos import DBOS  # noqa: F401

        return True
    except ImportError:
        console.print("[red]Error: DBOS is not installed[/red]")
        console.print("[dim]Workflows functionality requires DBOS.[/dim]")
        raise click.Abort()


@click.group(name="workflows")
def workflows_group():
    """Manage background workflows."""
    pass


@workflows_group.command(name="list")
@click.option(
    "--status",
    type=click.Choice(["PENDING", "SUCCESS", "ERROR", "RETRIES_EXCEEDED", "CANCELLED"]),
    help="Filter by workflow status",
)
@click.option("--limit", default=50, help="Maximum number of workflows to show")
@click.option("--id", "id_filter", help="Filter by workflow ID (substring match)")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
@track_command
def list_workflows(status: Optional[str], limit: int, id_filter: Optional[str], output_format: str):
    """
    List background workflows.

    Examples:
        kurt workflows list
        kurt workflows list --status SUCCESS
        kurt workflows list --id d28902 --format json
    """
    _check_dbos_available()

    from sqlalchemy import text

    from kurt_new.db import managed_session

    with managed_session() as session:
        sql = """
            SELECT workflow_uuid, name, status, created_at, updated_at
            FROM workflow_status
        """
        params = {}
        conditions = []

        if status:
            conditions.append("status = :status")
            params["status"] = status

        if id_filter:
            conditions.append("workflow_uuid LIKE :id_filter")
            params["id_filter"] = f"%{id_filter}%"

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY created_at DESC LIMIT :limit"
        params["limit"] = limit

        result = session.execute(text(sql), params)
        workflows = result.fetchall()

    if not workflows:
        console.print("[yellow]No workflows found[/yellow]")
        return

    if output_format == "json":
        data = [
            {
                "workflow_id": wf[0],
                "name": wf[1],
                "status": wf[2],
                "created_at": str(wf[3]) if wf[3] else None,
                "updated_at": str(wf[4]) if wf[4] else None,
            }
            for wf in workflows
        ]
        print(json.dumps(data, indent=2))
        return

    table = Table(title="DBOS Workflows", box=None, show_edge=False)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Created", style="blue")
    table.add_column("Updated", style="blue")

    for wf in workflows:
        status_str = wf[2]
        if status_str == "SUCCESS":
            status_display = f"[green]{status_str}[/green]"
        elif status_str in ("ERROR", "RETRIES_EXCEEDED"):
            status_display = f"[red]{status_str}[/red]"
        elif status_str == "PENDING":
            status_display = f"[yellow]{status_str}[/yellow]"
        else:
            status_display = status_str

        table.add_row(
            wf[0][:12] + "...",
            wf[1][:40] + ("..." if len(wf[1]) > 40 else ""),
            status_display,
            str(wf[3])[:19] if wf[3] else "-",
            str(wf[4])[:19] if wf[4] else "-",
        )

    console.print(table)


@workflows_group.command(name="status")
@click.argument("workflow_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@track_command
def workflow_status(workflow_id: str, output_json: bool):
    """
    Show detailed workflow status.

    Uses the new core/status.py module for live status display.

    Example:
        kurt workflows status abc123
        kurt workflows status abc123 --json
    """
    _check_dbos_available()

    from kurt_new.core.status import format_live_status, get_live_status

    status = get_live_status(workflow_id)

    if not status:
        console.print(f"[red]Workflow {workflow_id} not found[/red]")
        return

    if output_json:
        print(json.dumps(status, indent=2, default=str))
    else:
        formatted = format_live_status(status)
        console.print(formatted)


def _format_timestamp(ts) -> str:
    """Format a timestamp for display."""
    if ts is None:
        return "-"
    try:
        from datetime import datetime

        return datetime.utcfromtimestamp(float(ts)).strftime("%H:%M:%S")
    except Exception:
        return str(ts)[:19]


def _format_streams_table(streams: list[dict]) -> None:
    """Format workflow streams as a table."""
    table = Table(box=None, show_edge=False)
    table.add_column("Time", style="dim", no_wrap=True)
    table.add_column("Step", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Progress", justify="right")
    table.add_column("Details", style="dim")

    for entry in streams:
        ts = _format_timestamp(entry.get("timestamp"))
        step = entry.get("step", "-")
        status = entry.get("status", "-")

        # Color status
        if status == "success":
            status = f"[green]{status}[/green]"
        elif status == "error":
            status = f"[red]{status}[/red]"
        elif status == "start":
            status = f"[blue]{status}[/blue]"

        # Progress info
        idx = entry.get("idx")
        total = entry.get("total")
        if idx is not None and total:
            progress = f"{idx + 1}/{total}"
        elif total:
            progress = f"0/{total}"
        else:
            progress = "-"

        # Details
        details = []
        if entry.get("latency_ms"):
            details.append(f"{entry['latency_ms']}ms")
        if entry.get("error"):
            details.append(f"err: {entry['error'][:30]}")
        details_str = " ".join(details) if details else "-"

        table.add_row(ts, step, status, progress, details_str)

    console.print(table)


@workflows_group.command(name="logs")
@click.argument("workflow_id")
@click.option("--step", help="Filter logs by step name")
@click.option("--limit", default=200, help="Maximum number of log entries")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@track_command
def workflow_logs(workflow_id: str, step: Optional[str], limit: int, output_json: bool):
    """
    Show workflow logs and progress streams.

    Example:
        kurt workflows logs abc123
        kurt workflows logs abc123 --step extract --limit 50
    """
    _check_dbos_available()

    from kurt_new.core.status import read_workflow_streams

    # Read all streams (progress events contain the execution log)
    streams = read_workflow_streams(workflow_id, limit=limit)

    # Filter by step if specified
    if step:
        streams = [s for s in streams if s.get("step") == step]

    if not streams:
        console.print("[yellow]No logs found[/yellow]")
        return

    if output_json:
        print(json.dumps(streams, indent=2, default=str))
    else:
        _format_streams_table(streams)


@workflows_group.command(name="follow")
@click.argument("workflow_id")
@click.option("--wait", is_flag=True, help="Wait for workflow to complete")
@track_command
def follow_workflow(workflow_id: str, wait: bool):
    """
    Attach to a running workflow and show live progress.

    Example:
        kurt workflows follow abc123 --wait
    """
    _check_dbos_available()

    import time

    from rich.live import Live
    from rich.panel import Panel

    from kurt_new.core.status import format_live_status, get_live_status

    console.print(f"[bold]Following workflow:[/bold] {workflow_id}\n")

    with Live(console=console, refresh_per_second=2) as live:
        while True:
            status = get_live_status(workflow_id)

            if not status:
                live.update("[red]Workflow not found[/red]")
                break

            formatted = format_live_status(status)
            live.update(Panel(formatted, title=f"Workflow {workflow_id[:12]}..."))

            if status.get("status") in ("SUCCESS", "ERROR", "RETRIES_EXCEEDED", "CANCELLED"):
                console.print(f"\n[bold]Workflow completed:[/bold] {status.get('status')}")
                break

            if not wait:
                console.print("\n[dim]Workflow still running. Use --wait to keep following.[/dim]")
                break

            time.sleep(2)


@workflows_group.command(name="cancel")
@click.argument("workflow_id")
@track_command
def cancel_workflow(workflow_id: str):
    """
    Cancel a workflow.

    Current step will complete before stopping.

    Example:
        kurt workflows cancel abc123
    """
    _check_dbos_available()

    from dbos import DBOS

    try:
        DBOS.cancel_workflow(workflow_id)
        console.print(f"[green]Workflow {workflow_id} cancelled[/green]")
        console.print("[dim]Note: Current step will complete before stopping[/dim]")
    except Exception as e:
        console.print(f"[red]Error cancelling workflow: {e}[/red]")


@workflows_group.command(name="stats")
@click.argument("workflow_id", required=False)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@track_command
def workflow_stats(workflow_id: Optional[str], output_json: bool):
    """
    Show LLM usage statistics for a workflow.

    Example:
        kurt workflows stats
        kurt workflows stats abc123 --json
    """
    from kurt_new.core.tracing import LLMTracer

    tracer = LLMTracer()

    if workflow_id:
        stats = tracer.stats(workflow_id=workflow_id)
    else:
        stats = tracer.stats()

    if output_json:
        print(json.dumps(stats, indent=2, default=str))
        return

    console.print("\n[bold]LLM Usage Statistics[/bold]")
    console.print("=" * 50)

    if workflow_id:
        console.print(f"Workflow: {workflow_id}")

    console.print(f"\nTotal Calls: {stats.get('total_calls', 0)}")
    console.print(f"Total Tokens: {stats.get('total_tokens', 0):,}")
    console.print(f"Total Cost: ${stats.get('total_cost', 0):.4f}")

    if stats.get("by_step"):
        console.print("\n[bold]By Step:[/bold]")
        table = Table(box=None, show_edge=False)
        table.add_column("Step", style="cyan")
        table.add_column("Calls", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Cost", justify="right")

        for step_name, step_stats in stats["by_step"].items():
            table.add_row(
                step_name,
                str(step_stats.get("calls", 0)),
                f"{step_stats.get('tokens', 0):,}",
                f"${step_stats.get('cost', 0):.4f}",
            )

        console.print(table)

    console.print()

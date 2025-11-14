"""
Workflow Management Commands

CLI commands for managing DBOS workflows (background jobs).

Commands:
- kurt workflows list: List all workflows
- kurt workflows status <id>: Show workflow status and result
- kurt workflows cancel <id>: Cancel a workflow (completes current step)
"""

import json

import click
from rich.console import Console
from rich.table import Table

from kurt.workflows import DBOS_AVAILABLE

console = Console()


@click.group(name="workflows")
def workflows_group():
    """Manage background workflows"""
    pass


def _check_dbos_available():
    """Check if DBOS is available and show error if not"""
    if not DBOS_AVAILABLE:
        console.print("[red]Error: DBOS is not installed[/red]")
        console.print("[dim]Workflows functionality requires DBOS to be installed.[/dim]")
        console.print("[dim]Run: uv sync[/dim]")
        raise click.Abort()
    return True


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
    type=click.Choice(["table", "plain"]),
    default="table",
    help="Output format (table or plain)",
)
def list_workflows(status, limit, id_filter, output_format):
    """
    List background workflows.

    Examples:
        # List recent workflows (table format)
        kurt workflows list

        # Plain format (easy to copy full IDs)
        kurt workflows list --format plain

        # Get just the workflow IDs
        kurt workflows list --format plain | cut -d'|' -f1

        # Filter by workflow ID substring
        kurt workflows list --id d28902

        # Filter by status
        kurt workflows list --status SUCCESS

        # Combine filters
        kurt workflows list --id cbda --status SUCCESS --format plain

        # Limit results
        kurt workflows list --limit 10
    """
    _check_dbos_available()

    try:
        # DBOS provides workflow querying via SQL
        # We'll query the dbos_workflow_status table directly
        from sqlalchemy import text

        from kurt.db.database import get_session

        with get_session() as session:
            # Build SQL query
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

        # Plain format output (easy to copy/grep)
        if output_format == "plain":
            for wf in workflows:
                console.print(f"{wf[0]} | {wf[1]} | {wf[2]} | {wf[3]} | {wf[4]}")
            return

        # Create rich table with full IDs
        table = Table(title="DBOS Workflows", box=None, show_edge=False, pad_edge=False)

        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="magenta", no_wrap=True)
        table.add_column("Status", style="green", no_wrap=True)
        table.add_column("Created", style="blue", no_wrap=True)
        table.add_column("Updated", style="blue", no_wrap=True)

        for wf in workflows:
            # Color code status
            status_str = wf[2]
            if status_str == "SUCCESS":
                status_display = f"[green]{status_str}[/green]"
            elif status_str == "ERROR" or status_str == "RETRIES_EXCEEDED":
                status_display = f"[red]{status_str}[/red]"
            elif status_str == "PENDING":
                status_display = f"[yellow]{status_str}[/yellow]"
            else:
                status_display = status_str

            # Always display full ID
            table.add_row(
                wf[0],  # workflow_uuid (full ID)
                wf[1],  # workflow_class_name
                status_display,
                str(wf[3])[:19] if wf[3] else "-",  # created_at
                str(wf[4])[:19] if wf[4] else "-",  # updated_at
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing workflows: {e}[/red]")
        raise


@workflows_group.command(name="status")
@click.argument("workflow_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def workflow_status(workflow_id, output_json):
    """
    Show detailed status of a workflow.

    Args:
        workflow_id: Full or partial workflow UUID

    Example:
        kurt workflows status abc123...
        kurt workflows status abc123 --json
    """
    _check_dbos_available()

    try:
        # Query workflow status from database
        from sqlalchemy import text

        from kurt.db.database import get_session

        with get_session() as session:
            # Find workflow by partial or full UUID
            sql = """
                SELECT workflow_uuid, name, status, created_at, updated_at,
                       authenticated_user, output, error
                FROM workflow_status
                WHERE workflow_uuid LIKE :workflow_id || '%'
                LIMIT 1
            """
            result = session.execute(text(sql), {"workflow_id": workflow_id})
            wf = result.fetchone()

        if not wf:
            console.print(f"[red]Workflow {workflow_id} not found[/red]")
            return

        workflow_uuid, workflow_name, status, created_at, updated_at, user, output, error = wf

        if output_json:
            # JSON output
            output_data = None
            if output:
                try:
                    # DBOS stores results as pickled objects (base64-encoded)
                    import base64
                    import pickle

                    decoded = base64.b64decode(output)
                    output_data = pickle.loads(decoded)
                except Exception:  # noqa: S110
                    # Fallback: try JSON parsing
                    try:
                        output_data = json.loads(output)
                    except Exception:  # noqa: S110
                        output_data = output

            data = {
                "workflow_id": workflow_uuid,
                "workflow_name": workflow_name,
                "status": status,
                "created_at": str(created_at),
                "updated_at": str(updated_at),
                "user": user,
                "output": output_data,
                "error": error,
            }
            console.print(json.dumps(data, indent=2, default=str))
        else:
            # Human-readable output
            console.print(f"\n[bold]Workflow {workflow_uuid}[/bold]")
            console.print(f"Name: {workflow_name}")
            console.print(f"Status: [{'green' if status == 'SUCCESS' else 'red'}]{status}[/]")
            console.print(f"Created: {created_at}")
            console.print(f"Updated: {updated_at}")

            if output and status == "SUCCESS":
                console.print("\n[green]Result:[/green]")
                try:
                    # DBOS stores results as pickled objects (base64-encoded)
                    import base64
                    import pickle

                    decoded = base64.b64decode(output)
                    result_data = pickle.loads(decoded)
                    console.print(json.dumps(result_data, indent=2, default=str))
                except Exception:
                    # Fallback: try JSON parsing or show raw output
                    try:
                        result_data = json.loads(output)
                        console.print(json.dumps(result_data, indent=2))
                    except Exception:  # noqa: S110
                        console.print(output)

            if error:
                console.print(f"\n[red]Error:[/red] {error}")

    except Exception as e:
        console.print(f"[red]Error getting workflow status: {e}[/red]")
        raise


@workflows_group.command(name="process")
@click.option("--all", "process_all", is_flag=True, help="Process all enqueued workflows")
@click.option("--workflow-id", help="Process specific workflow by ID")
@click.option(
    "--keep-alive", type=int, help="Keep process alive for N seconds to let workflows execute"
)
def process_workflows(process_all, workflow_id, keep_alive):
    """
    Force-execute enqueued workflows that were never picked up automatically.

    This is useful for debugging edge cases where workflows got stuck in ENQUEUED
    state and never executed. It keeps the process alive to let the DBOS executor
    pick up and run the workflows.

    Example:
        # Check what's enqueued
        kurt workflows list --status ENQUEUED

        # Keep process alive for 30 seconds to let workflows execute
        kurt workflows process --all --keep-alive 30

        # Process specific workflow
        kurt workflows process --workflow-id abc123 --keep-alive 10
    """
    _check_dbos_available()

    import signal
    import time

    from sqlalchemy import text

    from kurt.db.database import get_session
    from kurt.workflows import get_dbos

    dbos = get_dbos()  # noqa: F841

    # Track if user requested early exit
    exit_requested = False

    def signal_handler(sig, frame):
        nonlocal exit_requested
        console.print("\n[yellow]Exit requested, shutting down...[/yellow]")
        exit_requested = True

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Get enqueued workflows
        with get_session() as session:
            if workflow_id:
                sql = text("""
                    SELECT workflow_uuid, name, status, queue_name
                    FROM workflow_status
                    WHERE workflow_uuid LIKE :workflow_id || '%'
                    LIMIT 1
                """)
                result = session.execute(sql, {"workflow_id": workflow_id})
                workflows = [result.fetchone()]
                if workflows[0] is None:
                    console.print(f"[red]Workflow {workflow_id} not found[/red]")
                    return
            else:
                sql = text("""
                    SELECT workflow_uuid, name, status, queue_name
                    FROM workflow_status
                    WHERE status = 'ENQUEUED'
                    ORDER BY priority ASC, created_at ASC
                """)
                result = session.execute(sql)
                workflows = result.fetchall()

        if not workflows or (len(workflows) == 1 and workflows[0] is None):
            console.print("[green]✓ No workflows enqueued[/green]")
            return

        # Show what will be processed
        console.print(f"[bold]Found {len(workflows)} enqueued workflow(s):[/bold]\n")

        from rich.table import Table

        table = Table(show_header=True)
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Status", style="yellow")
        table.add_column("Queue", style="blue")

        for wf_uuid, name, status, queue_name in workflows:
            table.add_row(
                wf_uuid[:12] + "...",
                name[:30] + ("..." if len(name) > 30 else ""),
                status,
                queue_name or "none",
            )

        console.print(table)

        if not process_all and not workflow_id:
            console.print("\n[yellow]No workflows will be processed[/yellow]")
            console.print("[dim]Use --all to process all enqueued workflows[/dim]")
            console.print("[dim]Or --workflow-id <id> to process a specific workflow[/dim]")
            return

        # Import workflow modules to register them with DBOS
        console.print("\n[cyan]Registering workflow modules...[/cyan]")
        try:
            # Import all workflow modules to register decorated functions
            from kurt.workflows import map as _map_workflows  # noqa
            from kurt.workflows import fetch as _fetch_workflows  # noqa
            from kurt.workflows import index as _index_workflows  # noqa

            console.print("[dim]✓ Workflow modules registered[/dim]\n")
        except ImportError as e:
            console.print(
                f"[yellow]Warning: Could not import some workflow modules: {e}[/yellow]\n"
            )

        # Resume enqueued workflows in background using ThreadPoolExecutor
        console.print(
            f"[cyan]Resuming {len(workflows)} enqueued workflow(s) in background...[/cyan]\n"
        )

        import concurrent.futures

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        futures = []
        resumed_count = 0

        for wf_uuid, name, status, queue_name in workflows:
            if status == "ENQUEUED":
                try:
                    # Submit resume_workflow to thread pool for background execution
                    future = executor.submit(dbos.resume_workflow, wf_uuid)
                    futures.append((wf_uuid, name, future))
                    console.print(
                        f"[green]✓[/green] Submitted to background: {name[:40]} ({wf_uuid[:12]}...)"
                    )
                    resumed_count += 1
                except Exception as e:
                    console.print(f"[red]✗[/red] Failed to submit {wf_uuid[:12]}: {e}")

        # Determine keep-alive duration
        if keep_alive is None:
            keep_alive = 30  # Default 30 seconds

        console.print(
            f"\n[cyan]Keeping process alive for {keep_alive} seconds to monitor execution...[/cyan]"
        )
        console.print("[dim]Press Ctrl+C to exit early[/dim]\n")

        # Monitor workflow progress
        start_time = time.time()
        last_check = start_time

        try:
            while (time.time() - start_time) < keep_alive and not exit_requested:
                # Check status every 2 seconds
                if time.time() - last_check >= 2:
                    last_check = time.time()

                    # Query current status
                    with get_session() as session:
                        workflow_ids = [wf[0] for wf in workflows]
                        placeholders = ",".join([f":id{i}" for i in range(len(workflow_ids))])
                        sql = text(f"""
                            SELECT workflow_uuid, name, status
                            FROM workflow_status
                            WHERE workflow_uuid IN ({placeholders})
                        """)
                        params = {f"id{i}": wf_id for i, wf_id in enumerate(workflow_ids)}
                        result = session.execute(sql, params)
                        current_status = {row[0]: (row[1], row[2]) for row in result.fetchall()}

                    # Show status updates
                    for wf_uuid, original_name, original_status, _ in workflows:
                        if wf_uuid in current_status:
                            name, status = current_status[wf_uuid]
                            if status != original_status:
                                console.print(f"[cyan]Status update:[/cyan] {name[:30]} → {status}")

                    # Check if all completed
                    all_done = all(
                        current_status.get(wf[0], (None, "ENQUEUED"))[1]
                        in ["SUCCESS", "ERROR", "CANCELLED"]
                        for wf in workflows
                    )

                    if all_done:
                        console.print("\n[green]✓ All workflows completed![/green]")
                        break

                time.sleep(0.5)

        finally:
            # Cleanup: shutdown the executor
            console.print("\n[dim]Shutting down executor...[/dim]")
            executor.shutdown(wait=False, cancel_futures=False)

        # Final status report
        console.print("\n[bold]Final Status:[/bold]\n")

        with get_session() as session:
            workflow_ids = [wf[0] for wf in workflows]
            placeholders = ",".join([f":id{i}" for i in range(len(workflow_ids))])
            sql = text(f"""
                SELECT workflow_uuid, name, status
                FROM workflow_status
                WHERE workflow_uuid IN ({placeholders})
            """)
            params = {f"id{i}": wf_id for i, wf_id in enumerate(workflow_ids)}
            result = session.execute(sql, params)
            final_status = result.fetchall()

        success_count = sum(1 for _, _, status in final_status if status == "SUCCESS")
        error_count = sum(1 for _, _, status in final_status if status == "ERROR")
        pending_count = sum(1 for _, _, status in final_status if status in ["ENQUEUED", "PENDING"])

        console.print(f"[green]✓ Success:[/green] {success_count}")
        console.print(f"[red]✗ Error:[/red] {error_count}")
        console.print(f"[yellow]⋯ Still Running:[/yellow] {pending_count}")

        if pending_count > 0:
            console.print(
                "\n[dim]Some workflows are still running. Use 'kurt workflows list' to check status.[/dim]"
            )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise


@workflows_group.command(name="follow")
@click.argument("workflow_id")
@click.option("--wait", is_flag=True, help="Wait for workflow to complete")
def follow_workflow(workflow_id, wait):
    """
    Attach to a running workflow and show live progress.

    This command retrieves events and streams published by the workflow
    to show progress in real-time. If the workflow publishes progress
    events, they will be displayed as they occur.

    Args:
        workflow_id: Full or partial workflow UUID

    Example:
        kurt workflows follow abc123...
        kurt workflows follow abc123 --wait  # Wait until completion
    """
    _check_dbos_available()

    import time

    from sqlalchemy import text

    from kurt.db.database import get_session
    from kurt.workflows import get_dbos

    dbos = get_dbos()  # noqa: F841

    try:
        # First, verify workflow exists and get full ID
        with get_session() as session:
            sql = text("""
                SELECT workflow_uuid, name, status
                FROM workflow_status
                WHERE workflow_uuid LIKE :workflow_id || '%'
                LIMIT 1
            """)
            result = session.execute(sql, {"workflow_id": workflow_id})
            wf = result.fetchone()

        if not wf:
            console.print(f"[red]Workflow {workflow_id} not found[/red]")
            return

        full_workflow_id, workflow_name, status = wf

        console.print(f"[bold]Following workflow:[/bold] {full_workflow_id}")
        console.print(f"[bold]Name:[/bold] {workflow_name}")
        console.print(f"[bold]Status:[/bold] {status}\n")

        # Check if there's a log file for this workflow
        from pathlib import Path

        log_file = Path(f".kurt/logs/workflow-{full_workflow_id}.log")

        if wait and log_file.exists():
            # Stream the log file in real-time
            console.print("[dim]Streaming workflow output from log file...[/dim]\n")
            import select
            import subprocess

            try:
                # If workflow is already completed, just cat the file
                if status in ["SUCCESS", "ERROR", "RETRIES_EXCEEDED", "CANCELLED"]:
                    with open(log_file, "r") as f:
                        print(f.read(), end="")
                    console.print("\n[green]✓ Workflow completed[/green]")
                    return

                # Use tail -f to follow the log file
                proc = subprocess.Popen(
                    ["tail", "-f", "-n", "+1", str(log_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                # Stream output until workflow completes
                while True:
                    # Use select to check if there's data available (with timeout)
                    ready, _, _ = select.select([proc.stdout], [], [], 0.5)

                    if ready:
                        line = proc.stdout.readline()
                        if line:
                            print(line, end="")

                    # Check if workflow completed
                    with get_session() as session:
                        sql = text("""
                            SELECT status
                            FROM workflow_status
                            WHERE workflow_uuid = :workflow_id
                        """)
                        result = session.execute(sql, {"workflow_id": full_workflow_id})
                        row = result.fetchone()
                        if row and row[0] in ["SUCCESS", "ERROR", "RETRIES_EXCEEDED", "CANCELLED"]:
                            # Give it a moment to flush final output
                            time.sleep(0.5)
                            # Read any remaining lines (non-blocking)
                            while True:
                                ready, _, _ = select.select([proc.stdout], [], [], 0.1)
                                if not ready:
                                    break
                                line = proc.stdout.readline()
                                if not line:
                                    break
                                print(line, end="")
                            proc.terminate()
                            break

                console.print("\n[green]✓ Workflow completed[/green]")
                return
            except KeyboardInterrupt:
                proc.terminate()
                console.print("\n[yellow]Stopped following workflow[/yellow]")
                return

        # Fallback: use database polling
        # Try to retrieve workflow handle
        try:
            dbos.retrieve_workflow(full_workflow_id)
            console.print("[dim]Connected to workflow[/dim]\n")
        except Exception as e:
            console.print(f"[yellow]Could not retrieve workflow handle: {e}[/yellow]")
            console.print("[dim]Will monitor via database queries...[/dim]\n")

        # Monitor workflow progress with Rich Progress display
        import base64
        import pickle

        from rich.progress import (
            BarColumn,
            Progress,
            SpinnerColumn,
            TaskProgressColumn,
            TextColumn,
            TimeRemainingColumn,
        )

        last_status = status
        event_keys_seen = set()

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=False,
        ) as progress:
            # Create initial task
            main_task = progress.add_task(f"[cyan]{workflow_name}", total=100)

            while True:
                # Check current status
                with get_session() as session:
                    sql = text("""
                        SELECT status, output, error
                        FROM workflow_status
                        WHERE workflow_uuid = :workflow_id
                    """)
                    result = session.execute(sql, {"workflow_id": full_workflow_id})
                    row = result.fetchone()

                if not row:
                    console.print("[red]Workflow disappeared from database[/red]")
                    break

                current_status, output, error = row

                # Show status changes
                if current_status != last_status:
                    progress.console.print(f"[cyan]Status:[/cyan] {last_status} → {current_status}")
                    last_status = current_status

                # Check for events (progress updates)
                try:
                    # Query workflow events
                    with get_session() as session:
                        sql = text("""
                            SELECT key, value
                            FROM workflow_events
                            WHERE workflow_uuid = :workflow_id
                        """)
                        result = session.execute(sql, {"workflow_id": full_workflow_id})
                        events = result.fetchall()

                    for key, value in events:
                        if key not in event_keys_seen:
                            event_keys_seen.add(key)
                            # Try to unpickle the event value for better display
                            try:
                                decoded = base64.b64decode(value)
                                unpickled_value = pickle.loads(decoded)

                                # Handle different types of progress events
                                if key == "phase":
                                    progress.update(
                                        main_task, description=f"[cyan]{unpickled_value}"
                                    )
                                elif key == "target_url":
                                    progress.console.print(
                                        f"\n[bold]Discovering content from:[/bold] {unpickled_value}\n"
                                    )
                                elif key == "url":
                                    progress.update(
                                        main_task,
                                        description=f"[cyan]Processing: {unpickled_value}",
                                    )
                                elif key in ["result_total", "total_discovered"]:
                                    # Update progress based on total
                                    if isinstance(unpickled_value, (int, float)):
                                        progress.update(
                                            main_task, completed=min(unpickled_value * 10, 100)
                                        )
                                elif key == "status":
                                    if unpickled_value == "completed":
                                        progress.update(main_task, completed=100)
                                    else:
                                        progress.update(
                                            main_task, description=f"[cyan]{unpickled_value}"
                                        )
                                else:
                                    # Show other events as messages
                                    if (
                                        isinstance(unpickled_value, str)
                                        and len(unpickled_value) > 50
                                    ):
                                        # Don't spam with long values
                                        pass
                                    else:
                                        progress.console.print(
                                            f"[dim]• {key}: {unpickled_value}[/dim]"
                                        )
                            except Exception:  # noqa: S110
                                # If unpickling fails, skip raw value display in progress mode
                                pass
                except Exception:
                    # Events table might not exist or no events yet
                    pass

                # Check if workflow completed
                if current_status in ["SUCCESS", "ERROR", "RETRIES_EXCEEDED", "CANCELLED"]:
                    progress.update(main_task, completed=100)
                    progress.console.print(
                        f"\n[bold]Workflow completed with status:[/bold] {current_status}"
                    )

                    if current_status == "SUCCESS" and output:
                        progress.console.print("\n[green]Result:[/green]")
                        try:
                            # DBOS stores results as pickled objects (base64-encoded)
                            import base64
                            import pickle

                            decoded = base64.b64decode(output)
                            result_data = pickle.loads(decoded)
                            progress.console.print(json.dumps(result_data, indent=2, default=str))
                        except Exception:  # noqa: S110
                            # Fallback: try JSON parsing or show raw output
                            try:
                                result_data = json.loads(output)
                                progress.console.print(json.dumps(result_data, indent=2))
                            except Exception:  # noqa: S110
                                progress.console.print(output)

                    if error:
                        progress.console.print(f"\n[red]Error:[/red] {error}")

                    break

                if not wait:
                    progress.console.print(
                        "\n[dim]Workflow still running. Use --wait to keep following.[/dim]"
                    )
                    break

                # Wait before checking again
                time.sleep(2)

    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped following workflow[/yellow]")
    except Exception as e:
        console.print(f"[red]Error following workflow: {e}[/red]")
        raise


@workflows_group.command(name="cancel")
@click.argument("workflow_id")
def cancel_workflow(workflow_id):
    """
    Cancel a workflow.

    Note: DBOS workflows are designed to ensure data consistency.
    Cancellation will allow the current step to complete before stopping.

    Args:
        workflow_id: Full or partial workflow UUID

    Example:
        kurt workflows cancel abc123...
    """
    _check_dbos_available()

    from kurt.workflows import get_dbos

    dbos = get_dbos()

    try:
        dbos.cancel_workflow(workflow_id)
        console.print(f"[green]✓ Workflow {workflow_id} cancelled[/green]")
        console.print("[dim]Note: Current step will complete before stopping[/dim]")
    except Exception as e:
        console.print(f"[red]Error cancelling workflow: {e}[/red]")


__all__ = ["workflows_group"]

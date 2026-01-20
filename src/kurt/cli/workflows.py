"""Workflow management CLI commands."""

from __future__ import annotations

import json
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command

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

    from kurt.db import managed_session

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

    from kurt.core.status import format_live_status, get_live_status

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

    from kurt.core.status import read_workflow_streams

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

    from kurt.core.status import format_live_status, get_live_status

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
    from kurt.core.tracing import LLMTracer

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


# ============================================================================
# Workflow Definitions Subgroup
# ============================================================================


@workflows_group.group(name="defs")
def defs_group():
    """
    Manage workflow definitions (agent and YAML).

    \\b
    Workflow definitions can be:
    - Agent workflows (.md) - Executed by Claude Code
    - YAML workflows (.yaml) - Multi-step pipelines with Python/LLM/agentic steps
    """
    pass


@defs_group.command(name="list")
@click.option("--tag", "-t", help="Filter by tag")
@click.option(
    "--type",
    "wf_type",
    type=click.Choice(["agent", "yaml", "all"]),
    default="all",
    help="Filter by workflow type",
)
@click.option("--scheduled", is_flag=True, help="Only show scheduled workflows")
@track_command
def defs_list_cmd(tag: str, wf_type: str, scheduled: bool):
    """List all workflow definitions."""
    from kurt.workflows.registry import list_all_workflows

    workflows = list_all_workflows()

    if not workflows:
        console.print("[dim]No workflow definitions found.[/dim]")
        console.print(
            "[dim]Create .md or .yaml files in workflows/ or run 'kurt workflows defs init'.[/dim]"
        )
        return

    # Apply filters
    if wf_type != "all":
        workflows = [w for w in workflows if w.workflow_type == wf_type]
    if tag:
        workflows = [w for w in workflows if tag in w.tags]
    if scheduled:
        workflows = [w for w in workflows if w.schedule_cron]

    if not workflows:
        console.print("[dim]No matching workflow definitions found.[/dim]")
        return

    table = Table(title="Workflow Definitions")
    table.add_column("Name", style="cyan")
    table.add_column("Title")
    table.add_column("Type", style="magenta")
    table.add_column("Schedule")
    table.add_column("Tags")
    table.add_column("Steps")

    for w in workflows:
        schedule_str = "-"
        if w.schedule_cron:
            schedule_str = w.schedule_cron
            if not w.schedule_enabled:
                schedule_str = f"{schedule_str} (disabled)"

        tags = ", ".join(w.tags) if w.tags else "-"
        steps = str(w.step_count) if w.step_count else "-"

        table.add_row(w.name, w.title, w.workflow_type, schedule_str, tags, steps)

    console.print(table)


@defs_group.command(name="show")
@click.argument("name")
@track_command
def defs_show_cmd(name: str):
    """Show workflow definition details."""
    from kurt.workflows.registry import get_workflow, get_workflow_type

    wf_type = get_workflow_type(name)
    workflow = get_workflow(name)

    if not workflow:
        console.print(f"[red]Workflow not found: {name}[/red]")
        raise click.Abort()

    console.print()
    console.print(f"[bold cyan]{workflow.title}[/bold cyan]")
    console.print(f"[dim]Name: {workflow.name}[/dim]")
    console.print(f"[dim]Type: {wf_type}[/dim]")

    if workflow.description:
        console.print("\n[bold]Description:[/bold]")
        console.print(workflow.description)

    if wf_type == "agent":
        console.print("\n[bold]Agent Config:[/bold]")
        console.print(f"  Model: {workflow.agent.model}")
        console.print(f"  Max Turns: {workflow.agent.max_turns}")
        console.print(f"  Permission Mode: {workflow.agent.permission_mode}")
        console.print(f"  Allowed Tools: {', '.join(workflow.agent.allowed_tools)}")

        console.print("\n[bold]Guardrails:[/bold]")
        console.print(f"  Max Tokens: {workflow.guardrails.max_tokens:,}")
        console.print(f"  Max Tool Calls: {workflow.guardrails.max_tool_calls}")
        console.print(f"  Max Time: {workflow.guardrails.max_time}s")

    elif wf_type == "yaml":
        console.print("\n[bold]Steps:[/bold]")
        for i, step in enumerate(workflow.steps, 1):
            condition_str = f" [dim](if {step.condition})[/dim]" if step.condition else ""
            console.print(f"  {i}. {step.name} [magenta]({step.type})[/magenta]{condition_str}")

        if workflow.tables:
            console.print("\n[bold]Tables:[/bold]")
            for table_name, table_def in workflow.tables.items():
                cols = ", ".join(c.name for c in table_def.columns)
                console.print(f"  - {table_name}: {cols}")

    schedule = getattr(workflow, "schedule", None)
    if schedule:
        console.print("\n[bold]Schedule:[/bold]")
        console.print(f"  Cron: {schedule.cron}")
        console.print(f"  Timezone: {schedule.timezone}")
        enabled_str = "[green]Yes[/green]" if schedule.enabled else "[red]No[/red]"
        console.print(f"  Enabled: {enabled_str}")

    if workflow.inputs:
        console.print("\n[bold]Inputs:[/bold]")
        for key, value in workflow.inputs.items():
            if wf_type == "yaml":
                # YAML inputs are InputDef objects
                desc = value.description or ""
                default = f" (default: {value.default})" if value.default is not None else ""
                required = " [red]*[/red]" if value.required else ""
                console.print(f"  {key}{required}: {value.type}{default} {desc}")
            else:
                # Agent inputs are simple key-value
                console.print(f"  {key}: {value}")

    if workflow.tags:
        console.print(f"\n[bold]Tags:[/bold] {', '.join(workflow.tags)}")

    if workflow.source_path:
        console.print(f"\n[dim]Source: {workflow.source_path}[/dim]")


@defs_group.command(name="validate")
@click.argument("file", type=click.Path(exists=True), required=False)
@track_command
def defs_validate_cmd(file: Optional[str]):
    """
    Validate workflow file(s).

    If FILE is provided, validates that specific file.
    Otherwise, validates all workflow files.
    """
    from pathlib import Path

    from kurt.workflows.agents.parser import validate_workflow as validate_agent
    from kurt.workflows.registry import validate_all_workflows
    from kurt.workflows.yaml_parser import validate_yaml_workflow

    if file:
        path = Path(file)
        if path.suffix == ".md":
            errors = validate_agent(path)
        elif path.suffix in (".yaml", ".yml"):
            errors = validate_yaml_workflow(path)
        else:
            console.print(f"[red]Unknown file type: {path.suffix}[/red]")
            raise click.Abort()

        if errors:
            console.print("[red]Validation failed:[/red]")
            for err in errors:
                console.print(f"  - {err}")
            raise click.Abort()
        else:
            console.print("[green]✓ Validation passed[/green]")
    else:
        result = validate_all_workflows()

        if result["valid"]:
            console.print(f"[green]Valid: {len(result['valid'])} workflow(s)[/green]")
            for item in result["valid"]:
                console.print(f"  [green]✓[/green] {item['name']} ({item['type']})")

        if result["errors"]:
            console.print("\n[red]Errors:[/red]")
            for err in result["errors"]:
                console.print(f"  {err['file']} ({err['type']}):")
                for e in err["errors"]:
                    console.print(f"    - {e}")

        if not result["valid"] and not result["errors"]:
            console.print("[dim]No workflow files found[/dim]")


@defs_group.command(name="run")
@click.argument("name")
@click.option("--input", "-i", "inputs", multiple=True, help="Input in key=value format")
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground (blocking)")
@track_command
def defs_run_cmd(name: str, inputs: tuple, foreground: bool):
    """
    Run a workflow definition.

    \\b
    Examples:
        kurt workflows defs run my-workflow
        kurt workflows defs run my-workflow --input source_url=https://example.com
        kurt workflows defs run my-workflow --foreground
    """
    from kurt.workflows.registry import get_workflow_type

    # Parse inputs
    input_dict = {}
    for inp in inputs:
        key, _, value = inp.partition("=")
        if not key:
            continue
        try:
            input_dict[key] = json.loads(value)
        except json.JSONDecodeError:
            input_dict[key] = value

    console.print(f"[dim]Running workflow: {name}[/dim]")

    wf_type = get_workflow_type(name)
    if not wf_type:
        console.print(f"[red]Workflow not found: {name}[/red]")
        raise click.Abort()

    try:
        if wf_type == "agent":
            from kurt.workflows.agents.executor import run_definition

            result = run_definition(
                name,
                inputs=input_dict if input_dict else None,
                background=not foreground,
                trigger="manual",
            )
        else:  # yaml
            from kurt.workflows.yaml_executor import run_yaml_definition

            result = run_yaml_definition(
                name,
                inputs=input_dict if input_dict else None,
                background=not foreground,
                trigger="manual",
            )

        if result.get("workflow_id") and not foreground:
            console.print("[green]✓ Workflow started[/green]")
            console.print(f"  Workflow ID: {result['workflow_id']}")
            console.print()
            console.print(
                f"[dim]Monitor with: [cyan]kurt workflows follow {result['workflow_id']}[/cyan][/dim]"
            )
        else:
            console.print("[green]✓ Workflow completed[/green]")
            console.print(f"  Status: {result.get('status')}")

            if wf_type == "agent":
                console.print(f"  Turns: {result.get('turns')}")
                console.print(f"  Tool Calls: {result.get('tool_calls')}")
                console.print(
                    f"  Tokens: {result.get('tokens_in', 0) + result.get('tokens_out', 0):,}"
                )
                console.print(f"  Duration: {result.get('duration_seconds')}s")
            else:
                if "results" in result:
                    console.print(f"  Steps completed: {len(result['results'])}")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error running workflow:[/red] {e}")
        raise click.Abort()


@defs_group.command(name="init")
@click.option(
    "--type",
    "wf_type",
    type=click.Choice(["agent", "yaml", "both"]),
    default="both",
    help="Type of example to create",
)
@track_command
def defs_init_cmd(wf_type: str):
    """
    Initialize the workflows directory with example workflows.
    """
    from kurt.workflows.registry import ensure_workflows_dir

    workflows_dir = ensure_workflows_dir()

    created = []

    # Create agent example
    if wf_type in ("agent", "both"):
        agent_path = workflows_dir / "example-agent.md"
        if not agent_path.exists():
            agent_content = """---
name: example-agent
title: Example Agent Workflow
description: |
  An example workflow demonstrating the agent workflow format.
  Customize this to create your own automated tasks.

agent:
  model: claude-sonnet-4-20250514
  max_turns: 10
  allowed_tools:
    - Bash
    - Read
    - Write
    - Glob

guardrails:
  max_tokens: 100000
  max_tool_calls: 50
  max_time: 300

inputs:
  task: "List files in the current directory"

tags: [example, agent]
---

# Example Agent Workflow

You are running inside an automated workflow. Complete the following task:

**Task:** {{task}}

## Instructions

1. Understand the task requirements
2. Use available tools to complete the task
3. Report your findings

## Output

Provide a summary of what you accomplished.
"""
            agent_path.write_text(agent_content)
            created.append(str(agent_path))

    # Create YAML example
    if wf_type in ("yaml", "both"):
        yaml_path = workflows_dir / "example-pipeline.yaml"
        if not yaml_path.exists():
            yaml_content = """name: example-pipeline
title: Example YAML Pipeline
description: |
  An example YAML workflow demonstrating multi-step pipelines.
  This workflow prepares data, analyzes it with an LLM, and compiles results.

inputs:
  topic:
    type: string
    required: true
    description: Topic to research
  max_results:
    type: integer
    default: 5
    min: 1
    max: 20

tables:
  analysis_results:
    columns:
      - name: id
        type: integer
        primary_key: true
      - name: topic
        type: string
      - name: summary
        type: string
        nullable: true
      - name: keywords
        type: json
        default: []
    indexes:
      - columns: [topic]

steps:
  - name: prepare
    type: python
    code: |
      # Prepare the research context
      result = {
          "topic": inputs["topic"],
          "max_results": inputs["max_results"],
          "prepared_at": str(datetime.now()),
      }

  - name: analyze
    type: llm
    model: claude-sonnet-4-20250514
    prompt: |
      Analyze the following topic and provide a brief summary with keywords:

      Topic: {inputs.topic}

      Return your response as JSON with these fields:
      - summary: A 2-3 sentence summary
      - keywords: A list of 3-5 relevant keywords
    output_schema:
      summary: string
      keywords: list[string]

  - name: report
    type: python
    code: |
      # Compile the final report
      result = {
          "topic": inputs["topic"],
          "summary": steps["analyze"].get("summary", "No summary available"),
          "keywords": steps["analyze"].get("keywords", []),
          "metadata": {
              "prepared_at": steps["prepare"]["prepared_at"],
              "completed_at": str(datetime.now()),
          }
      }

tags: [example, yaml]
"""
            yaml_path.write_text(yaml_content)
            created.append(str(yaml_path))

    if created:
        console.print("[green]✓ Created example workflow(s):[/green]")
        for path in created:
            console.print(f"  - {path}")
        console.print()
        console.print("[dim]Run with:[/dim]")
        if wf_type in ("agent", "both"):
            console.print("[cyan]  kurt workflows defs run example-agent[/cyan]")
        if wf_type in ("yaml", "both"):
            console.print(
                "[cyan]  kurt workflows defs run example-pipeline --input topic='AI safety'[/cyan]"
            )
    else:
        console.print("[dim]Example workflows already exist.[/dim]")

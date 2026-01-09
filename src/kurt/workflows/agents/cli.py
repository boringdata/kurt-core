"""CLI commands for agent-based workflow definitions."""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command

console = Console()


@click.group(name="agents")
def agents_group():
    """
    Manage agent-based workflow definitions.

    \\b
    Agent workflows are defined as Markdown files in workflows/
    (configurable via PATH_WORKFLOWS in kurt.config) and executed
    by Claude Code inside DBOS workflows.

    \\b
    Commands:
      list       List all workflow definitions
      show       Show workflow details
      validate   Validate workflow file(s)
      run        Run a workflow manually
      history    Show run history for a workflow
      init       Initialize with example workflow
    """
    pass


@agents_group.command(name="list")
@click.option("--tag", "-t", help="Filter by tag")
@click.option("--scheduled", is_flag=True, help="Only show scheduled workflows")
@track_command
def list_cmd(tag: str, scheduled: bool):
    """List all workflow definitions."""
    from .registry import list_definitions

    definitions = list_definitions()

    if not definitions:
        console.print("[dim]No workflow definitions found.[/dim]")
        console.print("[dim]Create .md files in workflows/ or run 'kurt agents init'.[/dim]")
        return

    if tag:
        definitions = [d for d in definitions if tag in d.tags]
    if scheduled:
        definitions = [d for d in definitions if d.schedule]

    if not definitions:
        console.print("[dim]No matching workflow definitions found.[/dim]")
        return

    table = Table(title="Agent Workflow Definitions")
    table.add_column("Name", style="cyan")
    table.add_column("Title")
    table.add_column("Schedule")
    table.add_column("Tags")

    for d in definitions:
        schedule_str = "-"
        if d.schedule:
            schedule_str = d.schedule.cron
            if not d.schedule.enabled:
                schedule_str = f"{schedule_str} (disabled)"

        tags = ", ".join(d.tags) if d.tags else "-"
        table.add_row(d.name, d.title, schedule_str, tags)

    console.print(table)


@agents_group.command(name="show")
@click.argument("name")
@track_command
def show_cmd(name: str):
    """Show workflow definition details."""
    from .registry import get_definition

    definition = get_definition(name)
    if not definition:
        console.print(f"[red]Workflow not found: {name}[/red]")
        raise click.Abort()

    console.print()
    console.print(f"[bold cyan]{definition.title}[/bold cyan]")
    console.print(f"[dim]Name: {definition.name}[/dim]")

    if definition.description:
        console.print("\n[bold]Description:[/bold]")
        console.print(definition.description)

    console.print("\n[bold]Agent Config:[/bold]")
    console.print(f"  Model: {definition.agent.model}")
    console.print(f"  Max Turns: {definition.agent.max_turns}")
    console.print(f"  Permission Mode: {definition.agent.permission_mode}")
    console.print(f"  Allowed Tools: {', '.join(definition.agent.allowed_tools)}")

    console.print("\n[bold]Guardrails:[/bold]")
    console.print(f"  Max Tokens: {definition.guardrails.max_tokens:,}")
    console.print(f"  Max Tool Calls: {definition.guardrails.max_tool_calls}")
    console.print(f"  Max Time: {definition.guardrails.max_time}s")

    if definition.schedule:
        console.print("\n[bold]Schedule:[/bold]")
        console.print(f"  Cron: {definition.schedule.cron}")
        console.print(f"  Timezone: {definition.schedule.timezone}")
        enabled_str = "[green]Yes[/green]" if definition.schedule.enabled else "[red]No[/red]"
        console.print(f"  Enabled: {enabled_str}")

    if definition.inputs:
        console.print("\n[bold]Inputs:[/bold]")
        for key, value in definition.inputs.items():
            console.print(f"  {key}: {value}")

    if definition.tags:
        console.print(f"\n[bold]Tags:[/bold] {', '.join(definition.tags)}")

    if definition.source_path:
        console.print(f"\n[dim]Source: {definition.source_path}[/dim]")


@agents_group.command(name="validate")
@click.argument("file", type=click.Path(exists=True), required=False)
@track_command
def validate_cmd(file: str):
    """
    Validate workflow file(s).

    If FILE is provided, validates that specific file.
    Otherwise, validates all workflow files in .kurt/workflows/.
    """
    from .parser import validate_workflow
    from .registry import validate_all

    if file:
        errors = validate_workflow(Path(file))
        if errors:
            console.print("[red]Validation failed:[/red]")
            for err in errors:
                console.print(f"  - {err}")
            raise click.Abort()
        else:
            console.print("[green]✓ Validation passed[/green]")
    else:
        result = validate_all()

        if result["valid"]:
            console.print(f"[green]Valid: {len(result['valid'])} workflow(s)[/green]")
            for name in result["valid"]:
                console.print(f"  [green]✓[/green] {name}")

        if result["errors"]:
            console.print("\n[red]Errors:[/red]")
            for err in result["errors"]:
                console.print(f"  {err['file']}:")
                for e in err["errors"]:
                    console.print(f"    - {e}")

        if not result["valid"] and not result["errors"]:
            console.print("[dim]No workflow files found in .kurt/workflows/[/dim]")


@agents_group.command(name="run")
@click.argument("name")
@click.option("--input", "-i", "inputs", multiple=True, help="Input in key=value format")
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground (blocking)")
@track_command
def run_cmd(name: str, inputs: tuple, foreground: bool):
    """
    Run a workflow definition.

    \\b
    Examples:
        kurt agents run daily-research
        kurt agents run daily-research --input topics='["AI", "ML"]'
        kurt agents run daily-research --foreground
    """
    from .executor import run_definition

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

    try:
        result = run_definition(
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
            console.print(f"  Turns: {result.get('turns')}")
            console.print(f"  Tool Calls: {result.get('tool_calls')}")
            console.print(f"  Tokens: {result.get('tokens_in', 0) + result.get('tokens_out', 0):,}")
            console.print(f"  Duration: {result.get('duration_seconds')}s")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error running workflow:[/red] {e}")
        raise click.Abort()


@agents_group.command(name="history")
@click.argument("name")
@click.option("--limit", "-l", default=20, help="Number of runs to show")
@track_command
def history_cmd(name: str, limit: int):
    """Show run history for a workflow (queries DBOS)."""
    from dbos import DBOS

    from kurt.core import init_dbos

    from .registry import get_definition

    definition = get_definition(name)
    if not definition:
        console.print(f"[red]Workflow not found: {name}[/red]")
        raise click.Abort()

    # Initialize DBOS to query workflow history
    init_dbos()

    try:
        # Query DBOS for workflow runs
        # Note: DBOS API for querying workflows may vary
        runs = DBOS.get_workflows(
            workflow_name="execute_agent_workflow",
            limit=limit * 2,  # Get more to filter
        )

        # Filter by definition name (stored as DBOS event)
        filtered_runs = []
        for run in runs:
            try:
                def_name = DBOS.get_event(run.workflow_id, "definition_name")
                if def_name == name:
                    filtered_runs.append(run)
                    if len(filtered_runs) >= limit:
                        break
            except Exception:
                continue

        if not filtered_runs:
            console.print(f"[dim]No run history found for: {name}[/dim]")
            return

        table = Table(title=f"Run History: {name}")
        table.add_column("Workflow ID")
        table.add_column("Status")
        table.add_column("Trigger")
        table.add_column("Started")
        table.add_column("Turns")
        table.add_column("Tokens")

        for run in filtered_runs:
            status = run.status
            status_color = {
                "SUCCESS": "green",
                "ERROR": "red",
                "PENDING": "yellow",
            }.get(status, "white")

            try:
                trigger = DBOS.get_event(run.workflow_id, "trigger") or "-"
                turns = DBOS.get_event(run.workflow_id, "agent_turns") or 0
                tokens_in = DBOS.get_event(run.workflow_id, "tokens_in") or 0
                tokens_out = DBOS.get_event(run.workflow_id, "tokens_out") or 0
            except Exception:
                trigger = "-"
                turns = 0
                tokens_in = 0
                tokens_out = 0

            table.add_row(
                run.workflow_id[:12] + "...",
                f"[{status_color}]{status}[/{status_color}]",
                trigger,
                run.created_at.strftime("%Y-%m-%d %H:%M") if run.created_at else "-",
                str(turns),
                f"{tokens_in + tokens_out:,}",
            )

        console.print(table)

    except Exception as e:
        console.print(f"[yellow]Warning: Could not query DBOS history: {e}[/yellow]")
        console.print("[dim]Run history requires DBOS to be properly initialized.[/dim]")


@agents_group.command(name="track-tool", hidden=True)
def track_tool_cmd():
    """
    Internal command called by PostToolUse hook.

    Reads tool call JSON from stdin and appends to KURT_TOOL_LOG_FILE.
    This command is not meant to be called directly by users.
    """
    import os
    import sys

    log_file = os.environ.get("KURT_TOOL_LOG_FILE")
    if not log_file:
        sys.exit(0)  # No tracking configured, skip silently

    try:
        data = json.load(sys.stdin)
        record = {
            "tool_name": data.get("tool_name"),
            "tool_use_id": data.get("tool_use_id"),
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass  # Don't fail the hook, Claude should continue

    sys.exit(0)


@agents_group.command(name="init")
@track_command
def init_cmd():
    """
    Initialize the workflows directory with an example workflow.
    """
    from .registry import ensure_workflows_dir

    workflows_dir = ensure_workflows_dir()

    example_path = workflows_dir / "example-workflow.md"
    if example_path.exists():
        console.print(f"[dim]Example workflow already exists: {example_path}[/dim]")
        return

    example_content = """---
name: example-workflow
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

tags: [example]
---

# Example Workflow

You are running inside an automated workflow. Complete the following task:

**Task:** {{task}}

## Instructions

1. Understand the task requirements
2. Use available tools to complete the task
3. Report your findings

## Output

Provide a summary of what you accomplished.
"""

    example_path.write_text(example_content)
    console.print(f"[green]✓ Created example workflow:[/green] {example_path}")
    console.print()
    console.print("[dim]Edit this file to customize your workflow, then run with:[/dim]")
    console.print("[cyan]  kurt agents run example-workflow[/cyan]")

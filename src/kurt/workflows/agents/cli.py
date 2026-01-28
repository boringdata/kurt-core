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
    Agent workflows are defined as Markdown or TOML files in workflows/
    (configurable via PATH_WORKFLOWS in kurt.config) and executed
    by Claude Code with observability tracking.

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

    # Show workflow type
    if definition.is_steps_driven:
        console.print("\n[bold]Workflow Type:[/bold] Steps-driven (DAG)")
        console.print(f"\n[bold]Steps:[/bold] {len(definition.steps)}")
        for step_name, step in definition.steps.items():
            deps = f" (depends: {', '.join(step.depends_on)})" if step.depends_on else ""
            console.print(f"  - {step_name}: type={step.type}{deps}")
    elif definition.agent:
        console.print("\n[bold]Workflow Type:[/bold] Agent-driven")
        console.print("\n[bold]Agent Config:[/bold]")
        console.print(f"  Model: {definition.agent.model}")
        console.print(f"  Max Turns: {definition.agent.max_turns}")
        console.print(f"  Permission Mode: {definition.agent.permission_mode}")
        tools = definition.agent.allowed_tools or []
        console.print(f"  Allowed Tools: {', '.join(tools) if tools else '-'}")

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
@click.argument("name_or_path")
@click.option("--input", "-i", "inputs", multiple=True, help="Input in key=value format")
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground (blocking)")
@track_command
def run_cmd(name_or_path: str, inputs: tuple, foreground: bool):
    """
    Run a workflow definition.

    NAME_OR_PATH can be:
    - A workflow name from the registry (e.g., daily-research)
    - A path to a workflow.md file (e.g., ./my-workflow.md)
    - A path to a workflow directory (e.g., ./my_workflow/)

    \\b
    Examples:
        kurt agents run daily-research
        kurt agents run ./experiments/test-workflow.md
        kurt agents run ./workflows/my_workflow/
        kurt agents run daily-research --input topics='["AI", "ML"]'
        kurt agents run daily-research --foreground
    """
    from .executor import run_definition, run_from_path

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

    # Determine if this is a path or a registry name
    path = Path(name_or_path)
    is_path = path.exists() or "/" in name_or_path or name_or_path.endswith((".md", ".toml"))

    if is_path:
        # Resolve the workflow file path
        if path.is_dir():
            # Try TOML first (preferred), then Markdown
            workflow_path = None
            for ext in [".toml", ".md"]:
                candidate = path / f"workflow{ext}"
                if candidate.exists():
                    workflow_path = candidate
                    break
            if workflow_path is None:
                console.print(f"[red]Error:[/red] No workflow.toml or workflow.md found in {path}")
                raise click.Abort()
        elif path.exists():
            workflow_path = path
        else:
            console.print(f"[red]Error:[/red] Path not found: {name_or_path}")
            raise click.Abort()

        console.print(f"[dim]Running workflow from: {workflow_path}[/dim]")

        try:
            result = run_from_path(
                workflow_path,
                inputs=input_dict if input_dict else None,
                background=not foreground,
                trigger="manual",
            )
        except Exception as e:
            console.print(f"[red]Error running workflow:[/red] {e}")
            raise click.Abort()
    else:
        # Registry-based lookup
        console.print(f"[dim]Running workflow: {name_or_path}[/dim]")

        try:
            result = run_definition(
                name_or_path,
                inputs=input_dict if input_dict else None,
                background=not foreground,
                trigger="manual",
            )
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise click.Abort()
        except Exception as e:
            console.print(f"[red]Error running workflow:[/red] {e}")
            raise click.Abort()

    # Display results
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


@agents_group.command(name="history")
@click.argument("name")
@click.option("--limit", "-l", default=20, help="Number of runs to show")
@track_command
def history_cmd(name: str, limit: int):
    """Show run history for a workflow."""
    import os
    from pathlib import Path

    from kurt.db.dolt import DoltDB

    from .registry import get_definition

    definition = get_definition(name)
    if not definition:
        console.print(f"[red]Workflow not found: {name}[/red]")
        raise click.Abort()

    # Get Dolt database
    dolt_path = os.environ.get("DOLT_PATH", ".")
    db = DoltDB(Path(dolt_path))

    if not db.exists():
        console.print("[dim]No workflow history database found.[/dim]")
        console.print("[dim]Run a workflow first to create the database.[/dim]")
        return

    # Ensure observability tables exist
    try:
        from kurt.db.dolt import check_schema_exists, init_observability_schema

        schema_status = check_schema_exists(db)
        if not schema_status.get("workflow_runs", False):
            console.print("[dim]Initializing workflow tracking tables...[/dim]")
            init_observability_schema(db)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not initialize tables: {e}[/yellow]")

    try:
        # Query workflow_runs for this definition
        # Filter by workflow name pattern (agent:<name> or steps:<name>)
        result = db.query(
            """
            SELECT id, workflow, status, started_at, completed_at, inputs, metadata_json, error
            FROM workflow_runs
            WHERE workflow LIKE ? OR workflow LIKE ?
            ORDER BY started_at DESC
            LIMIT ?
            """,
            [f"agent:{name}", f"steps:{name}", limit],
        )

        if not result.rows:
            console.print(f"[dim]No run history found for: {name}[/dim]")
            return

        table = Table(title=f"Run History: {name}")
        table.add_column("Run ID")
        table.add_column("Status")
        table.add_column("Started")
        table.add_column("Duration")
        table.add_column("Trigger")

        for row in result.rows:
            run_id = row.get("id", "")[:12] + "..."
            status = row.get("status", "unknown")
            status_color = {
                "completed": "green",
                "failed": "red",
                "running": "yellow",
                "pending": "dim",
            }.get(status, "white")

            started = row.get("started_at", "-")
            if isinstance(started, str) and len(started) > 16:
                started = started[:16]

            # Calculate duration if completed
            duration = "-"
            if row.get("completed_at") and row.get("started_at"):
                try:
                    from datetime import datetime
                    start = datetime.fromisoformat(row["started_at"].replace("Z", "+00:00"))
                    end = datetime.fromisoformat(row["completed_at"].replace("Z", "+00:00"))
                    dur_secs = (end - start).total_seconds()
                    if dur_secs < 60:
                        duration = f"{dur_secs:.0f}s"
                    else:
                        duration = f"{dur_secs/60:.1f}m"
                except Exception:
                    pass

            # Get trigger from metadata (column is metadata_json)
            trigger = "-"
            metadata = row.get("metadata_json") or row.get("metadata")
            if metadata:
                try:
                    import json
                    meta = json.loads(metadata) if isinstance(metadata, str) else metadata
                    trigger = meta.get("trigger", "-")
                except Exception:
                    pass

            table.add_row(
                run_id,
                f"[{status_color}]{status}[/{status_color}]",
                str(started),
                duration,
                trigger,
            )

        console.print(table)

    except Exception as e:
        console.print(f"[yellow]Warning: Could not query run history: {e}[/yellow]")
        console.print("[dim]Run 'kurt init --force' to reinitialize the database.[/dim]")


@agents_group.command(name="track-tool", hidden=True)
def track_tool_cmd():
    """
    Internal command called by PostToolUse hook.

    Writes tool call events directly to Dolt for real-time monitoring.
    This command is not meant to be called directly by users.

    Claude Code passes:
    - tool_name: The tool that was used (Bash, Read, Write, etc.)
    - tool_use_id: Unique ID for this tool call
    - tool_input: The input parameters passed to the tool
    - tool_result: The result/output from the tool (may be truncated)
    """
    import os
    import sys
    from datetime import datetime

    workflow_id = os.environ.get("KURT_PARENT_WORKFLOW_ID")
    if not workflow_id:
        sys.exit(0)  # No workflow context, skip silently

    try:
        data = json.load(sys.stdin)
        tool_name = data.get("tool_name", "Unknown")

        # Extract tool input summary
        tool_input = data.get("tool_input", {})
        input_summary = None
        if isinstance(tool_input, dict):
            if tool_name == "Bash":
                input_summary = tool_input.get("command", "")[:200]
            elif tool_name == "Read":
                input_summary = tool_input.get("file_path", "")
            elif tool_name == "Write":
                input_summary = tool_input.get("file_path", "")
            elif tool_name == "Edit":
                input_summary = tool_input.get("file_path", "")
            elif tool_name in ("Glob", "Grep"):
                input_summary = tool_input.get("pattern", "")
            elif tool_name == "WebFetch":
                input_summary = tool_input.get("url", "")
            elif tool_name == "WebSearch":
                input_summary = tool_input.get("query", "")
            else:
                # Generic: try to get first string value
                for v in tool_input.values():
                    if isinstance(v, str) and v:
                        input_summary = v[:100]
                        break

        # Extract result summary (truncate long results)
        tool_result = data.get("tool_result") or data.get("result") or data.get("output") or ""
        result_summary = None
        if tool_result:
            if isinstance(tool_result, str):
                result_summary = tool_result[:300] if len(tool_result) > 300 else tool_result
            elif isinstance(tool_result, dict):
                if "content" in tool_result:
                    result_summary = str(tool_result["content"])[:300]
                else:
                    result_summary = str(tool_result)[:300]

        # Write directly to Dolt step_events for real-time monitoring
        from kurt.db.dolt import DoltDB
        from pathlib import Path

        db = DoltDB(Path.cwd())
        metadata_json = json.dumps({
            "tool_name": tool_name,
            "tool_use_id": data.get("tool_use_id"),
            "input_summary": input_summary,
            "result_summary": result_summary,
        })
        message = f"{tool_name}: {input_summary[:80] if input_summary else ''}"

        db.execute(
            """INSERT INTO step_events (run_id, step_id, substep, status, message, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [workflow_id, "agent_execution", "tool_call", "completed", message, metadata_json]
        )

    except Exception:
        pass  # Don't fail the hook, Claude should continue

    sys.exit(0)


@agents_group.command(name="init")
@track_command
def init_cmd():
    """
    Initialize the workflows directory with example workflows.

    Creates both TOML and Markdown examples to demonstrate both formats.
    """
    from .registry import ensure_workflows_dir

    workflows_dir = ensure_workflows_dir()

    # Create TOML example (new format)
    toml_path = workflows_dir / "example-workflow.toml"
    if not toml_path.exists():
        toml_content = '''[workflow]
name = "example-workflow"
title = "Example Agent Workflow (TOML)"
description = "An example workflow demonstrating the TOML format."

[agent]
model = "claude-sonnet-4-20250514"
max_turns = 10
allowed_tools = ["Bash", "Read", "Write", "Glob"]
permission_mode = "bypassPermissions"
prompt = """
You are running inside an automated workflow. Complete the following task:

**Task:** {{task}}

## Instructions

1. Understand the task requirements
2. Use available tools to complete the task
3. Report your findings

## Output

Provide a summary of what you accomplished.
"""

[guardrails]
max_tokens = 100000
max_tool_calls = 50
max_time = 300

[inputs]
task = "List files in the current directory"

tags = ["example", "toml"]
'''
        toml_path.write_text(toml_content)
        console.print(f"[green]✓ Created TOML example:[/green] {toml_path}")
    else:
        console.print(f"[dim]TOML example already exists: {toml_path}[/dim]")

    # Create Markdown example (legacy format, still supported)
    md_path = workflows_dir / "example-workflow-md.md"
    if not md_path.exists():
        md_content = """---
name: example-workflow-md
title: Example Agent Workflow (Markdown)
description: |
  An example workflow demonstrating the Markdown format.
  TOML format is now preferred for new workflows.

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

tags: [example, markdown]
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
        md_path.write_text(md_content)
        console.print(f"[green]✓ Created Markdown example:[/green] {md_path}")
    else:
        console.print(f"[dim]Markdown example already exists: {md_path}[/dim]")

    console.print()
    console.print("[dim]Run workflows with:[/dim]")
    console.print("[cyan]  kurt agents run example-workflow[/cyan]")


@agents_group.command(name="create")
@click.option("--name", "-n", required=True, help="Workflow name (kebab-case)")
@click.option("--title", "-t", help="Display title (defaults to name)")
@click.option("--with-steps", is_flag=True, help="Create step-driven workflow with DAG steps")
@click.option("--with-tools", is_flag=True, help="Create directory structure with tools.py and models.py")
@track_command
def create_cmd(name: str, title: str, with_steps: bool, with_tools: bool):
    """
    Create a new workflow definition (generates .toml format).

    Creates either a simple flat file or a directory structure with
    tools.py and models.py for complex workflows.
    """
    from .registry import ensure_workflows_dir

    workflows_dir = ensure_workflows_dir()
    display_title = title or name.replace("-", " ").title()

    if with_tools or with_steps:
        # Create directory structure
        dir_name = name.replace("-", "_")
        workflow_dir = workflows_dir / dir_name
        workflow_dir.mkdir(exist_ok=True)
        workflow_path = workflow_dir / "workflow.toml"

        if with_steps:
            # Step-driven workflow template
            content = f'''[workflow]
name = "{name}"
title = "{display_title}"
description = "Step-driven workflow with DAG orchestration."

[inputs]
# Add your default inputs here

[steps.fetch]
type = "function"
function = "fetch_data"

[steps.process]
type = "agent"
depends_on = ["fetch"]
max_turns = 15
prompt = """
Process the fetched data from {{{{outputs.fetch}}}}.

Use kurt agent tool commands to save results:
```bash
kurt agent tool save-to-db --table=results --data='{{"key": "value"}}'
```
"""

[steps.finalize]
type = "function"
depends_on = ["process"]
function = "generate_output"

tags = ["steps-driven"]
'''
        else:
            # Agent-driven workflow template with tools
            content = f'''[workflow]
name = "{name}"
title = "{display_title}"
description = "Agent workflow with custom tools."

[agent]
model = "claude-sonnet-4-20250514"
max_turns = 20
allowed_tools = ["Bash", "Read", "Write", "Glob"]
permission_mode = "bypassPermissions"
prompt = """
Complete the task using available tools.

Custom tools from tools.py are available via Python import:
```python
from workflows.{dir_name}.tools import your_function
result = your_function(args)
```
"""

[guardrails]
max_tokens = 150000
max_tool_calls = 100
max_time = 600

[inputs]
# Add your default inputs here

tags = ["custom-tools"]
'''

        workflow_path.write_text(content)
        console.print(f"[green]✓ Created workflow:[/green] {workflow_path}")

        # Create tools.py
        tools_path = workflow_dir / "tools.py"
        if not tools_path.exists():
            tools_content = '''"""Custom functions for this workflow."""


def fetch_data(context: dict) -> dict:
    """Fetch data from sources.

    Args:
        context: Workflow context with inputs and outputs

    Returns:
        Fetched data
    """
    inputs = context.get("inputs", {})
    # Add your data fetching logic here
    return {"data": [], "count": 0}


def generate_output(context: dict) -> dict:
    """Generate final output.

    Args:
        context: Workflow context with inputs and outputs

    Returns:
        Output result
    """
    outputs = context.get("outputs", {})
    # Add your output generation logic here
    return {"status": "completed", "message": "Output generated"}
'''
            tools_path.write_text(tools_content)
            console.print(f"[green]✓ Created tools.py:[/green] {tools_path}")

        # Create models.py
        models_path = workflow_dir / "models.py"
        if not models_path.exists():
            models_content = '''"""SQLModel tables for this workflow."""

from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON


class WorkflowResult(SQLModel, table=True):
    """Results from this workflow."""

    __tablename__ = "results"

    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: str = Field(index=True)
    key: str
    value: str
    metadata: Optional[dict] = Field(default=None, sa_column=Column(JSON))
'''
            models_path.write_text(models_content)
            console.print(f"[green]✓ Created models.py:[/green] {models_path}")

    else:
        # Create simple flat file
        workflow_path = workflows_dir / f"{name}.toml"

        content = f'''[workflow]
name = "{name}"
title = "{display_title}"
description = "Add your workflow description here."

[agent]
model = "claude-sonnet-4-20250514"
max_turns = 15
allowed_tools = ["Bash", "Read", "Write", "Glob"]
permission_mode = "bypassPermissions"
prompt = """
Complete the following task:

{{{{task}}}}

Report your findings when done.
"""

[guardrails]
max_tokens = 100000
max_tool_calls = 50
max_time = 300

[inputs]
task = "Describe your task here"

tags = []
'''
        workflow_path.write_text(content)
        console.print(f"[green]✓ Created workflow:[/green] {workflow_path}")

    console.print()
    console.print("[dim]Validate and run with:[/dim]")
    console.print(f"[cyan]  kurt agents validate {workflow_path}[/cyan]")
    console.print(f"[cyan]  kurt agents run {name}[/cyan]")



"""
Shared CLI utilities for workflow commands.

Provides reusable Click options, output formatters, and helper functions
used across workflow CLIs (agents, TOML workflows, etc.).
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

import click
from rich.console import Console
from rich.table import Table

# Shared console instance
console = Console()


# ============================================================================
# Type Enums
# ============================================================================


class OutputFormat(str, Enum):
    """Output format options."""

    JSON = "json"
    TEXT = "text"
    TABLE = "table"


class StatusColor(str, Enum):
    """Status to color mappings."""

    COMPLETED = "green"
    SUCCESS = "green"
    RUNNING = "yellow"
    PENDING = "dim"
    FAILED = "red"
    ERROR = "red"
    CANCELED = "yellow"
    CANCELING = "yellow"


# ============================================================================
# Click Options
# ============================================================================


def foreground_option(f):
    """Add --foreground/-f option for blocking execution."""
    return click.option(
        "--foreground",
        "-f",
        is_flag=True,
        help="Run in foreground (blocking)",
    )(f)


def input_option(f):
    """Add --input/-i option for key=value inputs (multiple)."""
    return click.option(
        "--input",
        "-i",
        "inputs",
        multiple=True,
        help="Input in key=value format (can specify multiple)",
    )(f)


def tag_option(f):
    """Add --tag/-t option for filtering by tag."""
    return click.option(
        "--tag",
        "-t",
        help="Filter by tag",
    )(f)


def scheduled_option(f):
    """Add --scheduled flag for filtering scheduled workflows."""
    return click.option(
        "--scheduled",
        is_flag=True,
        help="Only show scheduled workflows",
    )(f)


def workflow_format_option(f):
    """Add --format option for workflow output (json/text)."""
    return click.option(
        "--format",
        "output_format",
        type=click.Choice(["json", "text"], case_sensitive=False),
        default="text",
        help="Output format",
    )(f)


def add_workflow_list_options():
    """
    Decorator to add standard workflow list options.

    Adds: --tag, --scheduled

    Usage:
        @click.command()
        @add_workflow_list_options()
        def list_cmd(tag, scheduled):
            ...
    """

    def decorator(f):
        f = scheduled_option(f)
        f = tag_option(f)
        return f

    return decorator


def add_workflow_run_options():
    """
    Decorator to add standard workflow run options.

    Adds: --input, --foreground

    Usage:
        @click.command()
        @add_workflow_run_options()
        def run_cmd(inputs, foreground):
            ...
    """

    def decorator(f):
        f = foreground_option(f)
        f = input_option(f)
        return f

    return decorator


# ============================================================================
# Input Parsing
# ============================================================================


def parse_input_value(value: str) -> Any:
    """
    Parse an input value with type coercion.

    Handles:
    - JSON values (arrays, objects, booleans)
    - "true"/"false" -> bool
    - integers -> int
    - floats -> float
    - everything else -> string

    Args:
        value: The string value to parse

    Returns:
        Parsed value with appropriate type
    """
    # Try JSON first (handles arrays, objects, booleans)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        pass

    # Boolean strings
    if value.lower() == "true":
        return True
    elif value.lower() == "false":
        return False

    # Integer
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return int(value)

    # Float
    try:
        return float(value)
    except ValueError:
        pass

    # String
    return value


def parse_inputs(inputs: tuple[str, ...]) -> dict[str, Any]:
    """
    Parse multiple key=value inputs into a dictionary.

    Args:
        inputs: Tuple of "key=value" strings

    Returns:
        Dictionary of parsed inputs

    Raises:
        click.BadParameter: If any input is not in key=value format.

    Example:
        >>> parse_inputs(("topic=AI", 'tags=["a","b"]', "count=5"))
        {"topic": "AI", "tags": ["a", "b"], "count": 5}
    """
    result: dict[str, Any] = {}
    for inp in inputs:
        if "=" not in inp:
            raise click.BadParameter(f"Input must be in key=value format: {inp}")
        key, _, value = inp.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        result[key] = parse_input_value(value)
    return result


def validate_input_format(ctx, param, value: str) -> tuple[str, Any]:
    """
    Click callback to validate and parse key=value input.

    Usage:
        @click.option("--input", callback=validate_input_format)
    """
    if "=" not in value:
        raise click.BadParameter(f"Input must be in key=value format: {value}")

    key, _, val = value.partition("=")
    return key.strip(), parse_input_value(val.strip())


# ============================================================================
# Output Formatting
# ============================================================================


def print_json_output(data: Any) -> None:
    """
    Print data as formatted JSON.

    Args:
        data: Data to serialize and print
    """
    print(json.dumps(data, indent=2, default=str))


def print_error(message: str, hint: str | None = None) -> None:
    """
    Print an error message with optional hint.

    Args:
        message: The error message
        hint: Optional hint/suggestion for the user
    """
    console.print(f"[red]Error:[/red] {message}")
    if hint:
        console.print(f"[dim]{hint}[/dim]")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]Warning:[/yellow] {message}")


def print_success(message: str) -> None:
    """Print a success message with checkmark."""
    console.print(f"[green]\u2713[/green] {message}")


def print_info(message: str) -> None:
    """Print an info message (dimmed)."""
    console.print(f"[dim]{message}[/dim]")


def format_status(status: str) -> str:
    """
    Format a status string with appropriate color.

    Args:
        status: Status string (completed, running, failed, etc.)

    Returns:
        Rich-formatted status string
    """
    status_lower = status.lower()

    color_map = {
        "completed": "green",
        "success": "green",
        "running": "yellow",
        "pending": "dim",
        "failed": "red",
        "error": "red",
        "canceled": "yellow",
        "canceling": "yellow",
    }

    color = color_map.get(status_lower, "white")
    return f"[{color}]{status}[/{color}]"


def format_duration(seconds: float | int | None) -> str:
    """
    Format duration in human-readable form.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "10s", "2.5m", "1.2h"
    """
    if seconds is None:
        return "-"

    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    else:
        return f"{seconds / 3600:.1f}h"


def format_count(count: int | None) -> str:
    """Format a count with thousands separators."""
    if count is None:
        return "-"
    return f"{count:,}"


# ============================================================================
# Table Helpers
# ============================================================================


def create_workflow_table(title: str | None = None) -> Table:
    """
    Create a standard workflow list table.

    Returns a Rich Table with standard columns for workflow listings.
    """
    table = Table(title=title)
    table.add_column("Name", style="cyan")
    table.add_column("Title")
    table.add_column("Schedule")
    table.add_column("Tags")
    return table


def create_status_table(title: str | None = None) -> Table:
    """
    Create a status table (no box, minimal styling).

    Useful for step logs, run history, etc.
    """
    table = Table(title=title, box=None, show_edge=False)
    return table


def create_run_history_table(title: str | None = None) -> Table:
    """
    Create a table for workflow run history.

    Standard columns: Run ID, Status, Started, Duration, Trigger
    """
    table = Table(title=title)
    table.add_column("Run ID")
    table.add_column("Status")
    table.add_column("Started")
    table.add_column("Duration")
    table.add_column("Trigger")
    return table


# ============================================================================
# Workflow Display Helpers
# ============================================================================


def display_workflow_started(workflow_id: str, follow_cmd: str | None = None) -> None:
    """
    Display workflow started message.

    Args:
        workflow_id: The workflow ID
        follow_cmd: Optional command to follow progress
    """
    print_success("Workflow started")
    console.print(f"  Workflow ID: {workflow_id}")
    console.print()
    if follow_cmd:
        console.print(f"[dim]Monitor with: [cyan]{follow_cmd}[/cyan][/dim]")


def display_workflow_completed(
    status: str,
    turns: int | None = None,
    tool_calls: int | None = None,
    tokens: int | None = None,
    duration_seconds: float | None = None,
) -> None:
    """
    Display workflow completed message with stats.

    Args:
        status: Final status
        turns: Number of conversation turns (agent workflows)
        tool_calls: Number of tool invocations
        tokens: Total tokens (in + out)
        duration_seconds: Execution duration
    """
    print_success("Workflow completed")
    console.print(f"  Status: {status}")
    if turns is not None:
        console.print(f"  Turns: {turns}")
    if tool_calls is not None:
        console.print(f"  Tool Calls: {tool_calls}")
    if tokens is not None:
        console.print(f"  Tokens: {format_count(tokens)}")
    if duration_seconds is not None:
        console.print(f"  Duration: {format_duration(duration_seconds)}")


def display_not_found(entity: str, name: str) -> None:
    """
    Display "not found" error and abort.

    Args:
        entity: What wasn't found (e.g., "Workflow", "Definition")
        name: The name/id that wasn't found
    """
    console.print(f"[red]{entity} not found: {name}[/red]")
    raise click.Abort()


def display_empty_result(message: str, hint: str | None = None) -> None:
    """
    Display empty result message.

    Args:
        message: The "no results" message
        hint: Optional hint for what to do
    """
    console.print(f"[dim]{message}[/dim]")
    if hint:
        console.print(f"[dim]{hint}[/dim]")


# ============================================================================
# Validation Helpers
# ============================================================================


def display_validation_success(message: str = "Validation passed") -> None:
    """Display validation success."""
    console.print(f"[green]\u2713 {message}[/green]")


def display_validation_errors(errors: list[str], header: str = "Validation failed:") -> None:
    """
    Display validation errors.

    Args:
        errors: List of error messages
        header: Header text
    """
    console.print(f"[red]{header}[/red]")
    for err in errors:
        console.print(f"  - {err}")
    raise click.Abort()

"""Decorators for tracking CLI command execution."""

import functools
import time
from typing import Callable

import click

from kurt.admin.telemetry.tracker import track_event


def track_command(func: Callable) -> Callable:
    """Decorator to track CLI command execution.

    Tracks:
    - command_started: When command begins
    - command_completed: When command succeeds
    - command_failed: When command raises an exception

    Properties tracked:
    - command: Full command path (e.g., "kurt ingest fetch")
    - duration_ms: Execution time in milliseconds
    - exit_code: 0 for success, 1 for error
    - error_type: Exception class name (if failed)

    Usage:
        @click.command()
        @track_command
        def my_command():
            # command implementation
            pass

    Args:
        func: Click command function to track

    Returns:
        Wrapped function with telemetry
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get command name from Click context
        ctx = click.get_current_context()
        command_path = _get_command_path(ctx)

        # Track command start
        start_time = time.time()
        track_event(
            "command_started",
            properties={
                "command": command_path,
            },
        )

        try:
            # Execute command
            result = func(*args, **kwargs)

            # Track success
            duration_ms = (time.time() - start_time) * 1000
            track_event(
                "command_completed",
                properties={
                    "command": command_path,
                    "duration_ms": round(duration_ms, 2),
                    "exit_code": 0,
                },
            )

            return result

        except Exception as e:
            # Track failure
            duration_ms = (time.time() - start_time) * 1000
            track_event(
                "command_failed",
                properties={
                    "command": command_path,
                    "duration_ms": round(duration_ms, 2),
                    "exit_code": 1,
                    "error_type": type(e).__name__,
                },
            )
            # Re-raise exception
            raise

    return wrapper


def _get_command_path(ctx: click.Context) -> str:
    """Get full command path from Click context.

    Args:
        ctx: Click context

    Returns:
        Command path like "kurt ingest fetch"
    """
    parts = []

    # Walk up context chain to get full command path
    while ctx:
        if ctx.info_name:
            parts.insert(0, ctx.info_name)
        ctx = ctx.parent

    return " ".join(parts)

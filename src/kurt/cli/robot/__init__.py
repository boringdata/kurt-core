"""Robot mode CLI utilities for AI agent integration.

Provides beads-style JSON output with hybrid activation:
- Explicit --json flag triggers JSON output
- Piped output auto-detects JSON mode (not TTY)
- Error envelope includes actionable hints

Example usage:
    from kurt.cli.robot import OutputContext, robot_success, robot_error, ErrorCode

    # In a Click command
    @click.pass_context
    def my_command(ctx):
        output: OutputContext = ctx.obj.get("output", OutputContext())

        if output.json_mode:
            print(robot_success({"count": 42}))
        else:
            console.print("[green]Found 42 items[/green]")
"""

from .context import OutputContext, is_json_mode, is_tty
from .output import ErrorCode, robot_error, robot_success

__all__ = [
    "OutputContext",
    "is_json_mode",
    "is_tty",
    "robot_success",
    "robot_error",
    "ErrorCode",
]

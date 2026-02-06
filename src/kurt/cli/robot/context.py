"""Output context for mode-aware CLI output (beads pattern).

The OutputContext class provides hybrid activation for JSON mode:
1. Explicit --json flag triggers JSON output
2. Piped output (not TTY) auto-detects JSON mode
3. --quiet flag for minimal output

This follows the beads_rust pattern:
    use_json = json_flag || !stdout.is_terminal()
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any


class OutputContext:
    """Mode-aware output context (like beads OutputContext).

    Determines output mode based on:
    1. Explicit --json flag
    2. TTY detection (piped = JSON)
    3. --quiet flag for minimal output

    Example:
        ctx = OutputContext(json_flag=True)
        if ctx.json_mode:
            ctx.print_success({"count": 42})
        elif ctx.use_rich:
            console.print("[green]42 items[/green]")
        else:
            print("42 items")
    """

    def __init__(self, json_flag: bool = False, quiet: bool = False):
        """Initialize output context.

        Args:
            json_flag: Explicit --json flag from CLI
            quiet: Minimal output mode (--quiet flag)
        """
        self._json_flag = json_flag
        self._quiet = quiet

    @property
    def json_mode(self) -> bool:
        """JSON output if --json flag OR stdout is piped.

        This is the key beads pattern: agents piping output
        automatically get JSON without needing to remember the flag.
        """
        return self._json_flag or not sys.stdout.isatty()

    @property
    def quiet(self) -> bool:
        """Minimal output mode."""
        return self._quiet

    @property
    def use_rich(self) -> bool:
        """Use Rich formatting only if TTY, not quiet, not JSON.

        Returns True when:
        - stdout is a TTY (interactive terminal)
        - not in quiet mode
        - not in JSON mode (explicit flag)
        - NO_COLOR env var not set
        """
        return (
            sys.stdout.isatty()
            and not self._quiet
            and not self._json_flag
            and not os.environ.get("NO_COLOR")
        )

    def print_success(self, data: Any, **metadata) -> None:
        """Print success response (JSON mode only).

        Args:
            data: Response data (dict, list, or primitive)
            **metadata: Optional metadata (duration_ms, count, etc.)
        """
        if self.json_mode:
            response: dict[str, Any] = {"success": True, "data": data}
            if metadata:
                response["metadata"] = metadata
            print(json.dumps(response, default=str))

    def print_error(
        self,
        code: str,
        message: str,
        hint: str | None = None,
        retryable: bool = False,
        exit_code: int = 1,
        **context: Any,
    ) -> None:
        """Print error response (JSON mode only).

        Args:
            code: Error code (SCREAMING_SNAKE_CASE)
            message: Human-readable error message
            hint: Actionable remediation hint
            retryable: Whether the operation can be retried
            exit_code: CLI exit code
            **context: Additional context for debugging
        """
        if self.json_mode:
            error: dict[str, Any] = {
                "code": code,
                "message": message,
            }
            if hint:
                error["hint"] = hint
            if retryable:
                error["retryable"] = retryable
            if context:
                error["context"] = context

            print(
                json.dumps(
                    {"success": False, "error": error, "exit_code": exit_code},
                    default=str,
                )
            )


def is_json_mode(json_flag: bool = False) -> bool:
    """Check if JSON mode is active (flag or piped).

    Args:
        json_flag: Explicit --json flag from CLI

    Returns:
        True if JSON output should be used
    """
    return json_flag or not sys.stdout.isatty()


def is_tty() -> bool:
    """Check if stdout is a TTY (interactive terminal)."""
    return sys.stdout.isatty()

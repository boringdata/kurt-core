"""JSON output formatters for robot mode (beads-style).

Provides structured JSON output with:
- Success envelope: {"success": true, "data": {...}, "metadata": {...}}
- Error envelope: {"success": false, "error": {...}, "exit_code": N}

Error envelopes include actionable hints for agents:
- code: SCREAMING_SNAKE_CASE error code for switching
- message: Human-readable error message
- hint: Actionable remediation (e.g., "Run: kurt docs list")
- retryable: Whether retry might succeed
- context: Debug information
"""

from __future__ import annotations

import json
from typing import Any


class ErrorCode:
    """Standard error codes for robot mode (SCREAMING_SNAKE_CASE).

    Agents can switch on these codes to handle errors programmatically.
    """

    NOT_FOUND = "NOT_FOUND"
    """Resource doesn't exist."""

    INVALID_ARGS = "INVALID_ARGS"
    """Bad or missing arguments."""

    CONFIG_ERROR = "CONFIG_ERROR"
    """Configuration file missing or invalid."""

    EXEC_ERROR = "EXEC_ERROR"
    """Execution or runtime error."""

    NETWORK_ERROR = "NETWORK_ERROR"
    """Network or API failure."""

    NOT_INITIALIZED = "NOT_INITIALIZED"
    """Project not initialized (run: kurt init)."""

    PERMISSION_DENIED = "PERMISSION_DENIED"
    """Access denied."""

    CONFLICT = "CONFLICT"
    """Resource conflict (e.g., already exists)."""

    TIMEOUT = "TIMEOUT"
    """Operation timed out."""


def robot_success(data: Any, **metadata: Any) -> str:
    """Format success JSON response.

    Args:
        data: The response data (dict, list, or primitive)
        **metadata: Optional metadata (duration_ms, count, etc.)

    Returns:
        JSON string with success envelope

    Example:
        >>> robot_success({"docs": 42}, count=42)
        '{"success": true, "data": {"docs": 42}, "metadata": {"count": 42}}'
    """
    response: dict[str, Any] = {"success": True, "data": data}
    if metadata:
        response["metadata"] = metadata
    return json.dumps(response, default=str)


def robot_error(
    code: str,
    message: str,
    hint: str | None = None,
    retryable: bool = False,
    exit_code: int = 1,
    **context: Any,
) -> str:
    """Format error JSON response (beads-style envelope).

    Args:
        code: Error code (SCREAMING_SNAKE_CASE, e.g., NOT_FOUND)
        message: Human-readable error message
        hint: Actionable remediation hint (e.g., "Run: kurt docs list")
        retryable: Whether the operation can be retried
        exit_code: Exit code for the CLI
        **context: Additional context for debugging

    Returns:
        JSON string with error envelope

    Example:
        >>> robot_error(
        ...     ErrorCode.NOT_FOUND,
        ...     "Document abc123 not found",
        ...     hint="Run: kurt docs list",
        ... )
        '{"success": false, "error": {"code": "NOT_FOUND", "message": "...", "hint": "..."}, "exit_code": 1}'
    """
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

    return json.dumps(
        {"success": False, "error": error, "exit_code": exit_code},
        default=str,
    )

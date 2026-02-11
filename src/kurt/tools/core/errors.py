"""
Tool system error taxonomy.

Defines a hierarchy of exceptions for tool execution errors,
enabling structured error handling and reporting.
"""

from __future__ import annotations

from typing import Any


class ToolError(Exception):
    """Base exception for all tool errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ToolNotFoundError(ToolError):
    """Raised when a tool name is not found in the registry."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(
            f"Tool not found: '{tool_name}'",
            details={"tool_name": tool_name},
        )
        self.tool_name = tool_name


class ToolConfigError(ToolError):
    """Raised when tool configuration is invalid (Pydantic validation failure)."""

    def __init__(
        self,
        tool_name: str,
        message: str,
        validation_errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            f"Invalid configuration for tool '{tool_name}': {message}",
            details={
                "tool_name": tool_name,
                "validation_errors": validation_errors or [],
            },
        )
        self.tool_name = tool_name
        self.validation_errors = validation_errors or []


class ToolInputError(ToolError):
    """Raised when input data does not match the expected schema."""

    def __init__(
        self,
        tool_name: str,
        message: str,
        validation_errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            f"Invalid input for tool '{tool_name}': {message}",
            details={
                "tool_name": tool_name,
                "validation_errors": validation_errors or [],
            },
        )
        self.tool_name = tool_name
        self.validation_errors = validation_errors or []


class ToolExecutionError(ToolError):
    """Raised when a tool fails during execution."""

    def __init__(
        self,
        tool_name: str,
        message: str,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(
            f"Execution failed for tool '{tool_name}': {message}",
            details={
                "tool_name": tool_name,
                "cause_type": type(cause).__name__ if cause else None,
                "cause_message": str(cause) if cause else None,
            },
        )
        self.tool_name = tool_name
        self.cause = cause


class ToolTimeoutError(ToolError):
    """Raised when tool execution exceeds the allowed timeout."""

    def __init__(
        self,
        tool_name: str,
        timeout_seconds: float,
        elapsed_seconds: float | None = None,
    ) -> None:
        msg = f"Tool '{tool_name}' timed out after {timeout_seconds}s"
        if elapsed_seconds is not None:
            msg += f" (elapsed: {elapsed_seconds:.2f}s)"
        super().__init__(
            msg,
            details={
                "tool_name": tool_name,
                "timeout_seconds": timeout_seconds,
                "elapsed_seconds": elapsed_seconds,
            },
        )
        self.tool_name = tool_name
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds


class ToolCanceledError(ToolError):
    """Raised when tool execution is canceled by user or system."""

    def __init__(
        self,
        tool_name: str,
        reason: str | None = None,
    ) -> None:
        msg = f"Tool '{tool_name}' was canceled"
        if reason:
            msg += f": {reason}"
        super().__init__(
            msg,
            details={
                "tool_name": tool_name,
                "reason": reason,
            },
        )
        self.tool_name = tool_name
        self.reason = reason


class ProviderNotFoundError(ToolError):
    """Raised when a provider is not found for a tool."""

    def __init__(
        self,
        tool_name: str,
        provider_name: str,
        available: list[str] | None = None,
    ) -> None:
        self.tool_name = tool_name
        self.provider_name = provider_name
        self.available = available or []

        msg = f"Provider '{provider_name}' not found for tool '{tool_name}'"
        if self.available:
            msg += f"\n\nAvailable providers: {', '.join(self.available)}"
        msg += f"\n\nHint: Run 'kurt tool providers {tool_name}' to see all providers"

        super().__init__(
            msg,
            details={
                "tool_name": tool_name,
                "provider_name": provider_name,
                "available": self.available,
            },
        )


class ProviderRequirementsError(ToolError):
    """Raised when a provider's required environment variables are missing."""

    def __init__(
        self,
        provider_name: str,
        missing: list[str],
        tool_name: str | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.missing = missing
        self.tool_name = tool_name

        msg = f"Provider '{provider_name}' missing required environment variables: {', '.join(missing)}"
        msg += "\n\nSet these environment variables before use."

        super().__init__(
            msg,
            details={
                "provider_name": provider_name,
                "tool_name": tool_name,
                "missing_env": missing,
            },
        )


class ProviderValidationError(ToolError):
    """Raised when a provider definition is invalid."""

    def __init__(self, provider_name: str, reason: str) -> None:
        self.provider_name = provider_name
        self.reason = reason

        super().__init__(
            f"Invalid provider '{provider_name}': {reason}",
            details={
                "provider_name": provider_name,
                "reason": reason,
            },
        )

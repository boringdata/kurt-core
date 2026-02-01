"""
Tool base interface and core dataclasses.

Defines:
- Tool: Abstract base class for all tools
- ToolContext: Execution context with db, http, llm, settings
- ToolResult: Structured output from tool execution
- SubstepEvent: Progress callback event data
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from httpx import AsyncClient

    # DoltDBProtocol defines the interface for Dolt database operations.
    # The actual DoltDB implementation will be provided in kurt-core-bc5.1.
    from kurt.db.dolt import DoltDBProtocol


# Type variables for generic input/output models
InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


@dataclass
class SubstepEvent:
    """
    Progress event emitted during tool execution.

    Used for real-time UI updates and observability.
    The on_progress callback receives these events synchronously.

    Attributes:
        substep: Name of the current substep (e.g., 'fetch_urls', 'save_content')
        status: Current status ('running', 'progress', 'completed', 'failed')
        current: Progress counter (optional, for progress status)
        total: Total items to process (optional)
        message: Human-readable status message (optional)
        metadata: Tool-specific additional data (optional)
    """

    substep: str
    status: str  # 'running' | 'progress' | 'completed' | 'failed'
    current: int | None = None
    total: int | None = None
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "substep": self.substep,
            "status": self.status,
            "current": self.current,
            "total": self.total,
            "message": self.message,
            "metadata": self.metadata,
        }


@dataclass
class ToolResultError:
    """
    Individual error within a tool result.

    Attributes:
        row_idx: Index of the row that caused the error (None for global errors)
        error_type: Type/category of error
        message: Human-readable error message
        details: Additional error context
    """

    row_idx: int | None
    error_type: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "row_idx": self.row_idx,
            "error_type": self.error_type,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class ToolResultMetadata:
    """
    Execution metadata for a tool result.

    Attributes:
        started_at: ISO timestamp when execution started
        completed_at: ISO timestamp when execution completed
        duration_ms: Total execution time in milliseconds
    """

    started_at: str
    completed_at: str
    duration_ms: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_timestamps(
        cls, started_at: datetime, completed_at: datetime
    ) -> ToolResultMetadata:
        """Create metadata from datetime objects."""
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        return cls(
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            duration_ms=duration_ms,
        )


@dataclass
class ToolResultSubstep:
    """
    Substep summary in a tool result.

    Attributes:
        name: Name of the substep
        status: Final status of the substep
        current: Final progress counter
        total: Total items processed
    """

    name: str
    status: str
    current: int
    total: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "status": self.status,
            "current": self.current,
            "total": self.total,
        }


@dataclass
class ToolResult:
    """
    Structured result from tool execution.

    All tools return this standardized format, enabling consistent
    error handling, progress tracking, and result processing.

    Attributes:
        success: Whether the tool completed successfully
        data: List of output records (OutputModel instances as dicts)
        errors: List of errors encountered during execution
        metadata: Execution timing information
        substeps: Summary of substeps executed
    """

    success: bool
    data: list[dict[str, Any]] = field(default_factory=list)
    errors: list[ToolResultError] = field(default_factory=list)
    metadata: ToolResultMetadata | None = None
    substeps: list[ToolResultSubstep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "data": self.data,
            "errors": [e.to_dict() for e in self.errors],
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "substeps": [s.to_dict() for s in self.substeps],
        }

    def add_error(
        self,
        error_type: str,
        message: str,
        row_idx: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Add an error to the result."""
        self.errors.append(
            ToolResultError(
                row_idx=row_idx,
                error_type=error_type,
                message=message,
                details=details or {},
            )
        )

    def add_substep(
        self,
        name: str,
        status: str,
        current: int = 0,
        total: int = 0,
    ) -> None:
        """Add a substep summary to the result."""
        self.substeps.append(
            ToolResultSubstep(
                name=name,
                status=status,
                current=current,
                total=total,
            )
        )


# Progress callback type
ProgressCallback = Callable[[SubstepEvent], None]


@dataclass
class ToolContext:
    """
    Execution context passed to all tools.

    Provides access to shared resources and configuration
    needed during tool execution.

    Attributes:
        db: Dolt database client for data persistence
        http: Async HTTP client for external requests
        llm: LLM client/configuration (dict or callable)
        settings: Tool-specific settings from config
        tools: Registry of available tools (for tool chaining)
    """

    db: DoltDBProtocol | None = None
    http: AsyncClient | None = None
    llm: dict[str, Any] | None = None
    settings: dict[str, Any] = field(default_factory=dict)
    tools: dict[str, Any] = field(default_factory=dict)


class Tool(ABC, Generic[InputT, OutputT]):
    """
    Abstract base class for all tools.

    Tool implementations define:
    - name: Unique identifier (matches step.type in TOML)
    - description: Human-readable description
    - InputModel: Pydantic model for input validation
    - OutputModel: Pydantic model for output schema
    - run(): Async execution method

    Example:
        class MapTool(Tool[MapInput, MapOutput]):
            name = "map"
            description = "Map URLs to content"
            InputModel = MapInput
            OutputModel = MapOutput

            async def run(
                self,
                params: MapInput,
                context: ToolContext,
                on_progress: ProgressCallback | None = None,
            ) -> ToolResult:
                ...
    """

    # Class attributes - must be defined by subclasses
    name: str
    description: str
    InputModel: type[InputT]
    OutputModel: type[OutputT]

    @abstractmethod
    async def run(
        self,
        params: InputT,
        context: ToolContext,
        on_progress: ProgressCallback | None = None,
    ) -> ToolResult:
        """
        Execute the tool with the given parameters.

        Args:
            params: Validated input parameters (InputModel instance)
            context: Execution context with db, http, llm, etc.
            on_progress: Optional callback for progress events.
                         Called synchronously during execution.
                         Must not raise exceptions (logged and ignored).

        Returns:
            ToolResult with success status, data, errors, and metadata.

        Raises:
            ToolExecutionError: On runtime failures
            ToolTimeoutError: If execution exceeds timeout
            ToolCanceledError: If canceled by user/system
        """
        pass

    def emit_progress(
        self,
        on_progress: ProgressCallback | None,
        substep: str,
        status: str,
        current: int | None = None,
        total: int | None = None,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Emit a progress event if callback is provided.

        Safe to call even if on_progress is None or raises.
        Exceptions from the callback are logged and ignored.

        Args:
            on_progress: Callback to invoke (may be None)
            substep: Name of current substep
            status: Status ('running', 'progress', 'completed', 'failed')
            current: Optional progress counter
            total: Optional total items
            message: Optional human-readable message
            metadata: Optional tool-specific data
        """
        if on_progress is None:
            return

        event = SubstepEvent(
            substep=substep,
            status=status,
            current=current,
            total=total,
            message=message,
            metadata=metadata or {},
        )

        try:
            on_progress(event)
        except Exception:
            # Progress callbacks must not raise - log and continue
            # In production, this would use proper logging
            pass

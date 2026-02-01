"""
Unit tests for tool base classes and dataclasses.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from pydantic import BaseModel

from kurt.tools.core.base import (
    ProgressCallback,
    SubstepEvent,
    Tool,
    ToolContext,
    ToolResult,
    ToolResultError,
    ToolResultMetadata,
    ToolResultSubstep,
)

# ============================================================================
# SubstepEvent Tests
# ============================================================================


class TestSubstepEvent:
    """Test SubstepEvent dataclass."""

    def test_minimal_event(self):
        """Event with only required fields."""
        event = SubstepEvent(substep="fetch_urls", status="running")
        assert event.substep == "fetch_urls"
        assert event.status == "running"
        assert event.current is None
        assert event.total is None
        assert event.message is None
        assert event.metadata == {}

    def test_full_event(self):
        """Event with all fields."""
        event = SubstepEvent(
            substep="save_content",
            status="progress",
            current=5,
            total=10,
            message="Processing items",
            metadata={"batch": 1},
        )
        assert event.substep == "save_content"
        assert event.status == "progress"
        assert event.current == 5
        assert event.total == 10
        assert event.message == "Processing items"
        assert event.metadata == {"batch": 1}

    def test_to_dict(self):
        """to_dict serializes all fields."""
        event = SubstepEvent(
            substep="step1",
            status="completed",
            current=10,
            total=10,
            message="Done",
            metadata={"key": "value"},
        )
        d = event.to_dict()
        assert d == {
            "substep": "step1",
            "status": "completed",
            "current": 10,
            "total": 10,
            "message": "Done",
            "metadata": {"key": "value"},
        }

    def test_to_dict_with_none_values(self):
        """to_dict includes None values."""
        event = SubstepEvent(substep="x", status="running")
        d = event.to_dict()
        assert d["current"] is None
        assert d["total"] is None
        assert d["message"] is None


# ============================================================================
# ToolResultError Tests
# ============================================================================


class TestToolResultError:
    """Test ToolResultError dataclass."""

    def test_global_error(self):
        """Error without row index (global error)."""
        err = ToolResultError(
            row_idx=None,
            error_type="connection_error",
            message="Failed to connect",
        )
        assert err.row_idx is None
        assert err.error_type == "connection_error"
        assert err.message == "Failed to connect"
        assert err.details == {}

    def test_row_error(self):
        """Error with row index."""
        err = ToolResultError(
            row_idx=5,
            error_type="validation_error",
            message="Invalid URL",
            details={"url": "not-a-url"},
        )
        assert err.row_idx == 5
        assert err.error_type == "validation_error"
        assert err.details == {"url": "not-a-url"}

    def test_to_dict(self):
        """to_dict serializes correctly."""
        err = ToolResultError(
            row_idx=3,
            error_type="parse_error",
            message="JSON decode failed",
            details={"position": 42},
        )
        d = err.to_dict()
        assert d == {
            "row_idx": 3,
            "error_type": "parse_error",
            "message": "JSON decode failed",
            "details": {"position": 42},
        }


# ============================================================================
# ToolResultMetadata Tests
# ============================================================================


class TestToolResultMetadata:
    """Test ToolResultMetadata dataclass."""

    def test_basic_metadata(self):
        """Basic metadata creation."""
        meta = ToolResultMetadata(
            started_at="2024-01-15T10:00:00",
            completed_at="2024-01-15T10:00:05",
            duration_ms=5000,
        )
        assert meta.started_at == "2024-01-15T10:00:00"
        assert meta.completed_at == "2024-01-15T10:00:05"
        assert meta.duration_ms == 5000

    def test_to_dict(self):
        """to_dict serializes correctly."""
        meta = ToolResultMetadata(
            started_at="2024-01-15T10:00:00",
            completed_at="2024-01-15T10:00:05",
            duration_ms=5000,
        )
        d = meta.to_dict()
        assert d == {
            "started_at": "2024-01-15T10:00:00",
            "completed_at": "2024-01-15T10:00:05",
            "duration_ms": 5000,
        }

    def test_from_timestamps(self):
        """from_timestamps factory method."""
        start = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 15, 10, 0, 5, 500000, tzinfo=timezone.utc)
        meta = ToolResultMetadata.from_timestamps(start, end)

        assert meta.started_at == start.isoformat()
        assert meta.completed_at == end.isoformat()
        assert meta.duration_ms == 5500  # 5.5 seconds


# ============================================================================
# ToolResultSubstep Tests
# ============================================================================


class TestToolResultSubstep:
    """Test ToolResultSubstep dataclass."""

    def test_basic_substep(self):
        """Basic substep creation."""
        substep = ToolResultSubstep(
            name="fetch",
            status="completed",
            current=10,
            total=10,
        )
        assert substep.name == "fetch"
        assert substep.status == "completed"
        assert substep.current == 10
        assert substep.total == 10

    def test_to_dict(self):
        """to_dict serializes correctly."""
        substep = ToolResultSubstep(
            name="process",
            status="running",
            current=5,
            total=20,
        )
        d = substep.to_dict()
        assert d == {
            "name": "process",
            "status": "running",
            "current": 5,
            "total": 20,
        }


# ============================================================================
# ToolResult Tests
# ============================================================================


class TestToolResult:
    """Test ToolResult dataclass."""

    def test_minimal_success_result(self):
        """Minimal successful result."""
        result = ToolResult(success=True)
        assert result.success is True
        assert result.data == []
        assert result.errors == []
        assert result.metadata is None
        assert result.substeps == []

    def test_full_result(self):
        """Result with all fields populated."""
        meta = ToolResultMetadata(
            started_at="2024-01-15T10:00:00",
            completed_at="2024-01-15T10:00:05",
            duration_ms=5000,
        )
        result = ToolResult(
            success=True,
            data=[{"id": 1, "url": "https://example.com"}],
            errors=[],
            metadata=meta,
            substeps=[
                ToolResultSubstep(name="fetch", status="completed", current=1, total=1)
            ],
        )
        assert result.success is True
        assert len(result.data) == 1
        assert result.metadata is not None

    def test_to_dict(self):
        """to_dict serializes the complete result."""
        meta = ToolResultMetadata(
            started_at="2024-01-15T10:00:00",
            completed_at="2024-01-15T10:00:05",
            duration_ms=5000,
        )
        result = ToolResult(
            success=False,
            data=[{"id": 1}],
            errors=[
                ToolResultError(
                    row_idx=0, error_type="error", message="failed", details={}
                )
            ],
            metadata=meta,
            substeps=[
                ToolResultSubstep(name="step1", status="failed", current=0, total=1)
            ],
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["data"] == [{"id": 1}]
        assert len(d["errors"]) == 1
        assert d["errors"][0]["row_idx"] == 0
        assert d["metadata"]["duration_ms"] == 5000
        assert len(d["substeps"]) == 1

    def test_to_dict_no_metadata(self):
        """to_dict handles None metadata."""
        result = ToolResult(success=True)
        d = result.to_dict()
        assert d["metadata"] is None

    def test_add_error(self):
        """add_error helper method."""
        result = ToolResult(success=True)
        result.add_error(
            error_type="validation",
            message="Invalid input",
            row_idx=5,
            details={"field": "url"},
        )
        assert len(result.errors) == 1
        assert result.errors[0].row_idx == 5
        assert result.errors[0].error_type == "validation"
        assert result.errors[0].details == {"field": "url"}

    def test_add_error_minimal(self):
        """add_error with minimal arguments."""
        result = ToolResult(success=True)
        result.add_error(error_type="error", message="Something failed")
        assert len(result.errors) == 1
        assert result.errors[0].row_idx is None
        assert result.errors[0].details == {}

    def test_add_substep(self):
        """add_substep helper method."""
        result = ToolResult(success=True)
        result.add_substep(name="fetch", status="completed", current=10, total=10)
        assert len(result.substeps) == 1
        assert result.substeps[0].name == "fetch"
        assert result.substeps[0].status == "completed"

    def test_add_substep_defaults(self):
        """add_substep with default values."""
        result = ToolResult(success=True)
        result.add_substep(name="init", status="running")
        assert result.substeps[0].current == 0
        assert result.substeps[0].total == 0


# ============================================================================
# ToolContext Tests
# ============================================================================


class TestToolContext:
    """Test ToolContext dataclass."""

    def test_empty_context(self):
        """Empty context with all defaults."""
        ctx = ToolContext()
        assert ctx.db is None
        assert ctx.http is None
        assert ctx.llm is None
        assert ctx.settings == {}
        assert ctx.tools == {}

    def test_context_with_values(self):
        """Context with some values set."""
        ctx = ToolContext(
            settings={"timeout": 30},
            tools={"map": "MapTool"},
        )
        assert ctx.settings == {"timeout": 30}
        assert ctx.tools == {"map": "MapTool"}

    def test_context_db_type_hint(self):
        """Context accepts db parameter (type checking only at runtime)."""
        # We can't test the actual DoltDB here since it's a future implementation
        # Just verify the attribute exists
        ctx = ToolContext()
        assert hasattr(ctx, "db")


# ============================================================================
# Tool ABC Tests
# ============================================================================


class TestToolABC:
    """Test Tool abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Tool ABC cannot be instantiated without implementing run()."""
        with pytest.raises(TypeError):
            Tool()

    def test_concrete_tool_implementation(self):
        """Concrete tool implementation works."""

        class TestInput(BaseModel):
            value: str

        class TestOutput(BaseModel):
            result: str

        class ConcreteTool(Tool[TestInput, TestOutput]):
            name = "test_tool"
            description = "A test tool"
            InputModel = TestInput
            OutputModel = TestOutput

            async def run(
                self,
                params: TestInput,
                context: ToolContext,
                on_progress: ProgressCallback | None = None,
            ) -> ToolResult:
                return ToolResult(
                    success=True,
                    data=[{"result": f"processed: {params.value}"}],
                )

        tool = ConcreteTool()
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.InputModel is TestInput
        assert tool.OutputModel is TestOutput

    def test_emit_progress_with_callback(self):
        """emit_progress calls callback with SubstepEvent."""

        class TestInput(BaseModel):
            pass

        class TestOutput(BaseModel):
            pass

        class ToolWithProgress(Tool[TestInput, TestOutput]):
            name = "progress_tool"
            description = "Tool with progress"
            InputModel = TestInput
            OutputModel = TestOutput

            async def run(
                self,
                params: TestInput,
                context: ToolContext,
                on_progress: ProgressCallback | None = None,
            ) -> ToolResult:
                self.emit_progress(
                    on_progress,
                    substep="step1",
                    status="running",
                    current=5,
                    total=10,
                    message="Working",
                    metadata={"key": "val"},
                )
                return ToolResult(success=True)

        callback = Mock()
        tool = ToolWithProgress()

        # Manually call emit_progress to test it
        tool.emit_progress(
            callback,
            substep="step1",
            status="progress",
            current=5,
            total=10,
            message="Working",
            metadata={"key": "val"},
        )

        callback.assert_called_once()
        event = callback.call_args[0][0]
        assert isinstance(event, SubstepEvent)
        assert event.substep == "step1"
        assert event.status == "progress"
        assert event.current == 5
        assert event.total == 10
        assert event.message == "Working"
        assert event.metadata == {"key": "val"}

    def test_emit_progress_without_callback(self):
        """emit_progress with None callback doesn't fail."""

        class TestInput(BaseModel):
            pass

        class TestOutput(BaseModel):
            pass

        class ToolWithProgress(Tool[TestInput, TestOutput]):
            name = "progress_tool"
            description = "Tool with progress"
            InputModel = TestInput
            OutputModel = TestOutput

            async def run(
                self,
                params: TestInput,
                context: ToolContext,
                on_progress: ProgressCallback | None = None,
            ) -> ToolResult:
                return ToolResult(success=True)

        tool = ToolWithProgress()
        # Should not raise
        tool.emit_progress(None, substep="step1", status="running")

    def test_emit_progress_callback_exception_ignored(self):
        """emit_progress ignores exceptions from callback."""

        class TestInput(BaseModel):
            pass

        class TestOutput(BaseModel):
            pass

        class ToolWithProgress(Tool[TestInput, TestOutput]):
            name = "progress_tool"
            description = "Tool with progress"
            InputModel = TestInput
            OutputModel = TestOutput

            async def run(
                self,
                params: TestInput,
                context: ToolContext,
                on_progress: ProgressCallback | None = None,
            ) -> ToolResult:
                return ToolResult(success=True)

        def failing_callback(event: SubstepEvent) -> None:
            raise ValueError("Callback failed!")

        tool = ToolWithProgress()
        # Should not raise even though callback raises
        tool.emit_progress(failing_callback, substep="step1", status="running")

    def test_emit_progress_minimal(self):
        """emit_progress with minimal arguments."""

        class TestInput(BaseModel):
            pass

        class TestOutput(BaseModel):
            pass

        class ToolWithProgress(Tool[TestInput, TestOutput]):
            name = "progress_tool"
            description = "Tool with progress"
            InputModel = TestInput
            OutputModel = TestOutput

            async def run(
                self,
                params: TestInput,
                context: ToolContext,
                on_progress: ProgressCallback | None = None,
            ) -> ToolResult:
                return ToolResult(success=True)

        callback = Mock()
        tool = ToolWithProgress()
        tool.emit_progress(callback, substep="init", status="running")

        event = callback.call_args[0][0]
        assert event.substep == "init"
        assert event.status == "running"
        assert event.current is None
        assert event.total is None
        assert event.message is None
        assert event.metadata == {}

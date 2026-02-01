"""
Unit tests for tool registry and execution.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from kurt.tools.core.base import (
    ProgressCallback,
    SubstepEvent,
    Tool,
    ToolContext,
    ToolResult,
)
from kurt.tools.core.errors import (
    ToolExecutionError,
    ToolInputError,
    ToolNotFoundError,
)
from kurt.tools.core.registry import (
    TOOLS,
    clear_registry,
    execute_tool,
    get_tool,
    get_tool_info,
    list_tools,
    register_tool,
)

# ============================================================================
# Test Fixtures and Helper Classes
# ============================================================================


class EchoInput(BaseModel):
    """Input model for echo tool."""

    message: str
    repeat: int = 1


class EchoOutput(BaseModel):
    """Output model for echo tool."""

    echoed: str
    count: int


class EchoTool(Tool[EchoInput, EchoOutput]):
    """Simple echo tool for testing."""

    name = "echo"
    description = "Echoes the input message"
    InputModel = EchoInput
    OutputModel = EchoOutput

    async def run(
        self,
        params: EchoInput,
        context: ToolContext,
        on_progress: ProgressCallback | None = None,
    ) -> ToolResult:
        self.emit_progress(on_progress, substep="echo", status="running")
        result = params.message * params.repeat
        self.emit_progress(on_progress, substep="echo", status="completed")
        return ToolResult(
            success=True,
            data=[{"echoed": result, "count": params.repeat}],
        )


class FailingInput(BaseModel):
    """Input model for failing tool."""

    should_fail: bool = True


class FailingOutput(BaseModel):
    """Output model for failing tool."""

    pass


class FailingTool(Tool[FailingInput, FailingOutput]):
    """Tool that always fails for testing."""

    name = "failing"
    description = "Always fails"
    InputModel = FailingInput
    OutputModel = FailingOutput

    async def run(
        self,
        params: FailingInput,
        context: ToolContext,
        on_progress: ProgressCallback | None = None,
    ) -> ToolResult:
        if params.should_fail:
            raise ValueError("Intentional failure")
        return ToolResult(success=True)


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear the registry before and after each test."""
    clear_registry()
    yield
    clear_registry()


# ============================================================================
# register_tool Tests
# ============================================================================


class TestRegisterTool:
    """Test register_tool decorator."""

    def test_register_tool_decorator(self):
        """register_tool adds tool to TOOLS dict."""

        @register_tool
        class MyTool(Tool[EchoInput, EchoOutput]):
            name = "my_tool"
            description = "My tool"
            InputModel = EchoInput
            OutputModel = EchoOutput

            async def run(self, params, context, on_progress=None):
                return ToolResult(success=True)

        assert "my_tool" in TOOLS
        assert TOOLS["my_tool"] is MyTool

    def test_register_tool_returns_class(self):
        """register_tool returns the class for decorator chaining."""

        @register_tool
        class AnotherTool(Tool[EchoInput, EchoOutput]):
            name = "another"
            description = "Another tool"
            InputModel = EchoInput
            OutputModel = EchoOutput

            async def run(self, params, context, on_progress=None):
                return ToolResult(success=True)

        assert AnotherTool.name == "another"

    def test_register_tool_without_name_raises(self):
        """register_tool raises if tool has no name."""
        with pytest.raises(ValueError, match="must define 'name'"):

            @register_tool
            class NoNameTool(Tool[EchoInput, EchoOutput]):
                description = "No name"
                InputModel = EchoInput
                OutputModel = EchoOutput

                async def run(self, params, context, on_progress=None):
                    return ToolResult(success=True)

    def test_register_tool_empty_name_raises(self):
        """register_tool raises if tool name is empty string."""
        with pytest.raises(ValueError, match="must define 'name'"):

            @register_tool
            class EmptyNameTool(Tool[EchoInput, EchoOutput]):
                name = ""
                description = "Empty name"
                InputModel = EchoInput
                OutputModel = EchoOutput

                async def run(self, params, context, on_progress=None):
                    return ToolResult(success=True)

    def test_register_duplicate_name_raises(self):
        """register_tool raises if name already registered."""

        @register_tool
        class FirstTool(Tool[EchoInput, EchoOutput]):
            name = "duplicate"
            description = "First"
            InputModel = EchoInput
            OutputModel = EchoOutput

            async def run(self, params, context, on_progress=None):
                return ToolResult(success=True)

        with pytest.raises(ValueError, match="already registered"):

            @register_tool
            class SecondTool(Tool[EchoInput, EchoOutput]):
                name = "duplicate"
                description = "Second"
                InputModel = EchoInput
                OutputModel = EchoOutput

                async def run(self, params, context, on_progress=None):
                    return ToolResult(success=True)


# ============================================================================
# get_tool Tests
# ============================================================================


class TestGetTool:
    """Test get_tool function."""

    def test_get_registered_tool(self):
        """get_tool returns registered tool class."""
        TOOLS["echo"] = EchoTool
        tool_class = get_tool("echo")
        assert tool_class is EchoTool

    def test_get_unregistered_tool_raises(self):
        """get_tool raises ToolNotFoundError for unknown tools."""
        with pytest.raises(ToolNotFoundError) as exc_info:
            get_tool("nonexistent")
        assert exc_info.value.tool_name == "nonexistent"


# ============================================================================
# list_tools Tests
# ============================================================================


class TestListTools:
    """Test list_tools function."""

    def test_list_empty_registry(self):
        """list_tools returns empty list for empty registry."""
        assert list_tools() == []

    def test_list_registered_tools(self):
        """list_tools returns sorted list of tool names."""
        TOOLS["zebra"] = EchoTool
        TOOLS["alpha"] = EchoTool
        TOOLS["beta"] = EchoTool
        assert list_tools() == ["alpha", "beta", "zebra"]


# ============================================================================
# get_tool_info Tests
# ============================================================================


class TestGetToolInfo:
    """Test get_tool_info function."""

    def test_get_tool_info(self):
        """get_tool_info returns tool metadata."""
        TOOLS["echo"] = EchoTool
        info = get_tool_info("echo")
        assert info["name"] == "echo"
        assert info["description"] == "Echoes the input message"
        assert "properties" in info["input_schema"]
        assert "properties" in info["output_schema"]

    def test_get_tool_info_not_found(self):
        """get_tool_info raises for unknown tools."""
        with pytest.raises(ToolNotFoundError):
            get_tool_info("unknown")


# ============================================================================
# execute_tool Tests
# ============================================================================


class TestExecuteTool:
    """Test execute_tool function."""

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """execute_tool runs tool and returns result."""
        TOOLS["echo"] = EchoTool
        result = await execute_tool(
            "echo",
            {"message": "hello", "repeat": 3},
        )
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["echoed"] == "hellohellohello"
        assert result.data[0]["count"] == 3

    @pytest.mark.asyncio
    async def test_execute_with_context(self):
        """execute_tool passes context to tool."""
        received_context = None

        class ContextCaptureTool(Tool[EchoInput, EchoOutput]):
            name = "capture"
            description = "Captures context"
            InputModel = EchoInput
            OutputModel = EchoOutput

            async def run(self, params, context, on_progress=None):
                nonlocal received_context
                received_context = context
                return ToolResult(success=True)

        TOOLS["capture"] = ContextCaptureTool
        ctx = ToolContext(settings={"key": "value"})

        await execute_tool("capture", {"message": "test"}, context=ctx)

        assert received_context is ctx
        assert received_context.settings == {"key": "value"}

    @pytest.mark.asyncio
    async def test_execute_creates_default_context(self):
        """execute_tool creates context if not provided."""
        received_context = None

        class ContextCaptureTool(Tool[EchoInput, EchoOutput]):
            name = "capture2"
            description = "Captures context"
            InputModel = EchoInput
            OutputModel = EchoOutput

            async def run(self, params, context, on_progress=None):
                nonlocal received_context
                received_context = context
                return ToolResult(success=True)

        TOOLS["capture2"] = ContextCaptureTool

        await execute_tool("capture2", {"message": "test"})

        assert received_context is not None
        assert isinstance(received_context, ToolContext)

    @pytest.mark.asyncio
    async def test_execute_with_progress_callback(self):
        """execute_tool passes progress callback to tool."""
        TOOLS["echo"] = EchoTool
        events = []

        def on_progress(event: SubstepEvent):
            events.append(event)

        await execute_tool(
            "echo",
            {"message": "test"},
            on_progress=on_progress,
        )

        assert len(events) == 2
        assert events[0].substep == "echo"
        assert events[0].status == "running"
        assert events[1].status == "completed"

    @pytest.mark.asyncio
    async def test_execute_not_found(self):
        """execute_tool raises ToolNotFoundError for unknown tools."""
        with pytest.raises(ToolNotFoundError) as exc_info:
            await execute_tool("unknown", {})
        assert exc_info.value.tool_name == "unknown"

    @pytest.mark.asyncio
    async def test_execute_invalid_input(self):
        """execute_tool raises ToolInputError for invalid params."""
        TOOLS["echo"] = EchoTool
        with pytest.raises(ToolInputError) as exc_info:
            await execute_tool("echo", {"wrong_field": "value"})
        assert exc_info.value.tool_name == "echo"
        assert len(exc_info.value.validation_errors) > 0

    @pytest.mark.asyncio
    async def test_execute_wraps_execution_errors(self):
        """execute_tool wraps exceptions in ToolExecutionError."""
        TOOLS["failing"] = FailingTool
        with pytest.raises(ToolExecutionError) as exc_info:
            await execute_tool("failing", {"should_fail": True})
        assert exc_info.value.tool_name == "failing"
        assert exc_info.value.cause is not None
        assert "Intentional failure" in str(exc_info.value.cause)

    @pytest.mark.asyncio
    async def test_execute_adds_metadata(self):
        """execute_tool adds timing metadata if not present."""
        TOOLS["echo"] = EchoTool
        result = await execute_tool("echo", {"message": "test"})
        assert result.metadata is not None
        assert result.metadata.started_at is not None
        assert result.metadata.completed_at is not None
        assert result.metadata.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_preserves_existing_metadata(self):
        """execute_tool preserves metadata set by tool."""
        from kurt.tools.core.base import ToolResultMetadata

        class MetadataTool(Tool[EchoInput, EchoOutput]):
            name = "meta"
            description = "Sets metadata"
            InputModel = EchoInput
            OutputModel = EchoOutput

            async def run(self, params, context, on_progress=None):
                return ToolResult(
                    success=True,
                    metadata=ToolResultMetadata(
                        started_at="custom",
                        completed_at="custom",
                        duration_ms=999,
                    ),
                )

        TOOLS["meta"] = MetadataTool
        result = await execute_tool("meta", {"message": "test"})
        assert result.metadata.started_at == "custom"
        assert result.metadata.duration_ms == 999

    @pytest.mark.asyncio
    async def test_execute_with_default_values(self):
        """execute_tool uses default values from InputModel."""
        TOOLS["echo"] = EchoTool
        result = await execute_tool("echo", {"message": "test"})
        # repeat defaults to 1
        assert result.data[0]["count"] == 1


# ============================================================================
# clear_registry Tests
# ============================================================================


class TestClearRegistry:
    """Test clear_registry function."""

    def test_clear_registry(self):
        """clear_registry removes all tools."""
        TOOLS["a"] = EchoTool
        TOOLS["b"] = EchoTool
        assert len(TOOLS) == 2

        clear_registry()
        assert len(TOOLS) == 0

    def test_clear_empty_registry(self):
        """clear_registry on empty registry doesn't fail."""
        clear_registry()
        assert len(TOOLS) == 0


# ============================================================================
# Integration Tests
# ============================================================================


class TestRegistryIntegration:
    """Integration tests for the registry system."""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete workflow: register, lookup, execute."""

        @register_tool
        class AddTool(Tool[EchoInput, EchoOutput]):
            name = "add"
            description = "Adds numbers"
            InputModel = EchoInput
            OutputModel = EchoOutput

            async def run(self, params, context, on_progress=None):
                return ToolResult(
                    success=True,
                    data=[{"echoed": params.message, "count": params.repeat + 10}],
                )

        # Verify registration
        assert "add" in list_tools()
        assert get_tool("add") is AddTool

        # Get info
        info = get_tool_info("add")
        assert info["name"] == "add"

        # Execute
        result = await execute_tool("add", {"message": "x", "repeat": 5})
        assert result.success is True
        assert result.data[0]["count"] == 15

"""
Tool registry and execution.

Provides:
- TOOLS: Dictionary mapping tool names to Tool classes
- register_tool(): Decorator for registering tools
- get_tool(): Lookup tool by name
- execute_tool(): Execute a tool with validation and error handling
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from .base import ProgressCallback, Tool, ToolContext, ToolResult, ToolResultMetadata
from .errors import (
    ToolExecutionError,
    ToolInputError,
    ToolNotFoundError,
)

# Global registry of tools
# Maps tool name (step type) to Tool class
# e.g., {"map": MapTool, "fetch": FetchTool, ...}
TOOLS: dict[str, type[Tool]] = {}

# Track whether tools have been auto-loaded
_tools_loaded = False


def _ensure_tools_loaded() -> None:
    """Ensure all tool modules are imported and tools are registered.

    This is called lazily by get_tool() and execute_tool() to avoid
    circular imports while ensuring tools are registered before use.
    """
    global _tools_loaded
    if _tools_loaded:
        return
    _tools_loaded = True

    # Import tool modules directly to trigger @register_tool decorators
    # Import each module separately to isolate failures and avoid
    # going through kurt.tools which could cause circular imports
    tool_modules = [
        "kurt.tools.map",
        "kurt.tools.fetch",
        "kurt.tools.sql",
        "kurt.tools.write_db",
        "kurt.tools.batch_embedding",
        "kurt.tools.batch_llm",
        "kurt.tools.agent",
        "kurt.tools.research",
        "kurt.tools.signals",
    ]

    import importlib
    import sys

    for module_name in tool_modules:
        try:
            # Force reimport if module was previously imported but tool not registered
            # This handles the case where module was imported before @register_tool ran
            if module_name in sys.modules:
                module = sys.modules[module_name]
                # Re-trigger registration if the module has the tool class
                for attr_name in dir(module):
                    attr = getattr(module, attr_name, None)
                    if (
                        isinstance(attr, type)
                        and hasattr(attr, "name")
                        and attr.name
                        and attr.name not in TOOLS
                        and hasattr(attr, "run")
                    ):
                        # Manually register the tool
                        TOOLS[attr.name] = attr
            else:
                importlib.import_module(module_name)
        except ImportError:
            # Some tools may not be available in minimal installations
            pass


def register_tool(tool_class: type[Tool]) -> type[Tool]:
    """
    Decorator to register a tool class in the global registry.

    Usage:
        @register_tool
        class MapTool(Tool[MapInput, MapOutput]):
            name = "map"
            ...

    Args:
        tool_class: Tool class to register

    Returns:
        The same tool class (for decorator chaining)

    Raises:
        ValueError: If tool name is missing or already registered
    """
    if not hasattr(tool_class, "name") or not tool_class.name:
        raise ValueError(f"Tool class {tool_class.__name__} must define 'name' attribute")

    name = tool_class.name
    if name in TOOLS:
        raise ValueError(
            f"Tool '{name}' already registered by {TOOLS[name].__name__}"
        )

    TOOLS[name] = tool_class
    return tool_class


def get_tool(name: str) -> type[Tool]:
    """
    Get a tool class by name.

    Args:
        name: Tool name (e.g., 'map', 'fetch', 'llm')

    Returns:
        Tool class

    Raises:
        ToolNotFoundError: If tool name is not registered
    """
    _ensure_tools_loaded()
    if name not in TOOLS:
        raise ToolNotFoundError(name)
    return TOOLS[name]


def list_tools() -> list[str]:
    """
    List all registered tool names.

    Returns:
        Sorted list of tool names

    Note:
        Does NOT auto-load tools. Returns only currently registered tools.
        Use get_tool() to trigger auto-loading if needed.
    """
    return sorted(TOOLS.keys())


def get_tool_info(name: str) -> dict[str, Any]:
    """
    Get metadata about a registered tool.

    Args:
        name: Tool name

    Returns:
        Dictionary with tool metadata (name, description, input/output schemas)

    Raises:
        ToolNotFoundError: If tool name is not registered
    """
    tool_class = get_tool(name)
    return {
        "name": tool_class.name,
        "description": tool_class.description,
        "input_schema": (
            tool_class.InputModel.model_json_schema()
            if hasattr(tool_class, "InputModel") and tool_class.InputModel
            else None
        ),
        "output_schema": (
            tool_class.OutputModel.model_json_schema()
            if hasattr(tool_class, "OutputModel") and tool_class.OutputModel
            else None
        ),
    }


async def execute_tool(
    name: str,
    params: dict[str, Any],
    context: ToolContext | None = None,
    on_progress: ProgressCallback | None = None,
) -> ToolResult:
    """
    Execute a tool by name with the given parameters.

    This is the main entry point for tool execution. It handles:
    1. Tool lookup from registry
    2. Input validation via Pydantic
    3. Context creation if not provided
    4. Execution with timing
    5. Error wrapping

    Args:
        name: Tool name (e.g., 'map', 'fetch')
        params: Input parameters as dictionary
        context: Execution context (created if None)
        on_progress: Optional progress callback

    Returns:
        ToolResult with success status, data, errors, and metadata

    Raises:
        ToolNotFoundError: If tool name is not registered
        ToolConfigError: If params fail Pydantic validation
        ToolExecutionError: If tool execution fails
    """
    # 1. Look up tool class
    tool_class = get_tool(name)

    # 2. Validate input parameters
    try:
        validated_params = tool_class.InputModel.model_validate(params)
    except ValidationError as e:
        raise ToolInputError(
            tool_name=name,
            message=str(e),
            validation_errors=e.errors(),
        ) from e

    # 3. Create context if not provided
    if context is None:
        context = ToolContext()

    # 4. Instantiate tool and execute with timing
    tool = tool_class()
    started_at = datetime.now(timezone.utc)

    try:
        result = await tool.run(validated_params, context, on_progress)
    except Exception as e:
        # Wrap unexpected errors in ToolExecutionError
        if isinstance(e, (ToolExecutionError,)):
            raise
        raise ToolExecutionError(
            tool_name=name,
            message=str(e),
            cause=e,
        ) from e

    completed_at = datetime.now(timezone.utc)

    # 5. Add timing metadata if not already present
    if result.metadata is None:
        result.metadata = ToolResultMetadata.from_timestamps(started_at, completed_at)

    return result


def clear_registry() -> None:
    """
    Clear all registered tools.

    Primarily used for testing to ensure clean state.
    Also resets _tools_loaded flag so tools can be re-loaded.
    """
    global _tools_loaded
    TOOLS.clear()
    _tools_loaded = False

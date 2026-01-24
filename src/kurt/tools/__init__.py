"""
Kurt Tool System.

This module provides the foundational infrastructure for defining,
registering, and executing tools in Kurt workflows.

Tool names map to step types in workflow TOML:
- step.type='map' -> MapTool
- step.type='fetch' -> FetchTool
- step.type='write' -> WriteTool
- step.type='sql' -> SQLTool
- step.type='embed' -> EmbedTool
- step.type='llm' -> LLMTool
- step.type='agent' -> AgentTool

Example usage:
    from kurt.tools import Tool, ToolContext, ToolResult, register_tool, execute_tool

    @register_tool
    class MyTool(Tool[MyInput, MyOutput]):
        name = "my_tool"
        description = "Does something useful"
        InputModel = MyInput
        OutputModel = MyOutput

        async def run(self, params, context, on_progress=None):
            # Implementation
            return ToolResult(success=True, data=[...])

    # Execute
    result = await execute_tool("my_tool", {"param": "value"})
"""

# Base classes and dataclasses
from .base import (
    ProgressCallback,
    SubstepEvent,
    Tool,
    ToolContext,
    ToolResult,
    ToolResultError,
    ToolResultMetadata,
    ToolResultSubstep,
)

# Error types
from .errors import (
    ToolCanceledError,
    ToolConfigError,
    ToolError,
    ToolExecutionError,
    ToolInputError,
    ToolNotFoundError,
    ToolTimeoutError,
)

# Registry functions
from .registry import (
    TOOLS,
    clear_registry,
    execute_tool,
    get_tool,
    get_tool_info,
    list_tools,
    register_tool,
)

# Context loading
from .context import (
    ConfigValidationError,
    DoltSettings,
    FetchSettings,
    LLMClient,
    LLMSettings,
    Settings,
    StorageSettings,
    load_settings,
    load_tool_context,
    validate_settings,
)

# Import tools to register them
from .embed_tool import (
    EmbedConfig,
    EmbedInput,
    EmbedOutput,
    EmbedParams,
    EmbedTool,
    bytes_to_embedding,
    embedding_to_bytes,
)
from .agent_tool import (
    AgentArtifact,
    AgentConfig,
    AgentInput,
    AgentOutput,
    AgentParams,
    AgentTool,
    AgentToolCall,
)
from .fetch_tool import FetchConfig, FetchInput, FetchOutput, FetchParams, FetchTool
from .llm_tool import LLMConfig, LLMInput, LLMOutput, LLMParams, LLMTool
from .map_tool import MapInput, MapOutput, MapTool, normalize_url
from .sql_tool import SQLConfig, SQLInput, SQLOutput, SQLTool
from .write_tool import WriteConfig, WriteInput, WriteOutput, WriteParams, WriteTool

# Import research and signals tools to register them
from .research import ResearchTool, ResearchInput, ResearchOutput, CitationOutput
from .signals import SignalsTool, SignalInput, SignalOutput

__all__ = [
    # Base classes
    "Tool",
    "ToolContext",
    "ToolResult",
    "ToolResultError",
    "ToolResultMetadata",
    "ToolResultSubstep",
    "SubstepEvent",
    "ProgressCallback",
    # Errors
    "ToolError",
    "ToolNotFoundError",
    "ToolConfigError",
    "ToolInputError",
    "ToolExecutionError",
    "ToolTimeoutError",
    "ToolCanceledError",
    # Registry
    "TOOLS",
    "register_tool",
    "get_tool",
    "list_tools",
    "get_tool_info",
    "execute_tool",
    "clear_registry",
    # Map tool
    "MapTool",
    "MapInput",
    "MapOutput",
    "normalize_url",
    # Fetch tool
    "FetchTool",
    "FetchInput",
    "FetchOutput",
    "FetchConfig",
    "FetchParams",
    # SQL tool
    "SQLTool",
    "SQLInput",
    "SQLOutput",
    "SQLConfig",
    # Embed tool
    "EmbedTool",
    "EmbedInput",
    "EmbedOutput",
    "EmbedConfig",
    "EmbedParams",
    "embedding_to_bytes",
    "bytes_to_embedding",
    # Agent tool
    "AgentTool",
    "AgentInput",
    "AgentOutput",
    "AgentConfig",
    "AgentParams",
    "AgentArtifact",
    "AgentToolCall",
    # Write tool
    "WriteTool",
    "WriteInput",
    "WriteOutput",
    "WriteConfig",
    "WriteParams",
    # LLM tool
    "LLMTool",
    "LLMInput",
    "LLMOutput",
    "LLMConfig",
    "LLMParams",
    # Context loading
    "Settings",
    "LLMSettings",
    "FetchSettings",
    "StorageSettings",
    "DoltSettings",
    "LLMClient",
    "load_settings",
    "load_tool_context",
    "validate_settings",
    "ConfigValidationError",
    # Research tool
    "ResearchTool",
    "ResearchInput",
    "ResearchOutput",
    "CitationOutput",
    # Signals tool
    "SignalsTool",
    "SignalInput",
    "SignalOutput",
]

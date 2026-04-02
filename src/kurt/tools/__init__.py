"""
Kurt Tool System.

This module provides the foundational infrastructure for defining,
registering, and executing tools in Kurt workflows.

Tool names map to step types in workflow TOML:
- step.type='map' -> MapTool
- step.type='fetch' -> FetchTool
- step.type='write-db' -> WriteTool
- step.type='sql' -> SQLTool
- step.type='batch-embedding' -> BatchEmbeddingTool
- step.type='batch-llm' -> BatchLLMTool
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

# Core infrastructure (re-exported from core/)
# Import tools to register them
from .agent import (
    AgentArtifact,
    AgentConfig,
    AgentInput,
    AgentOutput,
    AgentParams,
    AgentTool,
    AgentToolCall,
)
from .batch_embedding import (
    BatchEmbeddingConfig,
    BatchEmbeddingInput,
    BatchEmbeddingOutput,
    BatchEmbeddingParams,
    BatchEmbeddingTool,
    bytes_to_embedding,
    embedding_to_bytes,
)
from .batch_llm import (
    BatchLLMConfig,
    BatchLLMInput,
    BatchLLMOutput,
    BatchLLMParams,
    BatchLLMTool,
)
from .core import (
    # Registry
    TOOLS,
    # Context loading
    ConfigValidationError,
    DoltSettings,
    FetchSettings,
    # Base classes
    InputT,
    LLMClient,
    LLMSettings,
    OutputT,
    ProgressCallback,
    Settings,
    StorageSettings,
    SubstepEvent,
    Tool,
    # Errors
    ToolCanceledError,
    ToolConfigError,
    ToolContext,
    ToolError,
    ToolExecutionError,
    ToolInputError,
    ToolNotFoundError,
    ToolResult,
    ToolResultError,
    ToolResultMetadata,
    ToolResultSubstep,
    ToolTimeoutError,
    # Utilities
    canonicalize_url,
    clear_registry,
    # Runner
    create_pending_run,
    execute_tool,
    get_tool,
    get_tool_info,
    list_tools,
    load_settings,
    load_tool_context,
    make_document_id,
    make_url_hash,
    register_tool,
    run_tool_from_file,
    run_tool_with_tracking,
    spawn_background_run,
    validate_settings,
)
from .fetch import (
    NON_RETRYABLE_STATUS_CODES,
    RETRYABLE_STATUS_CODES,
    FetchInput,
    FetchOutput,
    FetchParams,
    FetchTool,
    FetchToolConfig,
)
from .map import MapInput, MapOutput, MapTool, normalize_url

# Backward compatibility alias - FetchConfig in fetch_tool.py was renamed to FetchToolConfig
# The FetchConfig in fetch/config.py is a StepConfig for workflows (different purpose)
FetchConfig = FetchToolConfig

# Import research and signals tools to register them
from .research import CitationOutput, ResearchInput, ResearchOutput, ResearchTool  # noqa: E402
from .signals import SignalInput, SignalOutput, SignalsTool  # noqa: E402
from .sql import SQLConfig, SQLInput, SQLOutput, SQLTool  # noqa: E402
from .write_db import WriteConfig, WriteInput, WriteOutput, WriteParams, WriteTool  # noqa: E402

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
    "InputT",
    "OutputT",
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
    # Runner
    "run_tool_with_tracking",
    "create_pending_run",
    "spawn_background_run",
    "run_tool_from_file",
    # Utilities
    "canonicalize_url",
    "make_document_id",
    "make_url_hash",
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
    "FetchToolConfig",
    "FetchParams",
    "NON_RETRYABLE_STATUS_CODES",
    "RETRYABLE_STATUS_CODES",
    # SQL tool
    "SQLTool",
    "SQLInput",
    "SQLOutput",
    "SQLConfig",
    # Batch embedding tool
    "BatchEmbeddingTool",
    "BatchEmbeddingInput",
    "BatchEmbeddingOutput",
    "BatchEmbeddingConfig",
    "BatchEmbeddingParams",
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
    # Batch LLM tool
    "BatchLLMTool",
    "BatchLLMInput",
    "BatchLLMOutput",
    "BatchLLMConfig",
    "BatchLLMParams",
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

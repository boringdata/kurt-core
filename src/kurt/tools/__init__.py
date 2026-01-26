"""
Kurt Tool System.

This module provides the foundational infrastructure for defining,
registering, and executing tools in Kurt workflows.

Tool names map to step types in workflow TOML:
- step.type='map' -> MapTool
- step.type='fetch' -> FetchTool
- step.type='write' -> WriteTool
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
from .core import (
    # Base classes
    InputT,
    OutputT,
    ProgressCallback,
    SubstepEvent,
    Tool,
    ToolContext,
    ToolResult,
    ToolResultError,
    ToolResultMetadata,
    ToolResultSubstep,
    # Context loading
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
    # Errors
    ToolCanceledError,
    ToolConfigError,
    ToolError,
    ToolExecutionError,
    ToolInputError,
    ToolNotFoundError,
    ToolTimeoutError,
    # Registry
    TOOLS,
    clear_registry,
    execute_tool,
    get_tool,
    get_tool_info,
    list_tools,
    register_tool,
    # Runner
    create_pending_run,
    run_tool_from_file,
    run_tool_with_tracking,
    spawn_background_run,
    # Utilities
    canonicalize_url,
    make_document_id,
    make_url_hash,
)

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
from .fetch import (
    NON_RETRYABLE_STATUS_CODES,
    RETRYABLE_STATUS_CODES,
    FetchInput,
    FetchOutput,
    FetchParams,
    FetchTool,
    FetchToolConfig,
    _compute_content_hash,
    _generate_content_path,
    _is_retryable_error,
    _save_content,
)
from .map import MapInput, MapOutput, MapTool, normalize_url

# Backward compatibility alias - FetchConfig in fetch_tool.py was renamed to FetchToolConfig
# The FetchConfig in fetch/config.py is a StepConfig for workflows (different purpose)
FetchConfig = FetchToolConfig

# Import research and signals tools to register them
from .research import CitationOutput, ResearchInput, ResearchOutput, ResearchTool
from .signals import SignalInput, SignalOutput, SignalsTool
from .sql import SQLConfig, SQLInput, SQLOutput, SQLTool
from .write import WriteConfig, WriteInput, WriteOutput, WriteParams, WriteTool

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
    "_compute_content_hash",
    "_generate_content_path",
    "_is_retryable_error",
    "_save_content",
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

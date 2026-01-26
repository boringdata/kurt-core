"""
Kurt Tool System Core Infrastructure.

This module contains all foundational infrastructure for the tool system:
- Base classes: Tool, ToolContext, ToolResult, SubstepEvent
- Error taxonomy: ToolError, ToolNotFoundError, ToolConfigError, etc.
- Registry: register_tool, get_tool, execute_tool, TOOLS
- Context loading: load_settings, load_tool_context, Settings
- Runner: run_tool_with_tracking, spawn_background_run
- Utilities: canonicalize_url, make_document_id
- CLI options: reusable Click decorators
"""

# Base classes and dataclasses
from .base import (
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
)

# CLI options and utilities (moved from kurt.cli.core)
from .cli_options import (
    add_background_options,
    add_confirmation_options,
    add_filter_options,
    add_output_options,
    background_option,
    dry_run_option,
    exclude_option,
    fetch_engine_option,
    file_extension_option,
    format_option,
    format_table_option,
    has_content_option,
    ids_option,
    in_cluster_option,
    include_option,
    limit_option,
    min_content_length_option,
    print_json,
    priority_option,
    source_type_option,
    url_contains_option,
    with_content_type_option,
    with_status_option,
    yes_option,
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

# Step hooks (moved from kurt.core.hooks)
from .hooks import (
    CompositeStepHooks,
    NoopStepHooks,
    StepHooks,
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

# Runner
from .runner import (
    create_pending_run,
    run_tool_from_file,
    run_tool_with_tracking,
    spawn_background_run,
)

# Utilities
from .utils import (
    canonicalize_url,
    make_document_id,
    make_url_hash,
)

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
    # Runner
    "run_tool_with_tracking",
    "create_pending_run",
    "spawn_background_run",
    "run_tool_from_file",
    # Utilities
    "canonicalize_url",
    "make_document_id",
    "make_url_hash",
    # Step hooks (moved from kurt.core)
    "StepHooks",
    "NoopStepHooks",
    "CompositeStepHooks",
    # CLI options and utilities (moved from kurt.cli.core)
    "add_background_options",
    "add_confirmation_options",
    "add_filter_options",
    "add_output_options",
    "background_option",
    "dry_run_option",
    "exclude_option",
    "fetch_engine_option",
    "file_extension_option",
    "format_option",
    "format_table_option",
    "has_content_option",
    "ids_option",
    "in_cluster_option",
    "include_option",
    "limit_option",
    "min_content_length_option",
    "print_json",
    "priority_option",
    "source_type_option",
    "url_contains_option",
    "with_content_type_option",
    "with_status_option",
    "yes_option",
]

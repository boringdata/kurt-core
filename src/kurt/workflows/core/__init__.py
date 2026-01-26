"""
Shared workflow utilities.

Contains common code used across workflow modules:
- Cycle detection for dependency graphs
- Shared configuration models
- Shared error classes
- CLI utilities (options, formatters, helpers)
"""

from .cli import (
    # Enums
    OutputFormat,
    StatusColor,
    # Click options
    add_workflow_list_options,
    add_workflow_run_options,
    # Output formatting
    console,
    create_run_history_table,
    create_status_table,
    create_workflow_table,
    display_empty_result,
    display_not_found,
    display_validation_errors,
    display_validation_success,
    display_workflow_completed,
    display_workflow_started,
    foreground_option,
    format_count,
    format_duration,
    format_status,
    input_option,
    # Input parsing
    parse_input_value,
    parse_inputs,
    print_error,
    print_info,
    print_json_output,
    print_success,
    print_warning,
    scheduled_option,
    tag_option,
    validate_input_format,
    workflow_format_option,
)
from .errors import CircularDependencyError, WorkflowParseError
from .models import GuardrailsConfig, ScheduleConfig
from .validation import detect_cycle, validate_cron

__all__ = [
    # Validation
    "detect_cycle",
    "validate_cron",
    # Errors
    "CircularDependencyError",
    "WorkflowParseError",
    # Models
    "GuardrailsConfig",
    "ScheduleConfig",
    # CLI - Click options
    "add_workflow_list_options",
    "add_workflow_run_options",
    "foreground_option",
    "input_option",
    "scheduled_option",
    "tag_option",
    "workflow_format_option",
    # CLI - Input parsing
    "parse_input_value",
    "parse_inputs",
    "validate_input_format",
    # CLI - Output formatting
    "console",
    "create_run_history_table",
    "create_status_table",
    "create_workflow_table",
    "display_empty_result",
    "display_not_found",
    "display_validation_errors",
    "display_validation_success",
    "display_workflow_completed",
    "display_workflow_started",
    "format_count",
    "format_duration",
    "format_status",
    "print_error",
    "print_info",
    "print_json_output",
    "print_success",
    "print_warning",
    # CLI - Enums
    "OutputFormat",
    "StatusColor",
]

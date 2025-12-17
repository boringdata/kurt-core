"""
Framework utilities for model-based indexing pipeline.
"""

from .dbos_integration import configure_dbos_writer
from .decorator import model
from .display import (
    display,
    make_progress_callback,
    print_info,
    print_inline_table,
    print_progress,
    print_warning,
)
from .dspy_helpers import (
    LLMAPIError,
    LLMAuthenticationError,
    LLMRateLimitError,
    get_dspy_lm,
)
from .mixins import (
    LLMTelemetryMixin,
    PipelineModelBase,
    _serialize,
    apply_dspy_telemetry,
    apply_field_renames,
)
from .model_runner import (
    ModelContext,
    PipelineContext,
    execute_model_sync,
    run_model,
    run_models,
    run_pipeline,
)
from .pipeline import PipelineConfig, get_pipeline
from .references import Reference
from .registry import ModelRegistry
from .table_io import TableReader, TableWriter
from .workflow import resolve_pipeline, run_pipeline_workflow, run_workflow

__all__ = [
    # Core
    "model",
    "Reference",
    "TableReader",
    "TableWriter",
    "ModelRegistry",
    "display",
    "print_progress",
    "print_info",
    "print_inline_table",
    "print_warning",
    "make_progress_callback",
    "configure_dbos_writer",
    # Pipeline execution
    "ModelContext",
    "PipelineContext",
    "PipelineConfig",
    "get_pipeline",
    "run_pipeline",
    "run_workflow",
    "run_pipeline_workflow",
    "resolve_pipeline",
    "run_model",
    "run_models",
    "execute_model_sync",
    # Mixins
    "PipelineModelBase",
    "LLMTelemetryMixin",
    "_serialize",
    "apply_dspy_telemetry",
    "apply_field_renames",
    # DSPy helpers
    "get_dspy_lm",
    # LLM Errors
    "LLMAuthenticationError",
    "LLMRateLimitError",
    "LLMAPIError",
]

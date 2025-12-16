"""Base mixins for pipeline models.

This module provides reusable SQLModel mixins for dbt-style pipeline steps:
- PipelineModelBase: Standard metadata columns (workflow_id, timestamps, error)
- LLMTelemetryMixin: Token usage and timing for LLM/DSPy steps
- _serialize(): Helper to convert DSPy outputs to JSON-serializable dicts
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from sqlmodel import Field, SQLModel

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================


def _serialize(field: Any, default: Any = None) -> Any:
    """Serialize DSPy output field to JSON-serializable format.

    Handles all DSPy output variants:
    - None → default
    - str (JSON) → parsed dict/list
    - Pydantic model → model_dump()
    - list[Pydantic] → [model_dump(), ...]
    - dict/list → pass through

    Args:
        field: DSPy output field (could be str, Pydantic model, dict, list, None)
        default: Default value if field is None or parsing fails

    Returns:
        JSON-serializable dict, list, or default value
    """
    if field is None:
        return default

    # Handle JSON string
    if isinstance(field, str):
        try:
            return json.loads(field)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON string: {field[:100]}...")
            return default

    # Handle Pydantic model
    if hasattr(field, "model_dump"):
        return field.model_dump()

    # Handle list of Pydantic models
    if isinstance(field, list) and field and hasattr(field[0], "model_dump"):
        return [x.model_dump() if hasattr(x, "model_dump") else x for x in field]

    # Already a dict/list, pass through
    return field


# ============================================================================
# Base Mixins
# ============================================================================


class PipelineModelBase(SQLModel):
    """Base mixin for all pipeline output tables.

    Provides standard metadata columns that are auto-populated by the framework:
    - workflow_id: Links row to the workflow run that created it
    - created_at/updated_at: Timestamps for tracking
    - model_name: Name of the model that created this row
    - error: Error message if processing failed for this row

    Usage:
        class MyOutputRow(PipelineModelBase, table=True):
            __tablename__ = "my_output_table"
            id: str = Field(primary_key=True)
            # ... model-specific fields
    """

    workflow_id: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    model_name: Optional[str] = Field(default=None)
    error: Optional[str] = Field(default=None)

    class Config:
        # Allow extra fields during construction (they'll be ignored)
        extra = "ignore"


class LLMTelemetryMixin(SQLModel):
    """Mixin for pipeline steps that call LLMs (DSPy, direct API, etc.).

    Provides standard telemetry columns for tracking LLM usage:
    - tokens_prompt: Input tokens consumed
    - tokens_completion: Output tokens generated
    - extraction_time_ms: Time taken for LLM call(s)
    - llm_model_name: Model used (e.g., "claude-3-haiku")

    Usage:
        class MyLLMOutputRow(PipelineModelBase, LLMTelemetryMixin, table=True):
            __tablename__ = "my_llm_output"
            id: str = Field(primary_key=True)
            # ... model-specific fields

            @model_validator(mode='before')
            @classmethod
            def from_dspy(cls, data: dict) -> dict:
                if "dspy_telemetry" in data:
                    t = data.pop("dspy_telemetry")
                    data["tokens_prompt"] = t.get("tokens_prompt")
                    data["tokens_completion"] = t.get("tokens_completion")
                    data["extraction_time_ms"] = int(t.get("execution_time", 0) * 1000)
                    data["llm_model_name"] = t.get("model_name")
                return data
    """

    tokens_prompt: Optional[int] = Field(default=None)
    tokens_completion: Optional[int] = Field(default=None)
    extraction_time_ms: Optional[int] = Field(default=None)
    llm_model_name: Optional[str] = Field(default=None)

    class Config:
        extra = "ignore"


# ============================================================================
# Validator Helpers
# ============================================================================


def apply_dspy_telemetry(data: dict) -> dict:
    """Extract telemetry from dspy_telemetry dict into flat fields.

    Use this in model_validator to transform:
        {"dspy_telemetry": {"tokens_prompt": 100, ...}}
    Into:
        {"tokens_prompt": 100, ...}

    Args:
        data: Input dict (modified in place)

    Returns:
        Modified dict with telemetry fields extracted
    """
    if "dspy_telemetry" in data:
        t = data.pop("dspy_telemetry")
        if t:
            data["tokens_prompt"] = t.get("tokens_prompt")
            data["tokens_completion"] = t.get("tokens_completion")
            data["extraction_time_ms"] = int(t.get("execution_time", 0) * 1000)
            data["llm_model_name"] = t.get("model_name")
    return data


def apply_field_renames(data: dict, renames: dict[str, str]) -> dict:
    """Apply field renames from source to target.

    Args:
        data: Input dict (modified in place)
        renames: Mapping of {source_field: target_field}

    Returns:
        Modified dict with fields renamed

    Example:
        apply_field_renames(data, {"heading": "section_heading"})
    """
    for source, target in renames.items():
        if source in data and target not in data:
            data[target] = data.pop(source)
    return data

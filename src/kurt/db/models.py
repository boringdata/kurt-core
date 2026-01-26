"""
Core database models for kurt.

Infrastructure tables shared across all tools.
Tool-specific output tables are defined in tools/<name>/models.py.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

# ============================================================================
# Mixins
# ============================================================================


class TimestampMixin(SQLModel):
    """Adds created_at and updated_at columns."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TenantMixin(SQLModel):
    """Adds user_id and workspace_id for multi-tenant isolation."""

    user_id: Optional[str] = Field(default=None, index=True)
    workspace_id: Optional[str] = Field(default=None, index=True)


class EmbeddingMixin(SQLModel):
    """Adds vector embedding for similarity search.

    Stores embeddings as bytes (float32 values packed).
    Default dimension is 512 (2048 bytes) but can vary by model.

    Usage in workflow models:
        class MyEntity(EmbeddingMixin, TenantMixin, SQLModel, table=True):
            id: int = Field(primary_key=True)
            name: str
            # embedding field inherited from mixin
    """

    embedding: Optional[bytes] = Field(default=None)


class ConfidenceMixin(SQLModel):
    """Adds confidence scoring for extracted data.

    Common pattern for LLM-extracted entities, claims, relationships.
    """

    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


# ============================================================================
# Infrastructure Models
# ============================================================================


class LLMTrace(TimestampMixin, TenantMixin, SQLModel, table=True):
    """
    LLM call traces for debugging and cost tracking.

    Records every LLM API call with prompts, responses, token usage, and cost.
    """

    __tablename__ = "llm_traces"

    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: str = Field(index=True)
    step_name: str = Field(index=True)

    # Model info
    model: str
    provider: str = Field(default="anthropic")

    # Request/Response
    prompt: str
    response: str
    structured_output: Optional[str] = Field(default=None)  # JSON string of parsed output

    # Token usage
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)

    # Cost tracking (in USD)
    cost: float = Field(default=0.0)

    # Timing
    latency_ms: int = Field(default=0)

    # Error tracking
    error: Optional[str] = Field(default=None)
    retry_count: int = Field(default=0)

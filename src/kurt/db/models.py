"""
Core database models for kurt.

Infrastructure tables shared across all workflows.
Workflow-specific output tables are defined in workflows/<name>/models.py
and registered via register_all_models().
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


def register_all_models():
    """Import all models to register them with SQLModel.metadata.

    Call this before creating tables to ensure all workflow models
    are included in SQLModel.metadata.create_all().
    """
    # Infrastructure models (defined below)
    from kurt.db.models import LLMTrace  # noqa: F401
    from kurt.workflows.domain_analytics.models import (  # noqa: F401
        AnalyticsDomain,
        PageAnalytics,
    )
    from kurt.tools.fetch.models import FetchDocument  # noqa: F401

    # Workflow models
    from kurt.tools.map.models import MapDocument  # noqa: F401
    from kurt.workflows.research.models import ResearchDocument  # noqa: F401
    from kurt.workflows.signals.models import MonitoringSignal  # noqa: F401


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

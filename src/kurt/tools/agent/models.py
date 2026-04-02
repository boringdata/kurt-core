"""Database models for agent tool execution tracking."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from kurt.db.models import TenantMixin, TimestampMixin


class AgentExecutionStatus(str, Enum):
    """Status for agent executions."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"


class AgentExecution(TimestampMixin, TenantMixin, SQLModel, table=True):
    """Persisted agent execution results for tracking and debugging."""

    __tablename__ = "agent_executions"

    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: Optional[str] = Field(default=None, index=True)

    # Execution status
    status: AgentExecutionStatus = Field(default=AgentExecutionStatus.PENDING)

    # Configuration
    model: str = Field(default="claude-sonnet-4-20250514")
    max_turns: int = Field(default=10)
    permission_mode: str = Field(default="bypassPermissions")

    # Metrics
    turns_used: int = Field(default=0)
    tokens_in: int = Field(default=0)
    tokens_out: int = Field(default=0)
    cost_usd: float = Field(default=0.0)
    duration_ms: int = Field(default=0)

    # Result
    result: Optional[str] = Field(default=None)
    prompt: Optional[str] = Field(default=None)

    # Error tracking
    error: Optional[str] = Field(default=None)

    # Tool calls and artifacts stored as JSON
    tool_calls_json: Optional[list] = Field(sa_column=Column(JSON), default=None)
    artifacts_json: Optional[list] = Field(sa_column=Column(JSON), default=None)

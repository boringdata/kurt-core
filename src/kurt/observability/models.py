"""
SQLModel classes for observability tables.

Tables for workflow tracking and monitoring:
- WorkflowRun: One row per workflow execution
- StepLog: Summary row per step (updated in place)
- StepEvent: Append-only event stream for progress tracking
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, BigInteger, Column, ForeignKey, Index, Text
from sqlmodel import Field, SQLModel

from kurt.db.models import TenantMixin, TimestampMixin


class WorkflowStatus(str, Enum):
    """Status for workflow runs."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Status for workflow steps."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowRun(TenantMixin, SQLModel, table=True):
    """Workflow execution tracking.

    One row per workflow execution. Tracks overall workflow status,
    timing, inputs, and any errors.
    """

    __tablename__ = "workflow_runs"
    __table_args__ = (
        Index("idx_workflow_runs_status", "status"),
        Index("idx_workflow_runs_started", "started_at"),
    )

    id: str = Field(primary_key=True, max_length=36)
    workflow: str = Field(max_length=255, index=True)
    status: WorkflowStatus = Field(default=WorkflowStatus.PENDING, max_length=20)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
    error: Optional[str] = Field(sa_column=Column(Text), default=None)
    inputs: Optional[dict] = Field(sa_column=Column(JSON), default=None)
    metadata_json: Optional[dict] = Field(sa_column=Column(JSON), default=None)


class StepLog(TenantMixin, SQLModel, table=True):
    """Step-level summaries.

    One row per step per run. Updated in place as the step progresses.
    Tracks input/output counts, errors, and timing.
    """

    __tablename__ = "step_logs"
    __table_args__ = (
        Index("idx_step_logs_run_step", "run_id", "step_id"),
        # Note: SQLModel handles unique constraint differently
    )

    id: str = Field(primary_key=True, max_length=36)
    run_id: str = Field(
        sa_column=Column(
            "run_id",
            nullable=False,
            index=True,
        ),
        max_length=36,
    )
    step_id: str = Field(max_length=255, index=True)
    tool: str = Field(max_length=50)
    status: StepStatus = Field(default=StepStatus.PENDING, max_length=20)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    input_count: Optional[int] = Field(default=None)
    output_count: Optional[int] = Field(default=None)
    error_count: int = Field(default=0)
    errors: Optional[dict] = Field(sa_column=Column(JSON), default=None)
    metadata_json: Optional[dict] = Field(sa_column=Column(JSON), default=None)


class StepEvent(TenantMixin, SQLModel, table=True):
    """Append-only event stream for progress tracking.

    Each row represents a progress event for a step. Used for
    real-time progress monitoring and streaming updates.
    """

    __tablename__ = "step_events"
    __table_args__ = (Index("idx_step_events_run_id", "run_id", "id"),)

    id: Optional[int] = Field(
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True),
        default=None,
    )
    run_id: str = Field(max_length=36, index=True)
    step_id: str = Field(max_length=255)
    substep: Optional[str] = Field(max_length=255, default=None)
    status: StepStatus = Field(default=StepStatus.PENDING, max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    current: Optional[int] = Field(default=None)
    total: Optional[int] = Field(default=None)
    message: Optional[str] = Field(sa_column=Column(Text), default=None)
    metadata_json: Optional[dict] = Field(sa_column=Column(JSON), default=None)


# List of all observability models for table creation
OBSERVABILITY_MODELS = [WorkflowRun, StepLog, StepEvent]

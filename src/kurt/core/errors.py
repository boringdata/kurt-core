"""Structured error handling for workflow steps.

This module provides error classes for representing step/model failures with
enough metadata for dashboards and CLI surfaces.

Usage:
    from kurt.core import WorkflowStepError, WorkflowDocumentRef

    # For per-document errors (skip and continue)
    raise WorkflowStepError(
        step="indexing.section_extractions",
        message="LLM rate limit exceeded",
        action="skip_record",
        severity="recoverable",
        documents=[
            WorkflowDocumentRef(document_id="doc1", section_id="sec1"),
        ],
        metadata={"llm_model": "claude-3-haiku"},
        cause=original_exception,
    )

    # For systemic errors (fail the model)
    raise WorkflowStepError(
        step="indexing.entity_resolution",
        message="Database constraint violation",
        action="fail_model",
        severity="fatal",
        documents=[WorkflowDocumentRef(document_id="doc1")],
        cause=db_exception,
    )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Literal, Optional, Tuple

if TYPE_CHECKING:
    from .model_runner import PipelineContext

logger = logging.getLogger(__name__)


# Type aliases for clarity
StepName = str  # e.g., "indexing.section_extractions"
ActionType = Literal["fail_model", "skip_record", "retry"]
SeverityType = Literal["fatal", "recoverable", "info"]


@dataclass(slots=True)
class WorkflowDocumentRef:
    """Reference to a document involved in a workflow error.

    This mirrors per-row identifiers used in indexing tables like SectionExtractionRow.
    All fields are optional to support different granularity levels.

    Attributes:
        document_id: Primary document identifier
        section_id: Section within document (for section-level errors)
        source_url: Original source URL of the document
        cms_document_id: External CMS identifier
        hash: Content hash for change detection
        entity_name: Entity name (for entity resolution errors)
        claim_hash: Claim hash (for claim resolution errors)
    """

    document_id: Optional[str] = None
    section_id: Optional[str] = None
    source_url: Optional[str] = None
    cms_document_id: Optional[str] = None
    hash: Optional[str] = None
    entity_name: Optional[str] = None
    claim_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        from dataclasses import fields

        return {
            f.name: getattr(self, f.name) for f in fields(self) if getattr(self, f.name) is not None
        }

    def __str__(self) -> str:
        """Human-readable representation."""
        parts = []
        if self.document_id:
            parts.append(f"doc={self.document_id}")
        if self.section_id:
            parts.append(f"sec={self.section_id}")
        if self.entity_name:
            parts.append(f"entity={self.entity_name}")
        if self.claim_hash:
            parts.append(f"claim={self.claim_hash[:8]}")
        return f"DocRef({', '.join(parts)})" if parts else "DocRef()"


class WorkflowStepError(Exception):
    """Structured exception for workflow step failures.

    This exception carries rich context about failures, enabling:
    - Dashboard/CLI surfaces to display meaningful error information
    - Pipeline runners to make informed decisions about continuation
    - Event emitters to record detailed error telemetry

    Attributes:
        step: The workflow step that failed (e.g., "indexing.section_extractions")
        message: Human-readable error description
        action: How the pipeline should respond:
            - "fail_model": Stop the model and propagate the error
            - "skip_record": Skip the affected documents and continue
            - "retry": Indicate the operation can be retried
        severity: Error severity level:
            - "fatal": Systemic failure, model cannot continue
            - "recoverable": Per-document failure, pipeline can continue
            - "info": Informational, logged but not necessarily problematic
        documents: Tuple of document references affected by this error
        metadata: Additional key-value context (e.g., llm_model, batch_size)
        cause: The underlying exception that caused this error
        retryable: Whether the operation can be retried

    Example:
        # LLM rate limit on specific sections
        error = WorkflowStepError(
            step="indexing.section_extractions",
            message="OpenAI rate limit exceeded",
            action="skip_record",
            severity="recoverable",
            documents=[
                WorkflowDocumentRef(document_id="doc1", section_id="sec1"),
                WorkflowDocumentRef(document_id="doc1", section_id="sec2"),
            ],
            metadata={"llm_model": "gpt-4", "retry_after": 60},
            retryable=True,
        )

        # Database constraint violation
        error = WorkflowStepError(
            step="indexing.entity_resolution",
            message="Duplicate entity name in batch",
            action="fail_model",
            severity="fatal",
            documents=[WorkflowDocumentRef(entity_name="Python")],
            cause=integrity_error,
        )
    """

    def __init__(
        self,
        step: StepName,
        message: str,
        action: ActionType = "fail_model",
        severity: SeverityType = "fatal",
        documents: Optional[Tuple[WorkflowDocumentRef, ...]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        retryable: bool = False,
    ):
        self.step = step
        self.message = message
        self.action = action
        self.severity = severity
        self.documents = documents or ()
        self.metadata = metadata or {}
        self.cause = cause
        self.retryable = retryable

        # Build exception message
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        """Build the exception message string."""
        parts = [f"[{self.step}] {self.message}"]
        if self.documents:
            doc_count = len(self.documents)
            parts.append(f"({doc_count} document{'s' if doc_count > 1 else ''} affected)")
        if self.cause:
            parts.append(f"Caused by: {type(self.cause).__name__}: {self.cause}")
        return " ".join(parts)

    def for_document(
        self,
        document_id: Optional[str] = None,
        section_id: Optional[str] = None,
        **kwargs: Any,
    ) -> "WorkflowStepError":
        """Create a new error with a single document reference added.

        Args:
            document_id: Document ID to add
            section_id: Section ID to add
            **kwargs: Additional WorkflowDocumentRef fields

        Returns:
            New WorkflowStepError with the document reference appended
        """
        new_ref = WorkflowDocumentRef(
            document_id=document_id,
            section_id=section_id,
            **kwargs,
        )
        return WorkflowStepError(
            step=self.step,
            message=self.message,
            action=self.action,
            severity=self.severity,
            documents=self.documents + (new_ref,),
            metadata=self.metadata.copy(),
            cause=self.cause,
            retryable=self.retryable,
        )

    def with_documents(self, documents: Tuple[WorkflowDocumentRef, ...]) -> "WorkflowStepError":
        """Create a new error with the specified documents.

        Args:
            documents: Tuple of document references to use

        Returns:
            New WorkflowStepError with the specified documents
        """
        return WorkflowStepError(
            step=self.step,
            message=self.message,
            action=self.action,
            severity=self.severity,
            documents=documents,
            metadata=self.metadata.copy(),
            cause=self.cause,
            retryable=self.retryable,
        )

    def root_cause(self) -> Exception:
        """Get the root cause of this error, traversing the cause chain.

        Returns:
            The deepest cause in the chain, or self if no cause
        """
        current: Exception = self
        while isinstance(current, WorkflowStepError) and current.cause:
            current = current.cause
        return current

    def to_event_payload(self) -> Dict[str, Any]:
        """Convert to a serializable dict for event emission.

        This drops the .cause (not serializable) and converts dataclasses to dicts.

        Returns:
            Dictionary suitable for JSON serialization
        """
        return {
            "step": self.step,
            "message": self.message,
            "action": self.action,
            "severity": self.severity,
            "documents": [doc.to_dict() for doc in self.documents],
            "metadata": self.metadata,
            "retryable": self.retryable,
            "cause_type": type(self.cause).__name__ if self.cause else None,
            "cause_message": str(self.cause) if self.cause else None,
        }

    def __repr__(self) -> str:
        return (
            f"WorkflowStepError(step={self.step!r}, message={self.message!r}, "
            f"action={self.action!r}, severity={self.severity!r}, "
            f"documents={len(self.documents)}, retryable={self.retryable})"
        )


def record_step_error(
    error: WorkflowStepError,
    *,
    model_name: Optional[str] = None,
    ctx: Optional["PipelineContext"] = None,
) -> Dict[str, Any]:
    """Record a step error to logging and event system.

    This utility function:
    1. Logs at the appropriate severity level
    2. Emits a step_error event via the global event emitter
    3. Returns a dict for inclusion in model results

    Args:
        error: The WorkflowStepError to record
        model_name: Optional model name for logger context
        ctx: Optional PipelineContext for workflow correlation

    Returns:
        Dict with error recording summary, e.g., {"errors_recorded": 1}
    """
    from .dbos_events import get_event_emitter

    # Determine logger name
    logger_name = f"kurt.core.steps.{model_name}" if model_name else "kurt.core.steps"
    step_logger = logging.getLogger(logger_name)

    # Log at appropriate level based on severity
    log_message = f"{error.step}: {error.message}"
    if error.documents:
        log_message += f" (affecting {len(error.documents)} documents)"

    if error.severity == "fatal":
        step_logger.error(log_message, exc_info=error.cause is not None)
    elif error.severity == "recoverable":
        step_logger.warning(log_message)
    else:  # info
        step_logger.info(log_message)

    # Emit event
    event_emitter = get_event_emitter()
    if event_emitter:
        event_emitter.emit_step_error(
            model_name=model_name or error.step,
            error_payload=error.to_event_payload(),
            workflow_id=ctx.workflow_id if ctx else None,
        )

    return {
        "errors_recorded": len(error.documents) if error.documents else 1,
        "error_step": error.step,
        "error_action": error.action,
    }


def make_doc_ref(
    document_id: Optional[str] = None,
    section_id: Optional[str] = None,
    source_url: Optional[str] = None,
    **kwargs: Any,
) -> WorkflowDocumentRef:
    """Convenience factory for creating WorkflowDocumentRef instances.

    Args:
        document_id: Primary document identifier
        section_id: Section within document
        source_url: Original source URL
        **kwargs: Additional fields (cms_document_id, hash, entity_name, claim_hash)

    Returns:
        WorkflowDocumentRef instance
    """
    return WorkflowDocumentRef(
        document_id=document_id,
        section_id=section_id,
        source_url=source_url,
        **kwargs,
    )

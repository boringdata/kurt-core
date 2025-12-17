"""Tests for WorkflowStepError and related utilities."""

import pytest

from kurt.core.dbos_events import DBOSEventEmitter
from kurt.core.errors import (
    WorkflowDocumentRef,
    WorkflowStepError,
    make_doc_ref,
    record_step_error,
)


class TestWorkflowDocumentRef:
    """Tests for WorkflowDocumentRef dataclass."""

    def test_basic_creation(self):
        """Test creating a document reference with basic fields."""
        ref = WorkflowDocumentRef(
            document_id="doc1",
            section_id="sec1",
        )
        assert ref.document_id == "doc1"
        assert ref.section_id == "sec1"
        assert ref.source_url is None

    def test_all_fields(self):
        """Test creating a document reference with all fields."""
        ref = WorkflowDocumentRef(
            document_id="doc1",
            section_id="sec1",
            source_url="https://example.com/doc1",
            cms_document_id="cms-123",
            hash="abc123",
            entity_name="Python",
            claim_hash="claim-hash-456",
        )
        assert ref.document_id == "doc1"
        assert ref.source_url == "https://example.com/doc1"
        assert ref.cms_document_id == "cms-123"
        assert ref.entity_name == "Python"
        assert ref.claim_hash == "claim-hash-456"

    def test_to_dict_excludes_none(self):
        """Test that to_dict excludes None values."""
        ref = WorkflowDocumentRef(
            document_id="doc1",
            section_id=None,
        )
        d = ref.to_dict()
        assert d == {"document_id": "doc1"}
        assert "section_id" not in d

    def test_str_representation(self):
        """Test string representation of document reference."""
        ref = WorkflowDocumentRef(document_id="doc1", section_id="sec1")
        s = str(ref)
        assert "doc=doc1" in s
        assert "sec=sec1" in s

    def test_str_with_entity(self):
        """Test string representation with entity name."""
        ref = WorkflowDocumentRef(entity_name="Python")
        s = str(ref)
        assert "entity=Python" in s

    def test_empty_ref(self):
        """Test empty document reference."""
        ref = WorkflowDocumentRef()
        assert str(ref) == "DocRef()"
        assert ref.to_dict() == {}


class TestWorkflowStepError:
    """Tests for WorkflowStepError exception class."""

    def test_basic_creation(self):
        """Test creating a basic workflow step error."""
        error = WorkflowStepError(
            step="indexing.section_extractions",
            message="LLM rate limit exceeded",
        )
        assert error.step == "indexing.section_extractions"
        assert error.message == "LLM rate limit exceeded"
        assert error.action == "fail_model"  # default
        assert error.severity == "fatal"  # default
        assert error.documents == ()
        assert error.metadata == {}
        assert error.cause is None
        assert error.retryable is False

    def test_skip_record_action(self):
        """Test error with skip_record action."""
        docs = (
            WorkflowDocumentRef(document_id="doc1", section_id="sec1"),
            WorkflowDocumentRef(document_id="doc1", section_id="sec2"),
        )
        error = WorkflowStepError(
            step="indexing.section_extractions",
            message="LLM rate limit exceeded",
            action="skip_record",
            severity="recoverable",
            documents=docs,
            metadata={"llm_model": "claude-3-haiku"},
            retryable=True,
        )
        assert error.action == "skip_record"
        assert error.severity == "recoverable"
        assert len(error.documents) == 2
        assert error.metadata["llm_model"] == "claude-3-haiku"
        assert error.retryable is True

    def test_exception_message(self):
        """Test that error message is properly built."""
        error = WorkflowStepError(
            step="indexing.section_extractions",
            message="LLM rate limit exceeded",
            documents=(WorkflowDocumentRef(document_id="doc1"),),
        )
        msg = str(error)
        assert "[indexing.section_extractions]" in msg
        assert "LLM rate limit exceeded" in msg
        assert "1 document affected" in msg

    def test_exception_message_with_cause(self):
        """Test exception message includes cause."""
        cause = ValueError("Original error")
        error = WorkflowStepError(
            step="test.step",
            message="Processing failed",
            cause=cause,
        )
        msg = str(error)
        assert "Caused by: ValueError: Original error" in msg

    def test_for_document_helper(self):
        """Test for_document helper method."""
        error = WorkflowStepError(
            step="test.step",
            message="Error",
        )
        new_error = error.for_document(document_id="doc1", section_id="sec1")

        assert len(new_error.documents) == 1
        assert new_error.documents[0].document_id == "doc1"
        assert new_error.documents[0].section_id == "sec1"
        # Original should be unchanged
        assert len(error.documents) == 0

    def test_for_document_appends(self):
        """Test for_document appends to existing documents."""
        error = WorkflowStepError(
            step="test.step",
            message="Error",
            documents=(WorkflowDocumentRef(document_id="doc1"),),
        )
        new_error = error.for_document(document_id="doc2")

        assert len(new_error.documents) == 2
        assert new_error.documents[0].document_id == "doc1"
        assert new_error.documents[1].document_id == "doc2"

    def test_with_documents_helper(self):
        """Test with_documents helper method."""
        error = WorkflowStepError(
            step="test.step",
            message="Error",
            documents=(WorkflowDocumentRef(document_id="doc1"),),
        )
        new_docs = (
            WorkflowDocumentRef(document_id="doc2"),
            WorkflowDocumentRef(document_id="doc3"),
        )
        new_error = error.with_documents(new_docs)

        assert len(new_error.documents) == 2
        assert new_error.documents[0].document_id == "doc2"
        assert new_error.documents[1].document_id == "doc3"

    def test_root_cause(self):
        """Test root_cause traverses cause chain."""
        original = ValueError("Original")
        wrapped = WorkflowStepError(
            step="step1",
            message="Wrapper 1",
            cause=original,
        )
        outer = WorkflowStepError(
            step="step2",
            message="Wrapper 2",
            cause=wrapped,
        )

        root = outer.root_cause()
        assert root is original

    def test_root_cause_no_chain(self):
        """Test root_cause with no cause returns self."""
        error = WorkflowStepError(
            step="test.step",
            message="Error",
        )
        assert error.root_cause() is error

    def test_to_event_payload(self):
        """Test conversion to event payload."""
        cause = ValueError("Test error")
        error = WorkflowStepError(
            step="indexing.section_extractions",
            message="LLM rate limit exceeded",
            action="skip_record",
            severity="recoverable",
            documents=(WorkflowDocumentRef(document_id="doc1", section_id="sec1"),),
            metadata={"llm_model": "claude-3-haiku"},
            cause=cause,
            retryable=True,
        )

        payload = error.to_event_payload()

        assert payload["step"] == "indexing.section_extractions"
        assert payload["message"] == "LLM rate limit exceeded"
        assert payload["action"] == "skip_record"
        assert payload["severity"] == "recoverable"
        assert len(payload["documents"]) == 1
        assert payload["documents"][0]["document_id"] == "doc1"
        assert payload["metadata"]["llm_model"] == "claude-3-haiku"
        assert payload["retryable"] is True
        assert payload["cause_type"] == "ValueError"
        assert payload["cause_message"] == "Test error"

    def test_to_event_payload_no_cause(self):
        """Test event payload without cause."""
        error = WorkflowStepError(
            step="test.step",
            message="Error",
        )
        payload = error.to_event_payload()
        assert payload["cause_type"] is None
        assert payload["cause_message"] is None

    def test_repr(self):
        """Test repr representation."""
        error = WorkflowStepError(
            step="test.step",
            message="Error",
            documents=(WorkflowDocumentRef(document_id="doc1"),),
        )
        r = repr(error)
        assert "WorkflowStepError" in r
        assert "test.step" in r
        assert "documents=1" in r


class TestMakeDocRef:
    """Tests for make_doc_ref helper function."""

    def test_basic_usage(self):
        """Test basic make_doc_ref usage."""
        ref = make_doc_ref(document_id="doc1", section_id="sec1")
        assert isinstance(ref, WorkflowDocumentRef)
        assert ref.document_id == "doc1"
        assert ref.section_id == "sec1"

    def test_with_kwargs(self):
        """Test make_doc_ref with extra kwargs."""
        ref = make_doc_ref(
            document_id="doc1",
            entity_name="Python",
            claim_hash="abc123",
        )
        assert ref.entity_name == "Python"
        assert ref.claim_hash == "abc123"


class TestRecordStepError:
    """Tests for record_step_error utility function."""

    def test_basic_recording(self):
        """Test basic error recording."""
        error = WorkflowStepError(
            step="test.step",
            message="Test error",
            documents=(WorkflowDocumentRef(document_id="doc1"),),
        )

        result = record_step_error(error, model_name="test.model")

        assert result["errors_recorded"] == 1
        assert result["error_step"] == "test.step"
        assert result["error_action"] == "fail_model"

    def test_recording_without_documents(self):
        """Test error recording without documents defaults to 1."""
        error = WorkflowStepError(
            step="test.step",
            message="Test error",
        )

        result = record_step_error(error)
        assert result["errors_recorded"] == 1

    def test_emit_step_error_integration(self):
        """Test that record_step_error emits to event emitter."""
        from kurt.core.dbos_events import configure_event_emitter, get_event_emitter

        # Configure a fresh emitter for this test
        configure_event_emitter(workflow_id="test_wf")
        emitter = get_event_emitter()
        emitter.clear_events()

        error = WorkflowStepError(
            step="test.step",
            message="Test error",
            action="skip_record",
            severity="recoverable",
            documents=(WorkflowDocumentRef(document_id="doc1"),),
        )

        record_step_error(error, model_name="test.model")

        events = emitter.get_events()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == "step_error"
        assert event.model_name == "test.model"
        assert event.payload["step"] == "test.step"
        assert event.payload["message"] == "Test error"


class TestDBOSEventEmitterStepError:
    """Tests for emit_step_error in DBOSEventEmitter."""

    def test_emit_step_error(self):
        """Test emitting step error event."""
        emitter = DBOSEventEmitter(workflow_id="wf1")

        error_payload = {
            "step": "indexing.section_extractions",
            "message": "LLM rate limit exceeded",
            "action": "skip_record",
            "severity": "recoverable",
            "documents": [{"document_id": "doc1", "section_id": "sec1"}],
            "metadata": {"llm_model": "claude-3-haiku"},
            "retryable": True,
        }

        emitter.emit_step_error("test.model", error_payload)

        events = emitter.get_events()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == "step_error"
        assert event.model_name == "test.model"
        assert event.workflow_id == "wf1"
        assert event.payload == error_payload
        assert event.error == "LLM rate limit exceeded"

    def test_emit_step_error_with_override_workflow(self):
        """Test step error with workflow ID override."""
        emitter = DBOSEventEmitter(workflow_id="wf1")

        error_payload = {"step": "test", "message": "Error"}
        emitter.emit_step_error("test.model", error_payload, workflow_id="override_wf")

        events = emitter.get_events()
        assert events[0].workflow_id == "override_wf"


class TestWorkflowStepErrorIntegration:
    """Integration tests for WorkflowStepError with pipeline components."""

    def test_error_can_be_raised_and_caught(self):
        """Test that WorkflowStepError can be raised and caught."""
        with pytest.raises(WorkflowStepError) as exc_info:
            raise WorkflowStepError(
                step="test.step",
                message="Test error",
                action="fail_model",
            )

        error = exc_info.value
        assert error.step == "test.step"
        assert error.action == "fail_model"

    def test_error_with_skip_record_payload(self):
        """Test creating error payload for skip_record scenario."""
        error = WorkflowStepError(
            step="indexing.section_extractions",
            message="OpenAI 429 rate limit",
            action="skip_record",
            severity="recoverable",
            documents=(
                WorkflowDocumentRef(document_id="doc1", section_id="sec1"),
                WorkflowDocumentRef(document_id="doc1", section_id="sec2"),
            ),
            metadata={"llm_model": "gpt-4", "retry_after": 60},
            retryable=True,
        )

        # Verify the payload can be serialized
        payload = error.to_event_payload()
        assert isinstance(payload, dict)
        assert len(payload["documents"]) == 2
        assert all(isinstance(d, dict) for d in payload["documents"])

    def test_error_with_fail_model_for_db_constraint(self):
        """Test creating error for database constraint violation."""
        db_error = Exception("UNIQUE constraint failed: entities.name")
        error = WorkflowStepError(
            step="indexing.entity_resolution",
            message="Database constraint violation",
            action="fail_model",
            severity="fatal",
            documents=(WorkflowDocumentRef(entity_name="Python"),),
            cause=db_error,
        )

        assert error.action == "fail_model"
        assert error.severity == "fatal"
        assert error.root_cause() is db_error

        payload = error.to_event_payload()
        assert payload["cause_type"] == "Exception"
        assert "UNIQUE constraint" in payload["cause_message"]

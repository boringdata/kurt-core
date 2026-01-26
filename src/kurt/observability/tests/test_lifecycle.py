"""Tests for workflow lifecycle tracking module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from kurt.db.dolt import DoltDB, DoltQueryError, QueryResult
from kurt.observability.lifecycle import (
    InvalidStatusTransition,
    LifecycleError,
    RunNotFoundError,
    StepLogNotFoundError,
    StepSummary,
    WorkflowLifecycle,
)


class TestWorkflowLifecycleCreateRun:
    """Tests for WorkflowLifecycle.create_run()."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock DoltDB."""
        db = MagicMock(spec=DoltDB)
        db.execute.return_value = QueryResult(rows=[], affected_rows=1)
        return db

    def test_creates_run_with_defaults(self, mock_db):
        """Should create run with default status='running'."""
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)
        run_id = lifecycle.create_run("map_workflow")

        assert run_id is not None
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        assert "INSERT INTO workflow_runs" in call_args[0][0]
        params = call_args[0][1]
        assert params[1] == "map_workflow"  # workflow
        assert params[2] == "running"  # status

    def test_creates_run_with_inputs(self, mock_db):
        """Should store inputs as JSON."""
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)
        inputs = {"url": "https://example.com", "max_pages": 100}
        lifecycle.create_run("map_workflow", inputs=inputs)

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert json.loads(params[4]) == inputs  # inputs JSON

    def test_creates_run_with_metadata(self, mock_db):
        """Should store metadata as JSON."""
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)
        metadata = {"user_id": "user-123", "source": "cli"}
        lifecycle.create_run("map_workflow", metadata=metadata)

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert json.loads(params[5]) == metadata  # metadata JSON

    def test_uses_provided_run_id(self, mock_db):
        """Should use provided run_id instead of generating UUID."""
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)
        run_id = lifecycle.create_run("map_workflow", run_id="custom-run-id")

        assert run_id == "custom-run-id"
        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[0] == "custom-run-id"

    def test_propagates_db_error(self, mock_db):
        """Should propagate DoltQueryError."""
        mock_db.execute.side_effect = DoltQueryError("Insert failed")
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)

        with pytest.raises(DoltQueryError, match="Insert failed"):
            lifecycle.create_run("map_workflow")


class TestWorkflowLifecycleUpdateStatus:
    """Tests for WorkflowLifecycle.update_status()."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock DoltDB."""
        db = MagicMock(spec=DoltDB)
        db.execute.return_value = QueryResult(rows=[], affected_rows=1)
        return db

    def test_valid_transition_running_to_completed(self, mock_db):
        """Should allow running -> completed transition."""
        mock_db.query_one.return_value = {"status": "running", "metadata": None}
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)

        lifecycle.update_status("run-123", "completed")

        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        assert "status = ?" in call_args[0][0]
        assert "completed_at = ?" in call_args[0][0]

    def test_valid_transition_running_to_failed(self, mock_db):
        """Should allow running -> failed transition with error."""
        mock_db.query_one.return_value = {"status": "running", "metadata": None}
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)

        lifecycle.update_status("run-123", "failed", error="Fetch timed out")

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[0] == "failed"
        assert "Fetch timed out" in params

    def test_valid_transition_running_to_canceling(self, mock_db):
        """Should allow running -> canceling transition."""
        mock_db.query_one.return_value = {"status": "running", "metadata": None}
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)

        lifecycle.update_status("run-123", "canceling")

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[0] == "canceling"

    def test_valid_transition_canceling_to_canceled(self, mock_db):
        """Should allow canceling -> canceled transition."""
        mock_db.query_one.return_value = {"status": "canceling", "metadata": None}
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)

        lifecycle.update_status("run-123", "canceled")

        call_args = mock_db.execute.call_args
        assert "completed_at = ?" in call_args[0][0]

    def test_invalid_transition_completed_to_running(self, mock_db):
        """Should reject completed -> running transition."""
        mock_db.query_one.return_value = {"status": "completed", "metadata": None}
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)

        with pytest.raises(InvalidStatusTransition) as exc_info:
            lifecycle.update_status("run-123", "running")

        assert exc_info.value.current == "completed"
        assert exc_info.value.target == "running"

    def test_invalid_transition_failed_to_running(self, mock_db):
        """Should reject failed -> running transition."""
        mock_db.query_one.return_value = {"status": "failed", "metadata": None}
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)

        with pytest.raises(InvalidStatusTransition):
            lifecycle.update_status("run-123", "running")

    def test_invalid_transition_canceled_to_running(self, mock_db):
        """Should reject canceled -> running transition."""
        mock_db.query_one.return_value = {"status": "canceled", "metadata": None}
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)

        with pytest.raises(InvalidStatusTransition):
            lifecycle.update_status("run-123", "running")

    def test_run_not_found(self, mock_db):
        """Should raise RunNotFoundError if run doesn't exist."""
        mock_db.query_one.return_value = None
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)

        with pytest.raises(RunNotFoundError) as exc_info:
            lifecycle.update_status("nonexistent-run", "completed")

        assert exc_info.value.run_id == "nonexistent-run"

    def test_merges_metadata(self, mock_db):
        """Should merge new metadata with existing."""
        mock_db.query_one.return_value = {
            "status": "running",
            "metadata": '{"existing": "value"}',
        }
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)

        lifecycle.update_status("run-123", "completed", metadata={"new": "data"})

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        # Find the metadata param (after status and completed_at)
        metadata_param = next(p for p in params if isinstance(p, str) and p.startswith("{"))
        merged = json.loads(metadata_param)
        assert merged["existing"] == "value"
        assert merged["new"] == "data"


class TestWorkflowLifecycleStepLogs:
    """Tests for step log methods."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock DoltDB."""
        db = MagicMock(spec=DoltDB)
        db.execute.return_value = QueryResult(rows=[], affected_rows=1)
        return db

    def test_create_step_log(self, mock_db):
        """Should insert step log with correct fields."""
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)
        step_log_id = lifecycle.create_step_log(
            run_id="run-123",
            step_id="fetch",
            tool="FetchTool",
            input_count=50,
        )

        assert step_log_id is not None
        call_args = mock_db.execute.call_args
        assert "INSERT INTO step_logs" in call_args[0][0]
        params = call_args[0][1]
        assert params[1] == "run-123"  # run_id
        assert params[2] == "fetch"  # step_id
        assert params[3] == "FetchTool"  # tool
        assert params[4] == "running"  # status
        assert params[6] == 50  # input_count

    def test_update_step_log_completed(self, mock_db):
        """Should update step log with output counts."""
        mock_db.query_one.return_value = {"status": "running", "metadata": None}
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)

        lifecycle.update_step_log(
            run_id="run-123",
            step_id="fetch",
            status="completed",
            output_count=95,
            error_count=5,
        )

        call_args = mock_db.execute.call_args
        assert "UPDATE step_logs" in call_args[0][0]
        assert "status = ?" in call_args[0][0]
        assert "completed_at = ?" in call_args[0][0]
        assert "output_count = ?" in call_args[0][0]

    def test_update_step_log_with_errors(self, mock_db):
        """Should store error details as JSON."""
        mock_db.query_one.return_value = {"status": "running", "metadata": None}
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)

        errors = [
            {"row_idx": 3, "error_type": "timeout", "message": "Request timed out"},
            {"row_idx": 12, "error_type": "http_error", "message": "404 Not Found"},
        ]
        lifecycle.update_step_log(
            run_id="run-123",
            step_id="fetch",
            status="completed",
            output_count=98,
            error_count=2,
            errors=errors,
        )

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        # Find the errors JSON param
        errors_param = next(p for p in params if isinstance(p, str) and "row_idx" in p)
        assert json.loads(errors_param) == errors

    def test_step_log_not_found(self, mock_db):
        """Should raise StepLogNotFoundError if step doesn't exist."""
        mock_db.query_one.return_value = None
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)

        with pytest.raises(StepLogNotFoundError) as exc_info:
            lifecycle.update_step_log("run-123", "nonexistent", status="completed")

        assert exc_info.value.run_id == "run-123"
        assert exc_info.value.step_id == "nonexistent"

    def test_invalid_step_status_transition(self, mock_db):
        """Should reject invalid step status transitions."""
        mock_db.query_one.return_value = {"status": "completed", "metadata": None}
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)

        with pytest.raises(InvalidStatusTransition) as exc_info:
            lifecycle.update_step_log("run-123", "fetch", status="running")

        assert exc_info.value.entity == "step"


class TestWorkflowLifecycleCallbacks:
    """Tests for convenience callback methods."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock DoltDB."""
        db = MagicMock(spec=DoltDB)
        db.execute.return_value = QueryResult(rows=[], affected_rows=1)
        db.query_one.return_value = {"status": "running", "metadata": None}
        return db

    def test_on_workflow_start(self, mock_db):
        """Should create run with running status."""
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)
        run_id = lifecycle.on_workflow_start("map_workflow", {"url": "example.com"})

        assert run_id is not None
        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[2] == "running"

    def test_on_step_start(self, mock_db):
        """Should create step log with running status."""
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)
        step_id = lifecycle.on_step_start("run-123", "fetch", "FetchTool", input_count=50)

        assert step_id is not None
        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[4] == "running"

    def test_on_step_complete(self, mock_db):
        """Should update step with completed status."""
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)
        lifecycle.on_step_complete("run-123", "fetch", output_count=95)

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[0] == "completed"

    def test_on_step_complete_with_errors(self, mock_db):
        """Should store non-fatal errors."""
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)
        errors = [{"row_idx": 3, "error_type": "timeout", "message": "Timed out"}]
        lifecycle.on_step_complete("run-123", "fetch", output_count=99, errors=errors)

        call_args = mock_db.execute.call_args
        assert "error_count = ?" in call_args[0][0]

    def test_on_step_fail(self, mock_db):
        """Should update step with failed status and error."""
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)
        lifecycle.on_step_fail("run-123", "fetch", "Connection refused")

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[0] == "failed"

    def test_on_workflow_complete(self, mock_db):
        """Should update workflow with completed status."""
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)
        lifecycle.on_workflow_complete("run-123")

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[0] == "completed"

    def test_on_workflow_fail(self, mock_db):
        """Should update workflow with failed status and error."""
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)
        lifecycle.on_workflow_fail("run-123", "Step fetch failed")

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[0] == "failed"
        assert "Step fetch failed" in params


class TestWorkflowLifecycleEventEmission:
    """Tests for event emission integration."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock DoltDB."""
        db = MagicMock(spec=DoltDB)
        db.execute.return_value = QueryResult(rows=[], affected_rows=1, last_insert_id=1)
        db.query_one.return_value = {"status": "running", "metadata": None}
        return db

    def test_emits_event_on_create_run(self, mock_db):
        """Should emit event when creating run."""
        lifecycle = WorkflowLifecycle(mock_db, emit_events=True)
        lifecycle.create_run("map_workflow")

        # Should have called execute twice: INSERT run + INSERT event
        assert mock_db.execute.call_count == 2
        event_call = mock_db.execute.call_args_list[1]
        assert "INSERT INTO step_events" in event_call[0][0]

    def test_emits_event_on_status_change(self, mock_db):
        """Should emit event when status changes."""
        lifecycle = WorkflowLifecycle(mock_db, emit_events=True)
        lifecycle.update_status("run-123", "completed")

        # Should have called execute for UPDATE + INSERT event
        assert mock_db.execute.call_count == 2

    def test_uses_tracker_if_provided(self, mock_db):
        """Should use EventTracker if provided."""
        from kurt.observability.tracking import EventTracker

        mock_tracker = MagicMock(spec=EventTracker)
        mock_tracker._running = True

        lifecycle = WorkflowLifecycle(mock_db, tracker=mock_tracker, emit_events=True)
        lifecycle.create_run("map_workflow")

        mock_tracker.track.assert_called_once()

    def test_no_events_when_disabled(self, mock_db):
        """Should not emit events when emit_events=False."""
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)
        lifecycle.create_run("map_workflow")

        # Should only have called execute once (INSERT run)
        assert mock_db.execute.call_count == 1


class TestWorkflowLifecycleGetMethods:
    """Tests for get methods."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock DoltDB."""
        db = MagicMock(spec=DoltDB)
        return db

    def test_get_run(self, mock_db):
        """Should return run data."""
        mock_db.query_one.return_value = {
            "id": "run-123",
            "workflow": "map_workflow",
            "status": "completed",
        }
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)

        result = lifecycle.get_run("run-123")

        assert result["id"] == "run-123"
        assert result["workflow"] == "map_workflow"

    def test_get_run_not_found(self, mock_db):
        """Should return None for nonexistent run."""
        mock_db.query_one.return_value = None
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)

        result = lifecycle.get_run("nonexistent")

        assert result is None

    def test_get_step_log(self, mock_db):
        """Should return step log data."""
        mock_db.query_one.return_value = {
            "id": "step-123",
            "run_id": "run-123",
            "step_id": "fetch",
            "status": "completed",
        }
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)

        result = lifecycle.get_step_log("run-123", "fetch")

        assert result["step_id"] == "fetch"

    def test_get_step_logs(self, mock_db):
        """Should return all step logs for a run."""
        mock_db.query.return_value = QueryResult(rows=[
            {"step_id": "fetch", "status": "completed"},
            {"step_id": "extract", "status": "running"},
        ])
        lifecycle = WorkflowLifecycle(mock_db, emit_events=False)

        result = lifecycle.get_step_logs("run-123")

        assert len(result) == 2
        assert result[0]["step_id"] == "fetch"
        assert result[1]["step_id"] == "extract"


class TestStepSummary:
    """Tests for StepSummary dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        summary = StepSummary()
        assert summary.input_count is None
        assert summary.output_count is None
        assert summary.error_count == 0
        assert summary.errors == []
        assert summary.metadata == {}

    def test_with_values(self):
        """Should store provided values."""
        summary = StepSummary(
            input_count=100,
            output_count=95,
            error_count=5,
            errors=[{"row_idx": 1, "error_type": "timeout", "message": "Timed out"}],
            metadata={"duration_ms": 5000},
        )
        assert summary.input_count == 100
        assert summary.output_count == 95
        assert summary.error_count == 5
        assert len(summary.errors) == 1
        assert summary.metadata["duration_ms"] == 5000


class TestExceptions:
    """Tests for exception classes."""

    def test_lifecycle_error(self):
        """Should be base exception."""
        error = LifecycleError("Something went wrong")
        assert str(error) == "Something went wrong"

    def test_invalid_status_transition(self):
        """Should include current and target status."""
        error = InvalidStatusTransition("completed", "running", "workflow")
        assert error.current == "completed"
        assert error.target == "running"
        assert error.entity == "workflow"
        assert "completed -> running" in str(error)

    def test_run_not_found_error(self):
        """Should include run_id."""
        error = RunNotFoundError("run-123")
        assert error.run_id == "run-123"
        assert "run-123" in str(error)

    def test_step_log_not_found_error(self):
        """Should include run_id and step_id."""
        error = StepLogNotFoundError("run-123", "fetch")
        assert error.run_id == "run-123"
        assert error.step_id == "fetch"
        assert "run-123" in str(error)
        assert "fetch" in str(error)

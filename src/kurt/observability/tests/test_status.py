"""Tests for kurt.observability.status module."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from kurt.observability.status import (
    _build_steps_array,
    _calculate_duration,
    _determine_effective_status,
    _extract_stage_progress,
    _map_step_status,
    _parse_datetime,
    _parse_json_field,
    get_live_status,
)


class TestParseJsonField:
    """Tests for _parse_json_field helper."""

    def test_none_returns_none(self):
        assert _parse_json_field(None) is None

    def test_dict_returns_dict(self):
        data = {"key": "value"}
        assert _parse_json_field(data) == data

    def test_list_returns_list(self):
        data = [1, 2, 3]
        assert _parse_json_field(data) == data

    def test_json_string_parsed(self):
        data = '{"key": "value"}'
        assert _parse_json_field(data) == {"key": "value"}

    def test_invalid_json_returns_none(self):
        assert _parse_json_field("not valid json") is None


class TestParseDatetime:
    """Tests for _parse_datetime helper."""

    def test_none_returns_none(self):
        assert _parse_datetime(None) is None

    def test_datetime_passthrough(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        assert _parse_datetime(dt) == dt

    def test_iso_format(self):
        result = _parse_datetime("2024-01-15T10:30:00")
        assert result == datetime(2024, 1, 15, 10, 30, 0)

    def test_space_format(self):
        result = _parse_datetime("2024-01-15 10:30:00")
        assert result == datetime(2024, 1, 15, 10, 30, 0)

    def test_with_microseconds(self):
        result = _parse_datetime("2024-01-15 10:30:00.123456")
        assert result is not None
        assert result.microsecond == 123456


class TestMapStepStatus:
    """Tests for _map_step_status helper."""

    def test_completed_to_success(self):
        assert _map_step_status("completed") == "success"

    def test_failed_to_error(self):
        assert _map_step_status("failed") == "error"

    def test_running_unchanged(self):
        assert _map_step_status("running") == "running"

    def test_pending_unchanged(self):
        assert _map_step_status("pending") == "pending"

    def test_unknown_passthrough(self):
        assert _map_step_status("unknown_status") == "unknown_status"


class TestDetermineEffectiveStatus:
    """Tests for _determine_effective_status helper."""

    def test_completed_no_errors(self):
        steps = [{"error": 0}, {"error": 0}]
        assert _determine_effective_status("completed", steps) == "completed"

    def test_completed_with_errors(self):
        steps = [{"error": 0}, {"error": 5}]
        assert _determine_effective_status("completed", steps) == "completed_with_errors"

    def test_failed_unchanged(self):
        steps = [{"error": 0}]
        assert _determine_effective_status("failed", steps) == "failed"

    def test_running_unchanged(self):
        steps = [{"error": 5}]
        assert _determine_effective_status("running", steps) == "running"


class TestCalculateDuration:
    """Tests for _calculate_duration helper."""

    def test_no_started_at(self):
        row = {"started_at": None}
        assert _calculate_duration(row) is None

    def test_completed_workflow(self):
        now = datetime.utcnow()
        start = now - timedelta(seconds=10)
        row = {
            "started_at": start.strftime("%Y-%m-%d %H:%M:%S"),
            "completed_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        }
        duration = _calculate_duration(row)
        assert duration is not None
        assert 9000 <= duration <= 11000  # ~10 seconds in ms

    def test_running_workflow(self):
        start = datetime.utcnow() - timedelta(seconds=5)
        row = {
            "started_at": start.strftime("%Y-%m-%d %H:%M:%S"),
            "completed_at": None,
        }
        duration = _calculate_duration(row)
        assert duration is not None
        assert duration >= 4000  # At least ~4 seconds in ms


class TestBuildStepsArray:
    """Tests for _build_steps_array helper."""

    def test_empty_logs(self):
        assert _build_steps_array([]) == []

    def test_single_step(self):
        logs = [{
            "step_id": "fetch",
            "tool": "FetchTool",
            "status": "completed",
            "started_at": "2024-01-15 10:00:00",
            "completed_at": "2024-01-15 10:01:00",
            "input_count": 100,
            "output_count": 95,
            "error_count": 5,
            "errors": json.dumps([{"message": "Timeout"}]),
            "metadata_json": None,
        }]
        steps = _build_steps_array(logs)

        assert len(steps) == 1
        step = steps[0]
        assert step["name"] == "fetch"
        assert step["status"] == "success"  # Mapped from "completed"
        assert step["success"] == 90  # output_count - error_count
        assert step["error"] == 5
        assert step["errors"] == ["Timeout"]
        assert step["duration_ms"] is not None
        assert step["duration_ms"] == 60000  # 1 minute in ms

    def test_step_type_from_metadata(self):
        logs = [{
            "step_id": "queue_step",
            "tool": "QueueTool",
            "status": "running",
            "started_at": "2024-01-15 10:00:00",
            "completed_at": None,
            "input_count": 10,
            "output_count": 0,
            "error_count": 0,
            "errors": None,
            "metadata_json": json.dumps({"step_type": "queue"}),
        }]
        steps = _build_steps_array(logs)

        assert steps[0]["step_type"] == "queue"


class TestExtractStageProgress:
    """Tests for _extract_stage_progress helper."""

    def test_empty_inputs(self):
        stage, progress = _extract_stage_progress([], [])
        assert stage is None
        assert progress == {"current": 0, "total": 0}

    def test_running_step_as_stage(self):
        steps = [
            {"name": "fetch", "status": "success"},
            {"name": "extract", "status": "running"},
        ]
        stage, progress = _extract_stage_progress([], steps)
        assert stage == "extract"

    def test_progress_from_events(self):
        events = [{
            "step_id": "fetch",
            "current": 50,
            "total": 100,
            "metadata_json": None,
        }]
        stage, progress = _extract_stage_progress(events, [])
        assert progress == {"current": 50, "total": 100}
        assert stage == "fetch"


class TestGetLiveStatus:
    """Tests for get_live_status function."""

    def test_workflow_not_found(self):
        """Test returns None when workflow not found."""
        db = MagicMock()
        db.query.return_value = MagicMock(rows=[])

        result = get_live_status(db, "nonexistent")
        assert result is None

    def test_full_workflow_status(self):
        """Test complete workflow status response."""
        db = MagicMock()

        # Mock workflow run query
        workflow_result = MagicMock()
        workflow_result.rows = [{
            "id": "abc-123-def-456",
            "workflow": "map_workflow",
            "status": "completed",
            "started_at": "2024-01-15 10:00:00",
            "completed_at": "2024-01-15 10:05:00",
            "error": None,
            "inputs": json.dumps({"url": "https://example.com"}),
            "metadata_json": json.dumps({"cli_command": "kurt content map https://example.com"}),
        }]

        # Mock step logs query
        step_result = MagicMock()
        step_result.rows = [{
            "step_id": "fetch",
            "tool": "FetchTool",
            "status": "completed",
            "started_at": "2024-01-15 10:01:00",
            "completed_at": "2024-01-15 10:04:00",
            "input_count": 10,
            "output_count": 10,
            "error_count": 0,
            "errors": None,
            "metadata_json": None,
        }]

        # Mock events query
        events_result = MagicMock()
        events_result.rows = []

        # Configure mock to return different results for different queries
        def query_side_effect(sql, params=None):
            if "workflow_runs" in sql:
                return workflow_result
            elif "step_logs" in sql:
                return step_result
            else:
                return events_result

        db.query.side_effect = query_side_effect

        result = get_live_status(db, "abc-123")

        assert result is not None
        assert result["workflow_id"] == "abc-123-def-456"
        assert result["name"] == "map_workflow"
        assert result["status"] == "completed"
        assert result["cli_command"] == "kurt content map https://example.com"
        assert result["inputs"] == {"url": "https://example.com"}
        assert result["duration_ms"] == 300000  # 5 minutes
        assert len(result["steps"]) == 1
        assert result["steps"][0]["name"] == "fetch"
        assert result["steps"][0]["success"] == 10

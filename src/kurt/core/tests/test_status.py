"""
Unit tests for status module.

Tests workflow status reading from DBOS tables (workflow_events, streams).
These tests catch issues like session.exec() vs session.execute() for raw SQL.
"""

from __future__ import annotations

import base64
import pickle
from typing import Any

import pytest
from sqlalchemy import text

from kurt.core.status import (
    _decode_dbos_value,
    format_live_status,
    format_step_logs,
    get_live_status,
    get_step_logs,
    paginate_stream,
    read_workflow_events,
    read_workflow_streams,
)
from kurt.db import managed_session

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def dbos_tables(dbos_launched):
    """
    Use dbos_launched fixture which properly initializes DBOS and creates
    all its tables (workflow_events, streams, etc.) in the test database.

    This ensures we test against real DBOS table schemas and catches issues
    like session.exec() vs session.execute() for raw SQL queries.
    """
    yield dbos_launched


def _encode_value(value: Any) -> bytes:
    """Encode a value like DBOS does (pickle + base64)."""
    return base64.b64encode(pickle.dumps(value))


def _insert_event(workflow_id: str, key: str, value: Any) -> None:
    """Insert a workflow event."""
    with managed_session() as session:
        session.execute(
            text(
                "INSERT OR REPLACE INTO workflow_events (workflow_uuid, key, value) VALUES (:wf, :key, :val)"
            ),
            {"wf": workflow_id, "key": key, "val": _encode_value(value)},
        )
        session.commit()


def _insert_stream(workflow_id: str, key: str, value: Any, offset: int) -> None:
    """Insert a stream entry."""
    with managed_session() as session:
        session.execute(
            text(
                'INSERT INTO streams (workflow_uuid, key, value, "offset") VALUES (:wf, :key, :val, :offset)'
            ),
            {"wf": workflow_id, "key": key, "val": _encode_value(value), "offset": offset},
        )
        session.commit()


# ============================================================================
# Decode Tests
# ============================================================================


class TestDecodeDbosValue:
    """Tests for _decode_dbos_value helper."""

    def test_decode_none(self):
        """Test decoding None."""
        assert _decode_dbos_value(None) is None

    def test_decode_base64_pickled_string(self):
        """Test decoding base64-encoded pickled value."""
        original = "hello world"
        encoded = base64.b64encode(pickle.dumps(original))
        assert _decode_dbos_value(encoded) == original

    def test_decode_base64_pickled_dict(self):
        """Test decoding base64-encoded pickled dict."""
        original = {"status": "running", "count": 42}
        encoded = base64.b64encode(pickle.dumps(original))
        assert _decode_dbos_value(encoded) == original

    def test_decode_raw_pickled_bytes(self):
        """Test decoding raw pickled bytes (no base64)."""
        original = {"key": "value"}
        encoded = pickle.dumps(original)
        assert _decode_dbos_value(encoded) == original

    def test_decode_plain_string(self):
        """Test that plain strings pass through."""
        assert _decode_dbos_value("plain text") == "plain text"

    def test_decode_memoryview(self):
        """Test decoding memoryview (SQLite returns this for BLOB)."""
        original = {"test": True}
        encoded = base64.b64encode(pickle.dumps(original))
        mv = memoryview(encoded)
        assert _decode_dbos_value(mv) == original


# ============================================================================
# Read Workflow Events Tests
# ============================================================================


class TestReadWorkflowEvents:
    """Tests for read_workflow_events function."""

    def test_read_empty_events(self, dbos_tables):
        """Test reading events for non-existent workflow."""
        events = read_workflow_events("nonexistent-workflow")
        assert events == {}

    def test_read_single_event(self, dbos_tables):
        """Test reading a single event."""
        workflow_id = "test-workflow-1"
        _insert_event(workflow_id, "status", "running")

        events = read_workflow_events(workflow_id)
        assert events == {"status": "running"}

    def test_read_multiple_events(self, dbos_tables):
        """Test reading multiple events."""
        workflow_id = "test-workflow-2"
        _insert_event(workflow_id, "status", "completed")
        _insert_event(workflow_id, "current_step", "extract")
        _insert_event(workflow_id, "stage_total", 100)

        events = read_workflow_events(workflow_id)
        assert events["status"] == "completed"
        assert events["current_step"] == "extract"
        assert events["stage_total"] == 100

    def test_read_events_isolation(self, dbos_tables):
        """Test that events are isolated by workflow_id."""
        _insert_event("workflow-a", "status", "running")
        _insert_event("workflow-b", "status", "completed")

        events_a = read_workflow_events("workflow-a")
        events_b = read_workflow_events("workflow-b")

        assert events_a["status"] == "running"
        assert events_b["status"] == "completed"


# ============================================================================
# Read Workflow Streams Tests
# ============================================================================


class TestReadWorkflowStreams:
    """Tests for read_workflow_streams function."""

    def test_read_empty_streams(self, dbos_tables):
        """Test reading streams for non-existent workflow."""
        streams = read_workflow_streams("nonexistent-workflow")
        assert streams == []

    def test_read_single_stream_entry(self, dbos_tables):
        """Test reading a single stream entry."""
        workflow_id = "test-workflow-3"
        _insert_stream(workflow_id, "progress", {"step": "extract", "idx": 0}, offset=1)

        streams = read_workflow_streams(workflow_id)
        assert len(streams) == 1
        assert streams[0]["key"] == "progress"
        assert streams[0]["step"] == "extract"
        assert streams[0]["offset"] == 1

    def test_read_multiple_stream_entries(self, dbos_tables):
        """Test reading multiple stream entries ordered by offset."""
        workflow_id = "test-workflow-4"
        _insert_stream(workflow_id, "progress", {"idx": 2}, offset=3)
        _insert_stream(workflow_id, "progress", {"idx": 0}, offset=1)
        _insert_stream(workflow_id, "progress", {"idx": 1}, offset=2)

        streams = read_workflow_streams(workflow_id)
        assert len(streams) == 3
        # Should be ordered by offset
        assert streams[0]["idx"] == 0
        assert streams[1]["idx"] == 1
        assert streams[2]["idx"] == 2

    def test_read_streams_filter_by_key(self, dbos_tables):
        """Test filtering streams by key."""
        workflow_id = "test-workflow-5"
        _insert_stream(workflow_id, "progress", {"step": "extract"}, offset=1)
        _insert_stream(workflow_id, "logs", {"message": "hello"}, offset=2)
        _insert_stream(workflow_id, "progress", {"step": "transform"}, offset=3)

        progress = read_workflow_streams(workflow_id, key="progress")
        logs = read_workflow_streams(workflow_id, key="logs")

        assert len(progress) == 2
        assert len(logs) == 1
        assert logs[0]["message"] == "hello"

    def test_read_streams_since_offset(self, dbos_tables):
        """Test reading streams since a specific offset."""
        workflow_id = "test-workflow-6"
        _insert_stream(workflow_id, "progress", {"idx": 0}, offset=1)
        _insert_stream(workflow_id, "progress", {"idx": 1}, offset=2)
        _insert_stream(workflow_id, "progress", {"idx": 2}, offset=3)

        streams = read_workflow_streams(workflow_id, since_offset=1)
        assert len(streams) == 2
        assert streams[0]["idx"] == 1
        assert streams[1]["idx"] == 2

    def test_read_streams_with_limit(self, dbos_tables):
        """Test reading streams with limit."""
        workflow_id = "test-workflow-7"
        for i in range(5):
            _insert_stream(workflow_id, "progress", {"idx": i}, offset=i + 1)

        streams = read_workflow_streams(workflow_id, limit=2)
        assert len(streams) == 2
        assert streams[0]["idx"] == 0
        assert streams[1]["idx"] == 1


# ============================================================================
# Paginate Stream Tests
# ============================================================================


class TestPaginateStream:
    """Tests for paginate_stream function."""

    def test_paginate_empty(self, dbos_tables):
        """Test paginating empty stream."""
        result = paginate_stream("nonexistent")
        assert result["items"] == []
        assert result["next_offset"] is None
        assert result["has_more"] is False

    def test_paginate_with_items(self, dbos_tables):
        """Test pagination with items."""
        workflow_id = "test-paginate-1"
        for i in range(5):
            _insert_stream(workflow_id, "progress", {"idx": i}, offset=i + 1)

        result = paginate_stream(workflow_id, limit=3)
        assert len(result["items"]) == 3
        assert result["next_offset"] == 3
        assert result["has_more"] is True

    def test_paginate_last_page(self, dbos_tables):
        """Test pagination on last page."""
        workflow_id = "test-paginate-2"
        for i in range(3):
            _insert_stream(workflow_id, "progress", {"idx": i}, offset=i + 1)

        result = paginate_stream(workflow_id, limit=5)
        assert len(result["items"]) == 3
        assert result["next_offset"] == 3
        assert result["has_more"] is False


# ============================================================================
# Get Step Logs Tests
# ============================================================================


class TestGetStepLogs:
    """Tests for get_step_logs function."""

    def test_get_logs_empty(self, dbos_tables):
        """Test getting logs for workflow with no logs."""
        logs = get_step_logs("nonexistent")
        assert logs == []

    def test_get_logs_all(self, dbos_tables):
        """Test getting all logs."""
        workflow_id = "test-logs-1"
        _insert_stream(workflow_id, "logs", {"message": "log1", "step": "extract"}, offset=1)
        _insert_stream(workflow_id, "logs", {"message": "log2", "step": "transform"}, offset=2)

        logs = get_step_logs(workflow_id)
        assert len(logs) == 2

    def test_get_logs_filter_by_step(self, dbos_tables):
        """Test filtering logs by step name."""
        workflow_id = "test-logs-2"
        _insert_stream(workflow_id, "logs", {"message": "log1", "step": "extract"}, offset=1)
        _insert_stream(workflow_id, "logs", {"message": "log2", "step": "transform"}, offset=2)
        _insert_stream(workflow_id, "logs", {"message": "log3", "step": "extract"}, offset=3)

        logs = get_step_logs(workflow_id, step_name="extract")
        assert len(logs) == 2
        assert all(log["step"] == "extract" for log in logs)


# ============================================================================
# Get Live Status Tests
# ============================================================================


class TestGetLiveStatus:
    """Tests for get_live_status function."""

    def test_get_status_empty_workflow(self, dbos_tables):
        """Test status for workflow with no events."""
        status = get_live_status("nonexistent")
        assert status["workflow_id"] == "nonexistent"
        assert status["status"] == "unknown"
        assert status["steps"] == []

    def test_get_status_with_events(self, dbos_tables):
        """Test status with workflow events."""
        workflow_id = "test-status-1"
        _insert_event(workflow_id, "status", "running")
        _insert_event(workflow_id, "current_step", "extract")
        _insert_event(workflow_id, "stage_current", 5)
        _insert_event(workflow_id, "stage_total", 10)

        status = get_live_status(workflow_id)
        assert status["status"] == "running"
        assert status["current_step"] == "extract"
        assert status["progress"]["current"] == 5
        assert status["progress"]["total"] == 10

    def test_get_status_with_progress_streams(self, dbos_tables):
        """Test status with progress stream entries."""
        workflow_id = "test-status-2"
        _insert_event(workflow_id, "status", "running")
        _insert_stream(
            workflow_id,
            "progress",
            {"step": "extract", "idx": 0, "total": 3, "status": "success", "timestamp": 1000},
            offset=1,
        )
        _insert_stream(
            workflow_id,
            "progress",
            {"step": "extract", "idx": 1, "total": 3, "status": "success", "timestamp": 1001},
            offset=2,
        )

        status = get_live_status(workflow_id)
        assert len(status["steps"]) == 1
        step = status["steps"][0]
        assert step["name"] == "extract"
        assert step["success"] == 2
        assert step["total"] == 3


# ============================================================================
# Format Tests
# ============================================================================


class TestFormatLiveStatus:
    """Tests for format_live_status function."""

    def test_format_basic_status(self):
        """Test formatting basic status."""
        status = {
            "workflow_id": "test-123",
            "status": "running",
            "current_step": "extract",
            "progress": {"current": 5, "total": 10},
            "steps": [],
        }
        output = format_live_status(status)
        assert "test-123" in output
        assert "running" in output
        assert "extract" in output
        assert "5/10" in output

    def test_format_with_steps(self):
        """Test formatting status with steps."""
        status = {
            "workflow_id": "test-123",
            "status": "running",
            "current_step": "extract",
            "progress": {"current": 5, "total": 10},
            "steps": [
                {"name": "extract", "status": "completed", "current": 10, "total": 10},
                {"name": "transform", "status": "running", "current": 3, "total": 5},
            ],
        }
        output = format_live_status(status)
        assert "extract" in output
        assert "transform" in output
        assert "completed" in output


class TestFormatStepLogs:
    """Tests for format_step_logs function."""

    def test_format_empty_logs(self):
        """Test formatting empty logs."""
        output = format_step_logs([])
        assert output == ""

    def test_format_logs(self):
        """Test formatting logs."""
        logs = [
            {"timestamp": 1000, "level": "info", "step": "extract", "message": "Processing item 1"},
            {"timestamp": 1001, "level": "error", "step": "extract", "message": "Failed"},
        ]
        output = format_step_logs(logs)
        assert "[info]" in output
        assert "[error]" in output
        assert "Processing item 1" in output
        assert "Failed" in output

"""Tests for status streaming module."""

from __future__ import annotations

import json
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from kurt.db.dolt import DoltDB, QueryResult
from kurt.observability.streaming import (
    DEFAULT_BATCH_LIMIT,
    DEFAULT_POLL_MS,
    TERMINAL_STATUSES,
    StatusStreamer,
    StepEvent,
    format_event,
    stream_events,
)


class TestStepEvent:
    """Tests for StepEvent dataclass."""

    def test_from_row_basic(self):
        """Should create StepEvent from basic row."""
        row = {
            "id": 42,
            "run_id": "run-123",
            "step_id": "map",
            "substep": "fetch",
            "status": "progress",
            "created_at": "2024-01-15T10:00:00",
            "current": 5,
            "total": 10,
            "message": "Processing",
            "metadata": None,
        }
        event = StepEvent.from_row(row)

        assert event.id == 42
        assert event.run_id == "run-123"
        assert event.step_id == "map"
        assert event.substep == "fetch"
        assert event.status == "progress"
        assert event.current == 5
        assert event.total == 10
        assert event.message == "Processing"
        assert event.metadata is None

    def test_from_row_with_metadata_string(self):
        """Should parse JSON metadata string."""
        row = {
            "id": 1,
            "run_id": "run-123",
            "step_id": "map",
            "substep": None,
            "status": "running",
            "created_at": None,
            "current": None,
            "total": None,
            "message": None,
            "metadata": '{"url": "https://example.com", "batch": 1}',
        }
        event = StepEvent.from_row(row)

        assert event.metadata == {"url": "https://example.com", "batch": 1}

    def test_from_row_with_metadata_dict(self):
        """Should accept dict metadata directly."""
        row = {
            "id": 1,
            "run_id": "run-123",
            "step_id": "map",
            "substep": None,
            "status": "running",
            "created_at": None,
            "current": None,
            "total": None,
            "message": None,
            "metadata": {"key": "value"},
        }
        event = StepEvent.from_row(row)

        assert event.metadata == {"key": "value"}

    def test_from_row_with_datetime_object(self):
        """Should handle datetime object."""
        dt = datetime(2024, 1, 15, 10, 0, 0)
        row = {
            "id": 1,
            "run_id": "run-123",
            "step_id": "map",
            "substep": None,
            "status": "running",
            "created_at": dt,
            "current": None,
            "total": None,
            "message": None,
            "metadata": None,
        }
        event = StepEvent.from_row(row)

        assert event.created_at == dt

    def test_from_row_with_iso_timestamp(self):
        """Should parse ISO format timestamp."""
        row = {
            "id": 1,
            "run_id": "run-123",
            "step_id": "map",
            "substep": None,
            "status": "running",
            "created_at": "2024-01-15T10:00:00Z",
            "current": None,
            "total": None,
            "message": None,
            "metadata": None,
        }
        event = StepEvent.from_row(row)

        assert event.created_at is not None
        assert event.created_at.year == 2024
        assert event.created_at.month == 1
        assert event.created_at.day == 15

    def test_to_dict(self):
        """Should convert to dict for JSON serialization."""
        event = StepEvent(
            id=42,
            run_id="run-123",
            step_id="map",
            substep="fetch",
            status="progress",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            current=5,
            total=10,
            message="Processing",
            metadata={"key": "value"},
        )
        result = event.to_dict()

        assert result["id"] == 42
        assert result["run_id"] == "run-123"
        assert result["step_id"] == "map"
        assert result["substep"] == "fetch"
        assert result["status"] == "progress"
        assert result["current"] == 5
        assert result["total"] == 10
        assert result["message"] == "Processing"
        assert result["created_at"] == "2024-01-15T10:00:00"
        assert result["metadata"] == {"key": "value"}

    def test_to_dict_without_optional_fields(self):
        """Should handle missing optional fields."""
        event = StepEvent(
            id=1,
            run_id="run-123",
            step_id="map",
            substep=None,
            status="running",
            created_at=None,
            current=None,
            total=None,
            message=None,
            metadata=None,
        )
        result = event.to_dict()

        assert "created_at" not in result
        assert "metadata" not in result
        assert result["substep"] is None


class TestFormatEvent:
    """Tests for format_event function."""

    def test_basic_format(self):
        """Should format event with all fields."""
        event = StepEvent(
            id=1,
            run_id="run-123",
            step_id="fetch",
            substep="fetch_urls",
            status="progress",
            created_at=datetime(2024, 1, 15, 10, 0, 1),
            current=50,
            total=100,
            message="Fetching batch 2",
            metadata=None,
        )
        result = format_event(event)

        assert result == "[10:00:01] fetch/fetch_urls: progress [50/100] Fetching batch 2"

    def test_format_without_substep(self):
        """Should format without substep."""
        event = StepEvent(
            id=1,
            run_id="run-123",
            step_id="map",
            substep=None,
            status="running",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            current=0,
            total=100,
            message=None,
            metadata=None,
        )
        result = format_event(event)

        assert result == "[10:00:00] map: running [0/100]"

    def test_format_without_progress(self):
        """Should format without progress counts."""
        event = StepEvent(
            id=1,
            run_id="run-123",
            step_id="map",
            substep=None,
            status="running",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            current=None,
            total=None,
            message=None,
            metadata=None,
        )
        result = format_event(event)

        assert result == "[10:00:00] map: running"

    def test_format_with_current_only(self):
        """Should format with current only (no total)."""
        event = StepEvent(
            id=1,
            run_id="run-123",
            step_id="map",
            substep=None,
            status="progress",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            current=42,
            total=None,
            message=None,
            metadata=None,
        )
        result = format_event(event)

        assert result == "[10:00:00] map: progress [42]"

    def test_format_completed(self):
        """Should format completed status."""
        event = StepEvent(
            id=1,
            run_id="run-123",
            step_id="fetch",
            substep="fetch_urls",
            status="completed",
            created_at=datetime(2024, 1, 15, 10, 0, 3),
            current=100,
            total=100,
            message=None,
            metadata=None,
        )
        result = format_event(event)

        assert result == "[10:00:03] fetch/fetch_urls: completed [100/100]"

    def test_format_json_output(self):
        """Should return JSON when json_output=True."""
        event = StepEvent(
            id=42,
            run_id="run-123",
            step_id="map",
            substep="fetch",
            status="progress",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            current=5,
            total=10,
            message="Processing",
            metadata=None,
        )
        result = format_event(event, json_output=True)
        data = json.loads(result)

        assert data["id"] == 42
        assert data["step_id"] == "map"
        assert data["status"] == "progress"

    def test_format_uses_current_time_if_no_timestamp(self):
        """Should use current time if created_at is None."""
        event = StepEvent(
            id=1,
            run_id="run-123",
            step_id="map",
            substep=None,
            status="running",
            created_at=None,
            current=None,
            total=None,
            message=None,
            metadata=None,
        )
        result = format_event(event)

        # Should contain a timestamp in HH:MM:SS format
        assert result.startswith("[")
        assert "] map: running" in result


class TestStatusStreamer:
    """Tests for StatusStreamer class."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock DoltDB."""
        db = MagicMock(spec=DoltDB)
        return db

    def test_init_defaults(self, mock_db):
        """Should initialize with default values."""
        streamer = StatusStreamer(mock_db)

        assert streamer._poll_ms == DEFAULT_POLL_MS
        assert streamer._batch_limit == DEFAULT_BATCH_LIMIT

    def test_init_custom_values(self, mock_db):
        """Should accept custom poll_ms and batch_limit."""
        streamer = StatusStreamer(mock_db, poll_ms=250, batch_limit=50)

        assert streamer._poll_ms == 250
        assert streamer._batch_limit == 50

    def test_is_workflow_terminated_completed(self, mock_db):
        """Should return True for completed workflow."""
        mock_db.query_one.return_value = {"status": "completed"}

        streamer = StatusStreamer(mock_db)
        result = streamer._is_workflow_terminated("run-123")

        assert result is True
        mock_db.query_one.assert_called_once()

    def test_is_workflow_terminated_failed(self, mock_db):
        """Should return True for failed workflow."""
        mock_db.query_one.return_value = {"status": "failed"}

        streamer = StatusStreamer(mock_db)
        result = streamer._is_workflow_terminated("run-123")

        assert result is True

    def test_is_workflow_terminated_canceled(self, mock_db):
        """Should return True for canceled workflow."""
        mock_db.query_one.return_value = {"status": "canceled"}

        streamer = StatusStreamer(mock_db)
        result = streamer._is_workflow_terminated("run-123")

        assert result is True

    def test_is_workflow_terminated_running(self, mock_db):
        """Should return False for running workflow."""
        mock_db.query_one.return_value = {"status": "running"}

        streamer = StatusStreamer(mock_db)
        result = streamer._is_workflow_terminated("run-123")

        assert result is False

    def test_is_workflow_terminated_not_found(self, mock_db):
        """Should return False if workflow not found."""
        mock_db.query_one.return_value = None

        streamer = StatusStreamer(mock_db)
        result = streamer._is_workflow_terminated("run-123")

        assert result is False

    def test_is_workflow_terminated_on_error(self, mock_db):
        """Should return False on query error."""
        mock_db.query_one.side_effect = Exception("DB error")

        streamer = StatusStreamer(mock_db)
        result = streamer._is_workflow_terminated("run-123")

        assert result is False

    def test_fetch_events(self, mock_db):
        """Should fetch and parse events."""
        mock_db.query.return_value = QueryResult(
            rows=[
                {
                    "id": 1,
                    "run_id": "run-123",
                    "step_id": "map",
                    "substep": None,
                    "status": "running",
                    "created_at": "2024-01-15T10:00:00",
                    "current": None,
                    "total": None,
                    "message": None,
                    "metadata": None,
                },
                {
                    "id": 2,
                    "run_id": "run-123",
                    "step_id": "map",
                    "substep": "fetch",
                    "status": "progress",
                    "created_at": "2024-01-15T10:00:01",
                    "current": 5,
                    "total": 10,
                    "message": "Processing",
                    "metadata": None,
                },
            ]
        )

        streamer = StatusStreamer(mock_db)
        events = streamer._fetch_events("run-123", 0)

        assert len(events) == 2
        assert events[0].id == 1
        assert events[1].id == 2
        assert events[1].substep == "fetch"

    def test_stream_yields_events_then_stops(self, mock_db):
        """Should yield events and stop on termination."""
        # First poll: return 2 events, workflow running
        # Second poll: return 1 event, workflow completed
        # Third poll (after termination): return 0 events
        mock_db.query.side_effect = [
            QueryResult(
                rows=[
                    {
                        "id": 1,
                        "run_id": "run-123",
                        "step_id": "map",
                        "substep": None,
                        "status": "running",
                        "created_at": None,
                        "current": None,
                        "total": None,
                        "message": None,
                        "metadata": None,
                    },
                ]
            ),
            QueryResult(
                rows=[
                    {
                        "id": 2,
                        "run_id": "run-123",
                        "step_id": "map",
                        "substep": None,
                        "status": "completed",
                        "created_at": None,
                        "current": 10,
                        "total": 10,
                        "message": None,
                        "metadata": None,
                    },
                ]
            ),
            QueryResult(rows=[]),  # Final fetch after termination
        ]

        # First check: running, second check: completed
        mock_db.query_one.side_effect = [
            {"status": "running"},
            {"status": "completed"},
        ]

        streamer = StatusStreamer(mock_db, poll_ms=10)
        events = list(streamer.stream("run-123"))

        assert len(events) == 2
        assert events[0].id == 1
        assert events[1].id == 2

    def test_stream_updates_cursor(self, mock_db):
        """Should update cursor with each event."""
        mock_db.query.side_effect = [
            QueryResult(
                rows=[
                    {
                        "id": 100,
                        "run_id": "run-123",
                        "step_id": "map",
                        "substep": None,
                        "status": "running",
                        "created_at": None,
                        "current": None,
                        "total": None,
                        "message": None,
                        "metadata": None,
                    },
                ]
            ),
            QueryResult(rows=[]),  # Second fetch (after event 100)
            QueryResult(rows=[]),  # Final fetch after termination
        ]
        mock_db.query_one.side_effect = [
            {"status": "running"},
            {"status": "completed"},
        ]

        streamer = StatusStreamer(mock_db, poll_ms=10)
        list(streamer.stream("run-123"))

        # Second query should use cursor=100
        calls = mock_db.query.call_args_list
        assert len(calls) >= 2
        # Check the second call used cursor=100
        second_call_params = calls[1][0][1]
        assert second_call_params[1] == 100  # cursor param

    def test_stream_respects_since_id(self, mock_db):
        """Should start from provided since_id."""
        mock_db.query.return_value = QueryResult(rows=[])
        mock_db.query_one.return_value = {"status": "completed"}

        streamer = StatusStreamer(mock_db, poll_ms=10)
        list(streamer.stream("run-123", since_id=500))

        # First query should use cursor=500
        call_params = mock_db.query.call_args[0][1]
        assert call_params[1] == 500


class TestStreamEvents:
    """Tests for stream_events convenience function."""

    def test_stream_events_creates_streamer(self):
        """Should create StatusStreamer and stream."""
        mock_db = MagicMock(spec=DoltDB)
        mock_db.query.return_value = QueryResult(rows=[])
        mock_db.query_one.return_value = {"status": "completed"}

        events = list(stream_events(mock_db, run_id="run-123", poll_ms=10))

        assert events == []
        mock_db.query.assert_called()

    def test_stream_events_passes_parameters(self):
        """Should pass all parameters to streamer."""
        mock_db = MagicMock(spec=DoltDB)
        mock_db.query.return_value = QueryResult(rows=[])
        mock_db.query_one.return_value = {"status": "completed"}

        list(stream_events(mock_db, run_id="run-123", since_id=100, poll_ms=250))

        # Check query was called with since_id
        call_params = mock_db.query.call_args[0][1]
        assert call_params[1] == 100  # cursor


class TestConstants:
    """Tests for module constants."""

    def test_terminal_statuses(self):
        """Should include expected terminal statuses."""
        assert "completed" in TERMINAL_STATUSES
        assert "failed" in TERMINAL_STATUSES
        assert "canceled" in TERMINAL_STATUSES
        assert "running" not in TERMINAL_STATUSES
        assert "pending" not in TERMINAL_STATUSES

    def test_default_poll_ms(self):
        """Should be 500ms."""
        assert DEFAULT_POLL_MS == 500

    def test_default_batch_limit(self):
        """Should be 100."""
        assert DEFAULT_BATCH_LIMIT == 100

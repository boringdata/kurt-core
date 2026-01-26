"""Tests for event tracking module."""

from __future__ import annotations

import json
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from kurt.db.dolt import DoltDB, DoltQueryError, QueryResult
from kurt.observability.tracking import (
    EVENT_KEY_ERROR,
    EVENT_KEY_PROGRESS,
    EVENT_KEY_STATUS,
    EventTracker,
    SubstepEvent,
    _BatchEvent,
    get_global_tracker,
    get_tracking_db,
    init_global_tracker,
    init_tracking,
    track_batched,
    track_event,
    write_event,
)


class TestSubstepEvent:
    """Tests for SubstepEvent dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        event = SubstepEvent()
        assert event.substep is None
        assert event.status == "progress"
        assert event.current is None
        assert event.total is None
        assert event.message is None
        assert event.metadata == {}

    def test_to_dict(self):
        """Should convert to dictionary correctly."""
        event = SubstepEvent(
            substep="fetch",
            status="running",
            current=5,
            total=10,
            message="Processing",
            metadata={"key": "value"},
        )
        result = event.to_dict()
        assert result == {
            "substep": "fetch",
            "status": "running",
            "current": 5,
            "total": 10,
            "message": "Processing",
            "metadata": {"key": "value"},
        }


class TestTrackEvent:
    """Tests for track_event function."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock DoltDB."""
        db = MagicMock(spec=DoltDB)
        db.execute.return_value = QueryResult(rows=[], affected_rows=1, last_insert_id=42)
        return db

    def test_basic_event(self, mock_db):
        """Should insert event with basic fields."""
        result = track_event(
            run_id="run-123",
            step_id="map",
            status="running",
            db=mock_db,
        )

        assert result == 42
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        assert "INSERT INTO step_events" in call_args[0][0]
        params = call_args[0][1]
        assert params[0] == "run-123"  # run_id
        assert params[1] == "map"  # step_id
        assert params[2] is None  # substep
        assert params[3] == "running"  # status

    def test_full_event(self, mock_db):
        """Should insert event with all fields."""
        metadata = {"url": "https://example.com"}
        result = track_event(
            run_id="run-123",
            step_id="map",
            substep="fetch",
            status="progress",
            current=5,
            total=10,
            message="Fetching page 5",
            metadata=metadata,
            db=mock_db,
        )

        assert result == 42
        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[0] == "run-123"
        assert params[1] == "map"
        assert params[2] == "fetch"
        assert params[3] == "progress"
        assert params[4] == 5
        assert params[5] == 10
        assert params[6] == "Fetching page 5"
        assert json.loads(params[7]) == metadata

    def test_requires_run_id(self, mock_db):
        """Should raise ValueError if run_id is empty."""
        with pytest.raises(ValueError, match="run_id is required"):
            track_event(run_id="", step_id="map", db=mock_db)

    def test_requires_step_id(self, mock_db):
        """Should raise ValueError if step_id is empty."""
        with pytest.raises(ValueError, match="step_id is required"):
            track_event(run_id="run-123", step_id="", db=mock_db)

    def test_returns_none_without_db(self):
        """Should return None if no DB configured."""
        # Clear global DB
        with patch("kurt.observability.tracking.get_tracking_db", return_value=None):
            result = track_event(run_id="run-123", step_id="map", status="running")
            assert result is None

    def test_propagates_db_error(self, mock_db):
        """Should propagate DoltQueryError."""
        mock_db.execute.side_effect = DoltQueryError("Insert failed")

        with pytest.raises(DoltQueryError, match="Insert failed"):
            track_event(run_id="run-123", step_id="map", db=mock_db)


class TestWriteEvent:
    """Tests for write_event function (legacy compatibility)."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock DoltDB."""
        db = MagicMock(spec=DoltDB)
        db.execute.return_value = QueryResult(rows=[], affected_rows=1, last_insert_id=42)
        return db

    def test_maps_progress_key(self, mock_db):
        """Should map 'progress' key to status='progress'."""
        write_event(
            run_id="run-123",
            key=EVENT_KEY_PROGRESS,
            payload={"step_id": "map", "current": 5, "total": 10},
            db=mock_db,
        )

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[3] == "progress"  # status

    def test_maps_status_key(self, mock_db):
        """Should map 'status' key to status='running'."""
        write_event(
            run_id="run-123",
            key=EVENT_KEY_STATUS,
            payload={"step_id": "map"},
            db=mock_db,
        )

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[3] == "running"

    def test_maps_error_key(self, mock_db):
        """Should map 'error' key to status='failed'."""
        write_event(
            run_id="run-123",
            key=EVENT_KEY_ERROR,
            payload={"step_id": "map", "message": "Something went wrong"},
            db=mock_db,
        )

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[3] == "failed"

    def test_uses_key_as_step_id_fallback(self, mock_db):
        """Should use key as step_id if not in payload."""
        write_event(
            run_id="run-123",
            key="custom_step",
            payload={"current": 5},
            db=mock_db,
        )

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[1] == "custom_step"  # step_id

    def test_extra_fields_go_to_metadata(self, mock_db):
        """Should put non-standard fields in metadata."""
        write_event(
            run_id="run-123",
            key="progress",
            payload={
                "step_id": "map",
                "current": 5,
                "url": "https://example.com",
                "custom_field": "value",
            },
            db=mock_db,
        )

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        metadata = json.loads(params[7])
        assert metadata["url"] == "https://example.com"
        assert metadata["custom_field"] == "value"
        assert "current" not in metadata  # standard field


class TestInitTracking:
    """Tests for global DB initialization."""

    def test_init_and_get(self):
        """Should set and get global DB."""
        mock_db = MagicMock(spec=DoltDB)

        with patch("kurt.observability.tracking._default_db", None):
            init_tracking(mock_db)
            result = get_tracking_db()
            assert result is mock_db


class TestEventTracker:
    """Tests for EventTracker class."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock DoltDB."""
        db = MagicMock(spec=DoltDB)
        db.execute.return_value = QueryResult(rows=[], affected_rows=1)
        return db

    def test_context_manager(self, mock_db):
        """Should start and stop properly as context manager."""
        with EventTracker(mock_db) as tracker:
            assert tracker._running is True
            tracker.track(run_id="run-123", step_id="map", status="running")

        assert tracker._running is False

    def test_tracks_events(self, mock_db):
        """Should track and flush events."""
        with EventTracker(mock_db) as tracker:
            tracker.track(run_id="run-123", step_id="map", status="running")
            tracker.flush()

        # Should have called execute with INSERT
        assert mock_db.execute.called
        call_args = mock_db.execute.call_args
        assert "INSERT INTO step_events" in call_args[0][0]

    def test_batches_events(self, mock_db):
        """Should batch multiple events into single INSERT."""
        with EventTracker(mock_db) as tracker:
            for i in range(5):
                tracker.track(
                    run_id="run-123",
                    step_id="map",
                    status="progress",
                    current=i,
                    total=5,
                )
            tracker.flush()

        # Should have called execute once with multi-row INSERT
        assert mock_db.execute.call_count >= 1
        call_args = mock_db.execute.call_args
        sql = call_args[0][0]
        # Should have multiple value tuples
        assert sql.count("(?, ?, ?, ?, ?, ?, ?, ?)") == 5

    def test_flushes_on_batch_size(self, mock_db):
        """Should flush when batch reaches max size."""
        tracker = EventTracker(mock_db, max_batch_size=10)
        tracker.start()

        try:
            for i in range(15):
                tracker.track(run_id="run-123", step_id="map", status="progress", current=i)

            # Wait for flush
            time.sleep(0.2)

            # Should have flushed at least once (at batch size 10)
            assert mock_db.execute.call_count >= 1
        finally:
            tracker.stop()

    def test_flushes_on_timeout(self, mock_db):
        """Should flush after timeout."""
        tracker = EventTracker(mock_db)
        tracker.start()

        try:
            tracker.track(run_id="run-123", step_id="map", status="running")

            # Wait for timeout flush (100ms + buffer)
            time.sleep(0.3)

            assert mock_db.execute.called
        finally:
            tracker.stop()

    def test_thread_safe(self, mock_db):
        """Should handle concurrent track calls."""
        tracker = EventTracker(mock_db)
        tracker.start()

        try:
            threads = []
            for i in range(10):
                t = threading.Thread(
                    target=lambda idx=i: tracker.track(
                        run_id="run-123",
                        step_id="map",
                        status="progress",
                        current=idx,
                    )
                )
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            tracker.flush()

            # All events should be tracked
            assert mock_db.execute.called
        finally:
            tracker.stop()

    def test_raises_if_not_started(self, mock_db):
        """Should raise RuntimeError if tracking before start."""
        tracker = EventTracker(mock_db)

        with pytest.raises(RuntimeError, match="not started"):
            tracker.track(run_id="run-123", step_id="map", status="running")

    def test_retry_on_failure(self, mock_db):
        """Should retry once on failure."""
        # First call fails, second succeeds
        mock_db.execute.side_effect = [
            DoltQueryError("Temporary error"),
            QueryResult(rows=[], affected_rows=1),
        ]

        with EventTracker(mock_db) as tracker:
            tracker.track(run_id="run-123", step_id="map", status="running")
            tracker.flush()

        # Should have retried
        assert mock_db.execute.call_count == 2


class TestGlobalTracker:
    """Tests for global tracker functions."""

    def test_init_global_tracker(self):
        """Should create and return global tracker."""
        mock_db = MagicMock(spec=DoltDB)

        with patch("kurt.observability.tracking._global_tracker", None):
            tracker = init_global_tracker(mock_db)
            assert tracker is not None
            assert tracker._running is True

            # Cleanup
            tracker.stop()

    def test_get_global_tracker_returns_none_initially(self):
        """Should return None before init."""
        with patch("kurt.observability.tracking._global_tracker", None):
            result = get_global_tracker()
            assert result is None


class TestTrackBatched:
    """Tests for track_batched convenience function."""

    def test_uses_global_tracker(self):
        """Should use global tracker if available."""
        mock_tracker = MagicMock(spec=EventTracker)
        mock_tracker._running = True

        with patch("kurt.observability.tracking.get_global_tracker", return_value=mock_tracker):
            track_batched(run_id="run-123", step_id="map", status="running")

        mock_tracker.track.assert_called_once()

    def test_falls_back_to_track_event(self):
        """Should fall back to track_event if no global tracker."""
        mock_db = MagicMock(spec=DoltDB)
        mock_db.execute.return_value = QueryResult(rows=[], affected_rows=1, last_insert_id=1)

        with patch("kurt.observability.tracking.get_global_tracker", return_value=None):
            with patch("kurt.observability.tracking.get_tracking_db", return_value=mock_db):
                track_batched(run_id="run-123", step_id="map", status="running")

        mock_db.execute.assert_called_once()


class TestBatchEvent:
    """Tests for internal _BatchEvent dataclass."""

    def test_creation(self):
        """Should create batch event with all fields."""
        event = _BatchEvent(
            run_id="run-123",
            step_id="map",
            substep="fetch",
            status="progress",
            current=5,
            total=10,
            message="Processing",
            metadata_json='{"key": "value"}',
        )

        assert event.run_id == "run-123"
        assert event.step_id == "map"
        assert event.substep == "fetch"
        assert event.status == "progress"
        assert event.current == 5
        assert event.total == 10
        assert event.message == "Processing"
        assert event.metadata_json == '{"key": "value"}'

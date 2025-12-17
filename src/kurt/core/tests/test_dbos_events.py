"""Tests for DBOS event integration."""

from datetime import datetime

from kurt.core.dbos_events import (
    DBOSEventEmitter,
    ModelEvent,
    configure_event_emitter,
    get_event_emitter,
)


class TestDBOSEventEmitter:
    """Tests for DBOS event emitter."""

    def test_event_emitter_initialization(self):
        """Test event emitter can be initialized."""
        emitter = DBOSEventEmitter(workflow_id="test_wf", run_id="test_run")
        assert emitter.workflow_id == "test_wf"
        assert emitter.run_id == "test_run"
        assert emitter.get_events() == []

    def test_emit_model_started(self):
        """Test emitting model started event."""
        emitter = DBOSEventEmitter(workflow_id="wf1")
        context = {"param1": "value1"}

        emitter.emit_model_started("test.model", context)

        events = emitter.get_events()
        assert len(events) == 1
        event = events[0]
        assert event.model_name == "test.model"
        assert event.event_type == "started"
        assert event.workflow_id == "wf1"
        assert event.payload == context
        assert event.error is None

    def test_emit_model_completed(self):
        """Test emitting model completed event."""
        emitter = DBOSEventEmitter()

        emitter.emit_model_completed(
            "test.model", rows_written=100, execution_time=2.5, metadata={"extra": "info"}
        )

        events = emitter.get_events()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == "completed"
        assert event.payload["rows_written"] == 100
        assert event.payload["execution_time"] == 2.5
        assert event.payload["extra"] == "info"

    def test_emit_model_failed(self):
        """Test emitting model failed event."""
        emitter = DBOSEventEmitter()
        error = ValueError("Test error")

        emitter.emit_model_failed("test.model", error, {"context": "data"})

        events = emitter.get_events()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == "failed"
        assert event.error == "Test error"
        assert event.payload == {"context": "data"}

    def test_emit_progress(self):
        """Test emitting progress event."""
        emitter = DBOSEventEmitter()

        emitter.emit_progress("test.model", current=50, total=100, message="Halfway")

        events = emitter.get_events()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == "progress"
        assert event.payload["current"] == 50
        assert event.payload["total"] == 100
        assert event.payload["percentage"] == 50.0
        assert event.payload["message"] == "Halfway"

    def test_emit_progress_zero_total(self):
        """Test progress event with zero total doesn't crash."""
        emitter = DBOSEventEmitter()

        emitter.emit_progress("test.model", current=0, total=0)

        events = emitter.get_events()
        assert len(events) == 1
        assert events[0].payload["percentage"] == 0

    def test_emit_data_available(self):
        """Test emitting data available event."""
        emitter = DBOSEventEmitter()

        emitter.emit_data_available("test_table", row_count=500, model_name="producer")

        events = emitter.get_events()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == "data_available"
        assert event.model_name == "producer"
        assert event.payload["table_name"] == "test_table"
        assert event.payload["row_count"] == 500

    def test_emit_data_available_without_model(self):
        """Test data available event without model name uses 'system'."""
        emitter = DBOSEventEmitter()

        emitter.emit_data_available("test_table", row_count=100)

        events = emitter.get_events()
        assert events[0].model_name == "system"

    def test_clear_events(self):
        """Test clearing stored events."""
        emitter = DBOSEventEmitter()
        emitter.emit_model_started("model1")
        emitter.emit_model_completed("model2", 10, 1.0)

        assert len(emitter.get_events()) == 2

        emitter.clear_events()
        assert emitter.get_events() == []

    def test_event_serialization(self):
        """Test event can be serialized to JSON."""
        emitter = DBOSEventEmitter()
        event = ModelEvent(
            model_name="test",
            event_type="started",
            timestamp=datetime.utcnow(),
            workflow_id="wf1",
            payload={"key": "value"},
        )

        json_str = emitter._serialize_event(event)
        assert isinstance(json_str, str)
        assert "test" in json_str
        assert "started" in json_str

    def test_global_event_emitter(self):
        """Test global event emitter singleton."""
        emitter1 = get_event_emitter()
        emitter2 = get_event_emitter()
        assert emitter1 is emitter2

    def test_configure_global_emitter(self):
        """Test configuring global emitter with context."""
        configure_event_emitter(workflow_id="global_wf", run_id="global_run")

        emitter = get_event_emitter()
        assert emitter.workflow_id == "global_wf"
        assert emitter.run_id == "global_run"

    def test_multiple_events_tracking(self):
        """Test that multiple events are tracked correctly."""
        emitter = DBOSEventEmitter()

        # Emit various events
        emitter.emit_model_started("model1")
        emitter.emit_progress("model1", 10, 100)
        emitter.emit_progress("model1", 50, 100)
        emitter.emit_model_completed("model1", 100, 5.0)
        emitter.emit_model_started("model2")
        emitter.emit_model_failed("model2", RuntimeError("Failed"))

        events = emitter.get_events()
        assert len(events) == 6

        # Check event types
        event_types = [e.event_type for e in events]
        assert event_types == ["started", "progress", "progress", "completed", "started", "failed"]

        # Check model names
        model_names = [e.model_name for e in events]
        assert model_names == ["model1", "model1", "model1", "model1", "model2", "model2"]

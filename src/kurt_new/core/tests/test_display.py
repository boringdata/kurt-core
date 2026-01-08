"""
Tests for display module.

Tests run in real environment without mocking Rich components,
verifying that the display system works correctly with actual terminal output.
"""

from __future__ import annotations

import io
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from rich.console import Console

from kurt_new.core.display import (
    StepDisplay,
    _format_duration,
    get_concurrent_manager,
    is_display_enabled,
    print_info,
    print_warning,
    set_display_enabled,
)
from kurt_new.core.tracking import WorkflowTracker, log_item, track_step, update_step_progress


class TestDisplayEnabledFlag:
    """Tests for display enabled/disabled context flag."""

    def test_display_disabled_by_default(self):
        """Display should be disabled by default."""
        # Reset to ensure clean state
        set_display_enabled(False)
        assert is_display_enabled() is False

    def test_enable_disable_display(self):
        """Test toggling display on and off."""
        set_display_enabled(True)
        assert is_display_enabled() is True

        set_display_enabled(False)
        assert is_display_enabled() is False

    def test_print_warning_when_disabled(self):
        """print_warning should do nothing when display is disabled."""
        set_display_enabled(False)

        # Capture output
        console = Console(file=io.StringIO(), force_terminal=True)
        with patch("kurt_new.core.display._console", console):
            print_warning("Test warning")

        output = console.file.getvalue()
        assert output == ""

    def test_print_warning_when_enabled(self):
        """print_warning should output when display is enabled."""
        set_display_enabled(True)
        try:
            console = Console(file=io.StringIO(), force_terminal=True)
            with patch("kurt_new.core.display._console", console):
                print_warning("Test warning")

            output = console.file.getvalue()
            assert "Test warning" in output
            assert "⚠" in output
        finally:
            set_display_enabled(False)

    def test_print_info_when_disabled(self):
        """print_info should do nothing when display is disabled."""
        set_display_enabled(False)

        console = Console(file=io.StringIO(), force_terminal=True)
        with patch("kurt_new.core.display._console", console):
            print_info("Test info")

        output = console.file.getvalue()
        assert output == ""

    def test_print_info_when_enabled(self):
        """print_info should output when display is enabled."""
        set_display_enabled(True)
        try:
            console = Console(file=io.StringIO(), force_terminal=True)
            with patch("kurt_new.core.display._console", console):
                print_info("Test info")

            output = console.file.getvalue()
            assert "Test info" in output
        finally:
            set_display_enabled(False)


class TestFormatDuration:
    """Tests for duration formatting."""

    def test_format_seconds(self):
        """Test formatting for durations under 60 seconds."""
        assert _format_duration(0.5) == "0.5s"
        assert _format_duration(5.123) == "5.1s"
        assert _format_duration(59.9) == "59.9s"

    def test_format_minutes(self):
        """Test formatting for durations in minutes."""
        assert _format_duration(60) == "1m 0s"
        assert _format_duration(90) == "1m 30s"
        assert _format_duration(3599) == "59m 59s"

    def test_format_hours(self):
        """Test formatting for durations in hours."""
        assert _format_duration(3600) == "1h 0m"
        assert _format_duration(3660) == "1h 1m"
        assert _format_duration(7200) == "2h 0m"


class TestStepDisplay:
    """Tests for StepDisplay class."""

    def test_step_display_not_started_when_disabled(self):
        """StepDisplay should not start when display is disabled."""
        set_display_enabled(False)

        display = StepDisplay("test_step", total=10)
        display.start()

        assert display._started is False
        assert display._manager is None

    def test_step_display_starts_when_enabled(self):
        """StepDisplay should start when display is enabled."""
        set_display_enabled(True)
        try:
            display = StepDisplay("test_step", total=10)
            display.start()

            assert display._started is True
            assert display._manager is not None

            display.stop()
        finally:
            set_display_enabled(False)

    def test_step_display_context_manager(self):
        """Test StepDisplay as context manager."""
        set_display_enabled(True)
        try:
            with StepDisplay("test_step", total=5) as display:
                assert display._started is True
                display.update(1)
                display.update(2)

            # After context exit, should be stopped
            assert display._started is False
        finally:
            set_display_enabled(False)

    def test_step_display_log_methods(self):
        """Test StepDisplay logging methods."""
        set_display_enabled(True)
        try:
            with StepDisplay("test_step", total=3) as display:
                # These should not raise errors
                display.log_success("item1", title="First item", elapsed=0.5)
                display.log_skip("item2", reason="unchanged")
                display.log_error("item3", error="Something went wrong")
                display.log_info("Processing complete")
        finally:
            set_display_enabled(False)

    def test_step_display_no_progress_bar_when_total_zero(self):
        """When total=0, should show log window only, no progress bar."""
        set_display_enabled(True)
        try:
            display = StepDisplay("test_step", total=0)
            display.start()

            # Should be started but manager should not have a progress bar task
            assert display._started is True
            manager = display._manager
            tracker_info = manager._trackers.get(display._tracker_id)
            assert tracker_info is not None
            assert tracker_info["task_id"] is None  # No progress bar
            assert tracker_info["total"] == 0

            display.stop()
        finally:
            set_display_enabled(False)

    def test_step_display_with_progress_bar_when_total_positive(self):
        """When total > 0, should show progress bar + log window."""
        set_display_enabled(True)
        try:
            display = StepDisplay("test_step", total=10)
            display.start()

            manager = display._manager
            tracker_info = manager._trackers.get(display._tracker_id)
            assert tracker_info is not None
            assert tracker_info["task_id"] is not None  # Has progress bar
            assert tracker_info["total"] == 10

            display.stop()
        finally:
            set_display_enabled(False)


class TestConcurrentProgressManager:
    """Tests for ConcurrentProgressManager singleton."""

    def test_concurrent_manager_is_singleton(self):
        """ConcurrentProgressManager should be a singleton."""
        manager1 = get_concurrent_manager()
        manager2 = get_concurrent_manager()
        assert manager1 is manager2

    def test_register_and_unregister_tracker(self):
        """Test registering and unregistering trackers."""
        set_display_enabled(True)
        try:
            manager = get_concurrent_manager()

            # Register tracker
            manager.register_tracker("test1", "Test Step", 10)
            assert "test1" in manager._trackers
            assert manager.is_active() is True

            # Unregister
            manager.unregister_tracker("test1")
            assert "test1" not in manager._trackers
            assert manager.is_active() is False
        finally:
            set_display_enabled(False)

    def test_multiple_trackers(self):
        """Test multiple concurrent trackers."""
        set_display_enabled(True)
        try:
            manager = get_concurrent_manager()

            manager.register_tracker("step1", "Step 1", 10)
            manager.register_tracker("step2", "Step 2", 20)

            assert "step1" in manager._trackers
            assert "step2" in manager._trackers
            assert manager.is_active() is True

            # Clean up
            manager.unregister_tracker("step1")
            assert manager.is_active() is True  # step2 still active

            manager.unregister_tracker("step2")
            assert manager.is_active() is False
        finally:
            set_display_enabled(False)

    def test_add_log_to_tracker(self):
        """Test adding log messages to tracker."""
        set_display_enabled(True)
        try:
            manager = get_concurrent_manager()
            manager.register_tracker("test1", "Test", 5)

            # Add log message
            manager.add_log("test1", "Test message", style="dim green")

            # Log buffer should have the message
            assert len(manager._log_buffer) == 1

            manager.unregister_tracker("test1")
        finally:
            set_display_enabled(False)


class TestWorkflowTrackerWithDisplay:
    """Tests for WorkflowTracker integration with display."""

    def test_tracker_creates_display_when_enabled(self):
        """WorkflowTracker should create display when is_display_enabled()."""
        set_display_enabled(True)
        try:
            tracker = WorkflowTracker()
            tracker.start_step("test_step", total=5)

            assert tracker._display is not None
            assert tracker._current_step == "test_step"

            tracker.end_step("test_step")
            assert tracker._display is None
        finally:
            set_display_enabled(False)

    def test_tracker_no_display_when_disabled(self):
        """WorkflowTracker should not create display when disabled."""
        set_display_enabled(False)

        tracker = WorkflowTracker()
        tracker.start_step("test_step", total=5)

        assert tracker._display is None

        tracker.end_step("test_step")

    def test_tracker_update_progress_updates_display(self):
        """update_progress should update display."""
        set_display_enabled(True)
        try:
            tracker = WorkflowTracker()
            tracker.start_step("test_step", total=10)

            # Update progress
            tracker.update_progress(5, step_name="test_step")

            # Display should still be active
            assert tracker._display is not None
            assert tracker._display._started is True

            tracker.end_step("test_step")
        finally:
            set_display_enabled(False)

    def test_tracker_log_item(self):
        """Test log_item method for batch operations."""
        set_display_enabled(True)
        try:
            tracker = WorkflowTracker()
            tracker.start_step("test_step", total=3)

            # Log items
            tracker.log_item("item1", status="success", message="Done", elapsed=0.5)
            tracker.log_item("item2", status="skip", message="unchanged")
            tracker.log_item("item3", status="error", message="Failed to process")

            tracker.end_step("test_step")
        finally:
            set_display_enabled(False)


class TestTrackStepContextManager:
    """Tests for track_step context manager with display."""

    def test_track_step_with_display(self):
        """track_step should show display when enabled."""
        set_display_enabled(True)
        try:
            with track_step("test_step", total=5):
                # Inside context, display should be active
                pass
        finally:
            set_display_enabled(False)

    def test_track_step_without_display(self):
        """track_step should not show display when disabled."""
        set_display_enabled(False)

        with track_step("test_step", total=5):
            pass


class TestLogItemHelper:
    """Tests for log_item helper function."""

    def test_log_item_success(self):
        """Test log_item with success status."""
        set_display_enabled(True)
        try:
            tracker = WorkflowTracker()
            tracker.start_step("test", total=1)

            log_item(
                "doc123", status="success", message="Document fetched", elapsed=1.5, tracker=tracker
            )

            tracker.end_step("test")
        finally:
            set_display_enabled(False)

    def test_log_item_skip(self):
        """Test log_item with skip status."""
        set_display_enabled(True)
        try:
            tracker = WorkflowTracker()
            tracker.start_step("test", total=1)

            log_item("doc123", status="skip", message="unchanged", tracker=tracker)

            tracker.end_step("test")
        finally:
            set_display_enabled(False)

    def test_log_item_error(self):
        """Test log_item with error status."""
        set_display_enabled(True)
        try:
            tracker = WorkflowTracker()
            tracker.start_step("test", total=1)

            log_item("doc123", status="error", message="Connection timeout", tracker=tracker)

            tracker.end_step("test")
        finally:
            set_display_enabled(False)


class TestDisplayIntegration:
    """End-to-end integration tests for display system."""

    def test_full_workflow_display(self):
        """Test a complete workflow with progress display."""
        set_display_enabled(True)
        try:
            with track_step("fetch_documents", total=5) as tracker:
                for i in range(5):
                    # Simulate work
                    time.sleep(0.01)

                    # Log item
                    log_item(
                        f"doc{i}",
                        status="success",
                        message=f"https://example.com/doc{i}",
                        elapsed=0.01,
                        tracker=tracker,
                    )

                    # Update progress
                    update_step_progress(i + 1, tracker=tracker)
        finally:
            set_display_enabled(False)

    def test_multiple_steps_sequential(self):
        """Test multiple sequential steps with display."""
        set_display_enabled(True)
        try:
            # Step 1
            with track_step("fetch", total=3):
                for i in range(3):
                    update_step_progress(i + 1)

            # Step 2
            with track_step("process", total=3):
                for i in range(3):
                    update_step_progress(i + 1)
        finally:
            set_display_enabled(False)

    def test_step_without_total(self):
        """Test step without total (log window only)."""
        set_display_enabled(True)
        try:
            with track_step("save_results", total=0):
                # Non-batch step, just logs
                pass
        finally:
            set_display_enabled(False)

    def test_display_with_mixed_statuses(self):
        """Test display with success, skip, and error statuses."""
        set_display_enabled(True)
        try:
            with track_step("process_items", total=6) as tracker:
                # Success
                log_item(
                    "item1", status="success", message="Processed", elapsed=0.1, tracker=tracker
                )
                update_step_progress(1, tracker=tracker)

                # Success
                log_item(
                    "item2", status="success", message="Processed", elapsed=0.2, tracker=tracker
                )
                update_step_progress(2, tracker=tracker)

                # Skip
                log_item("item3", status="skip", message="already exists", tracker=tracker)
                update_step_progress(3, tracker=tracker)

                # Error
                log_item("item4", status="error", message="Network error", tracker=tracker)
                update_step_progress(4, tracker=tracker)

                # Success
                log_item(
                    "item5", status="success", message="Processed", elapsed=0.15, tracker=tracker
                )
                update_step_progress(5, tracker=tracker)

                # Skip
                log_item("item6", status="skip", message="unchanged", tracker=tracker)
                update_step_progress(6, tracker=tracker)
        finally:
            set_display_enabled(False)


class TestConcurrentDisplay:
    """Tests for concurrent/parallel display scenarios."""

    def test_concurrent_trackers_thread_safe(self):
        """Test that concurrent trackers are thread-safe."""
        set_display_enabled(True)
        try:
            results = []

            def run_step(step_name: str, total: int):
                with track_step(step_name, total=total):
                    for i in range(total):
                        time.sleep(0.01)
                        update_step_progress(i + 1)
                results.append(step_name)

            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(run_step, "step1", 5),
                    executor.submit(run_step, "step2", 5),
                    executor.submit(run_step, "step3", 5),
                ]
                for f in futures:
                    f.result()

            assert len(results) == 3
            assert "step1" in results
            assert "step2" in results
            assert "step3" in results
        finally:
            set_display_enabled(False)

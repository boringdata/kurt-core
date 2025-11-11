"""Tests for telemetry tracker."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kurt.admin.telemetry.tracker import _get_system_properties, track_event


class TestTracker:
    """Test telemetry tracking functions."""

    def test_get_system_properties(self):
        """Test system properties collection."""
        props = _get_system_properties()

        assert "os" in props
        assert "os_version" in props
        assert "python_version" in props
        assert "kurt_version" in props
        assert "is_ci" in props

        # Verify types
        assert isinstance(props["os"], str)
        assert isinstance(props["python_version"], str)
        assert isinstance(props["is_ci"], bool)

    @patch("kurt.admin.telemetry.tracker._get_posthog_client")
    def test_track_event_when_disabled(self, mock_get_client, tmp_path, monkeypatch):
        """Test that tracking doesn't happen when telemetry is disabled."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("DO_NOT_TRACK", "1")

        # Should not call PostHog
        track_event("test_event")
        mock_get_client.assert_not_called()

    @patch("kurt.admin.telemetry.tracker._get_posthog_client")
    def test_track_event_with_properties(self, mock_get_client, tmp_path, monkeypatch):
        """Test tracking event with custom properties."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Mock PostHog client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Track event
        custom_props = {"command": "test", "duration_ms": 123.45}
        track_event("test_event", properties=custom_props, blocking=True)

        # Verify client was called
        mock_client.capture.assert_called_once()
        call_args = mock_client.capture.call_args

        # Check event name
        assert call_args[1]["event"] == "test_event"

        # Check properties include both custom and system props
        props = call_args[1]["properties"]
        assert "command" in props
        assert props["command"] == "test"
        assert "duration_ms" in props
        assert props["duration_ms"] == 123.45
        assert "os" in props
        assert "kurt_version" in props

    @patch("kurt.admin.telemetry.tracker._get_posthog_client")
    def test_track_event_error_handling(self, mock_get_client, tmp_path, monkeypatch):
        """Test that tracking errors don't raise exceptions."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Mock client that raises error
        mock_client = MagicMock()
        mock_client.capture.side_effect = Exception("Network error")
        mock_get_client.return_value = mock_client

        # Should not raise exception
        try:
            track_event("test_event", blocking=True)
        except Exception:
            pytest.fail("track_event should not raise exceptions")

    @patch("kurt.admin.telemetry.tracker._get_posthog_client")
    def test_track_event_non_blocking(self, mock_get_client, tmp_path, monkeypatch):
        """Test that non-blocking tracking uses threading."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Mock PostHog client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Track event (non-blocking by default)
        track_event("test_event", blocking=False)

        # The call happens in a background thread, so we just verify setup
        # Note: In real tests, you might want to add thread synchronization
        # to verify the call eventually happens

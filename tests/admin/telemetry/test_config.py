"""Tests for telemetry configuration."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from kurt.admin.telemetry.config import (
    get_machine_id,
    get_telemetry_status,
    is_ci_environment,
    is_telemetry_enabled,
    set_telemetry_enabled,
)


class TestTelemetryConfig:
    """Test telemetry configuration functions."""

    def test_machine_id_generation(self, tmp_path, monkeypatch):
        """Test that machine ID is generated and persisted."""
        # Use temp directory for test
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # First call should generate new ID
        machine_id_1 = get_machine_id()
        assert machine_id_1
        assert len(machine_id_1) == 36  # UUID format

        # Second call should return same ID
        machine_id_2 = get_machine_id()
        assert machine_id_1 == machine_id_2

    @patch("kurt.config.get_config_or_default")
    def test_telemetry_enabled_by_default(self, mock_get_config, tmp_path, monkeypatch):
        """Test that telemetry is enabled by default."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Mock config with TELEMETRY_ENABLED=True
        mock_config = MagicMock()
        mock_config.TELEMETRY_ENABLED = True
        mock_get_config.return_value = mock_config

        assert is_telemetry_enabled() is True

    def test_telemetry_disabled_by_do_not_track(self, tmp_path, monkeypatch):
        """Test that DO_NOT_TRACK disables telemetry."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("DO_NOT_TRACK", "1")

        assert is_telemetry_enabled() is False

    def test_telemetry_disabled_by_kurt_env(self, tmp_path, monkeypatch):
        """Test that KURT_TELEMETRY_DISABLED disables telemetry."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("KURT_TELEMETRY_DISABLED", "1")

        assert is_telemetry_enabled() is False

    @patch("kurt.config.update_config")
    @patch("kurt.config.config_exists")
    @patch("kurt.config.get_config_or_default")
    def test_set_telemetry_enabled(
        self, mock_get_config, mock_config_exists, mock_update_config, tmp_path, monkeypatch
    ):
        """Test enabling/disabling telemetry via kurt.config."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Mock config
        mock_config = MagicMock()
        mock_config.TELEMETRY_ENABLED = True
        mock_get_config.return_value = mock_config
        mock_config_exists.return_value = True

        # Disable telemetry
        set_telemetry_enabled(False)
        assert mock_config.TELEMETRY_ENABLED is False
        mock_update_config.assert_called_once_with(mock_config)

        # Reset mock
        mock_update_config.reset_mock()
        mock_config.TELEMETRY_ENABLED = False

        # Enable telemetry
        set_telemetry_enabled(True)
        assert mock_config.TELEMETRY_ENABLED is True
        mock_update_config.assert_called_once_with(mock_config)

    def test_get_telemetry_status(self, tmp_path, monkeypatch):
        """Test getting telemetry status."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        status = get_telemetry_status()
        assert isinstance(status, dict)
        assert "enabled" in status
        assert "config_path" in status
        assert "machine_id" in status
        assert "is_ci" in status

    def test_get_telemetry_status_disabled(self, tmp_path, monkeypatch):
        """Test getting telemetry status when disabled."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("DO_NOT_TRACK", "1")

        status = get_telemetry_status()
        assert status["enabled"] is False
        assert status["disabled_reason"] == "DO_NOT_TRACK environment variable"
        assert status["machine_id"] is None

    def test_is_ci_environment(self, monkeypatch):
        """Test CI environment detection."""
        # Clear all CI environment variables first
        ci_env_vars = [
            "CI",
            "CONTINUOUS_INTEGRATION",
            "BUILD_NUMBER",
            "GITHUB_ACTIONS",
            "GITLAB_CI",
            "CIRCLECI",
            "TRAVIS",
            "JENKINS_HOME",
        ]
        for var in ci_env_vars:
            monkeypatch.delenv(var, raising=False)

        # Not in CI by default (after clearing env vars)
        assert is_ci_environment() is False

        # Test various CI env vars
        for ci_var in ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "CIRCLECI"]:
            monkeypatch.setenv(ci_var, "true")
            assert is_ci_environment() is True
            monkeypatch.delenv(ci_var)

    @patch("kurt.config.get_config_or_default")
    def test_config_error_fallback(self, mock_get_config, tmp_path, monkeypatch):
        """Test handling of config loading errors."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Simulate config loading error
        mock_get_config.side_effect = Exception("Config error")

        # Should default to enabled
        assert is_telemetry_enabled() is True

"""Tests for telemetry configuration."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from kurt.telemetry.config import (
    get_machine_id,
    get_telemetry_config_path,
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

    def test_telemetry_enabled_by_default(self, tmp_path, monkeypatch):
        """Test that telemetry is enabled by default."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
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

    def test_set_telemetry_enabled(self, tmp_path, monkeypatch):
        """Test enabling/disabling telemetry via config file."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Disable telemetry
        set_telemetry_enabled(False)
        assert is_telemetry_enabled() is False

        # Enable telemetry
        set_telemetry_enabled(True)
        assert is_telemetry_enabled() is True

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
        # Not in CI by default
        assert is_ci_environment() is False

        # Test various CI env vars
        for ci_var in ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "CIRCLECI"]:
            monkeypatch.setenv(ci_var, "true")
            assert is_ci_environment() is True
            monkeypatch.delenv(ci_var)

    def test_config_file_malformed(self, tmp_path, monkeypatch):
        """Test handling of malformed config file."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create malformed config
        config_path = get_telemetry_config_path()
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text("not valid json")

        # Should default to enabled
        assert is_telemetry_enabled() is True

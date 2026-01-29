"""Tests for workflow configuration models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kurt.workflows.core import GuardrailsConfig, ScheduleConfig


class TestScheduleConfig:
    """Tests for ScheduleConfig model."""

    def test_defaults(self) -> None:
        """Default values are applied correctly."""
        config = ScheduleConfig(cron="0 9 * * *")
        assert config.cron == "0 9 * * *"
        assert config.timezone == "UTC"
        assert config.enabled is True

    def test_custom_timezone(self) -> None:
        """Custom timezone is accepted."""
        config = ScheduleConfig(cron="0 9 * * *", timezone="America/New_York")
        assert config.timezone == "America/New_York"

    def test_disabled_schedule(self) -> None:
        """Schedule can be disabled."""
        config = ScheduleConfig(cron="0 9 * * *", enabled=False)
        assert config.enabled is False

    def test_all_fields(self) -> None:
        """All fields can be specified."""
        config = ScheduleConfig(
            cron="0 0 * * 0",
            timezone="Europe/London",
            enabled=True,
        )
        assert config.cron == "0 0 * * 0"
        assert config.timezone == "Europe/London"
        assert config.enabled is True

    def test_cron_required(self) -> None:
        """cron field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ScheduleConfig()  # type: ignore[call-arg]
        assert "cron" in str(exc_info.value)

    def test_from_dict(self) -> None:
        """Config can be created from dict."""
        data = {"cron": "*/5 * * * *", "timezone": "UTC", "enabled": True}
        config = ScheduleConfig(**data)
        assert config.cron == "*/5 * * * *"

    def test_model_dump(self) -> None:
        """Config can be serialized to dict."""
        config = ScheduleConfig(cron="0 9 * * *")
        data = config.model_dump()
        assert data == {"cron": "0 9 * * *", "timezone": "UTC", "enabled": True}


class TestGuardrailsConfig:
    """Tests for GuardrailsConfig model."""

    def test_defaults(self) -> None:
        """Default values match expected values."""
        config = GuardrailsConfig()
        assert config.max_tokens == 500000
        assert config.max_tool_calls == 200
        assert config.max_time == 3600

    def test_custom_values(self) -> None:
        """Custom values are accepted."""
        config = GuardrailsConfig(
            max_tokens=100000,
            max_tool_calls=50,
            max_time=600,
        )
        assert config.max_tokens == 100000
        assert config.max_tool_calls == 50
        assert config.max_time == 600

    def test_min_max_tokens(self) -> None:
        """max_tokens has minimum of 1000."""
        # Valid minimum
        config = GuardrailsConfig(max_tokens=1000)
        assert config.max_tokens == 1000

        # Below minimum
        with pytest.raises(ValidationError) as exc_info:
            GuardrailsConfig(max_tokens=999)
        assert "max_tokens" in str(exc_info.value)

    def test_min_max_tool_calls(self) -> None:
        """max_tool_calls has minimum of 1."""
        # Valid minimum
        config = GuardrailsConfig(max_tool_calls=1)
        assert config.max_tool_calls == 1

        # Below minimum
        with pytest.raises(ValidationError) as exc_info:
            GuardrailsConfig(max_tool_calls=0)
        assert "max_tool_calls" in str(exc_info.value)

    def test_min_max_time(self) -> None:
        """max_time has minimum of 60 seconds."""
        # Valid minimum
        config = GuardrailsConfig(max_time=60)
        assert config.max_time == 60

        # Below minimum
        with pytest.raises(ValidationError) as exc_info:
            GuardrailsConfig(max_time=59)
        assert "max_time" in str(exc_info.value)

    def test_from_dict(self) -> None:
        """Config can be created from dict."""
        data = {"max_tokens": 200000, "max_tool_calls": 100, "max_time": 1800}
        config = GuardrailsConfig(**data)
        assert config.max_tokens == 200000
        assert config.max_tool_calls == 100
        assert config.max_time == 1800

    def test_partial_dict(self) -> None:
        """Config with partial dict uses defaults for missing fields."""
        data = {"max_tokens": 250000}
        config = GuardrailsConfig(**data)
        assert config.max_tokens == 250000
        assert config.max_tool_calls == 200  # default
        assert config.max_time == 3600  # default

    def test_model_dump(self) -> None:
        """Config can be serialized to dict."""
        config = GuardrailsConfig()
        data = config.model_dump()
        assert data == {
            "max_tokens": 500000,
            "max_tool_calls": 200,
            "max_time": 3600,
        }

    def test_large_values(self) -> None:
        """Large values are accepted (no upper bound enforced)."""
        config = GuardrailsConfig(
            max_tokens=10_000_000,
            max_tool_calls=10000,
            max_time=86400,  # 24 hours
        )
        assert config.max_tokens == 10_000_000
        assert config.max_tool_calls == 10000
        assert config.max_time == 86400

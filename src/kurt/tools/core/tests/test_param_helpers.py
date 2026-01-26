"""Tests for param_helpers module."""

import pytest
from pydantic import BaseModel, Field

from kurt.tools.core.param_helpers import (
    DualInputMixin,
    build_config_from_flat_fields,
)


# ============================================================================
# Test Models
# ============================================================================

# Define config fields list as a module-level constant to avoid Pydantic issues
SAMPLE_CONFIG_FIELDS = ["concurrency", "timeout_ms", "engine"]


class SampleInput(BaseModel):
    """Sample input model for testing."""

    url: str
    metadata: dict | None = None


class SampleConfig(BaseModel):
    """Sample config model for testing."""

    concurrency: int = 5
    timeout_ms: int = 30000
    engine: str = "default"


class SampleParams(DualInputMixin, BaseModel):
    """Sample params model using the mixin."""

    # Executor style (flat)
    input_data: list[SampleInput] = Field(default_factory=list)

    # Direct API style (nested)
    inputs: list[SampleInput] = Field(default_factory=list)
    config: SampleConfig | None = Field(default=None)

    # Flat config fields (for executor compatibility)
    # Note: These MUST have matching defaults to the config class
    # because build_config_from_flat_fields passes all non-None values
    concurrency: int = Field(default=5)
    timeout_ms: int = Field(default=30000)
    engine: str = Field(default="default")

    def get_inputs(self) -> list[SampleInput]:
        """Get inputs using mixin helper."""
        return self.get_inputs_from_fields("input_data", "inputs")

    def get_config(self) -> SampleConfig:
        """Get config using mixin helper."""
        return self.get_config_from_fields("config", SampleConfig, SAMPLE_CONFIG_FIELDS)


# ============================================================================
# Tests for DualInputMixin
# ============================================================================


class TestDualInputMixin:
    """Tests for DualInputMixin class."""

    def test_get_inputs_from_primary_field(self):
        """Should return inputs from primary field when present."""
        params = SampleParams(
            input_data=[
                SampleInput(url="https://example1.com"),
                SampleInput(url="https://example2.com"),
            ]
        )
        inputs = params.get_inputs()
        assert len(inputs) == 2
        assert inputs[0].url == "https://example1.com"
        assert inputs[1].url == "https://example2.com"

    def test_get_inputs_from_fallback_field(self):
        """Should return inputs from fallback field when primary is empty."""
        params = SampleParams(
            inputs=[
                SampleInput(url="https://api1.com"),
            ]
        )
        inputs = params.get_inputs()
        assert len(inputs) == 1
        assert inputs[0].url == "https://api1.com"

    def test_get_inputs_prefers_primary_over_fallback(self):
        """Should prefer primary field even when both are present."""
        params = SampleParams(
            input_data=[SampleInput(url="https://primary.com")],
            inputs=[SampleInput(url="https://fallback.com")],
        )
        inputs = params.get_inputs()
        assert len(inputs) == 1
        assert inputs[0].url == "https://primary.com"

    def test_get_inputs_returns_empty_when_none(self):
        """Should return empty list when both fields are empty."""
        params = SampleParams()
        inputs = params.get_inputs()
        assert inputs == []

    def test_get_config_from_nested_field(self):
        """Should return nested config when present."""
        params = SampleParams(
            config=SampleConfig(concurrency=10, timeout_ms=5000, engine="fast")
        )
        config = params.get_config()
        assert config.concurrency == 10
        assert config.timeout_ms == 5000
        assert config.engine == "fast"

    def test_get_config_from_flat_fields(self):
        """Should build config from flat fields when nested is None."""
        params = SampleParams(
            concurrency=8,
            timeout_ms=15000,
            engine="slow",
        )
        config = params.get_config()
        assert config.concurrency == 8
        assert config.timeout_ms == 15000
        assert config.engine == "slow"

    def test_get_config_prefers_nested_over_flat(self):
        """Should prefer nested config even when flat fields are set."""
        params = SampleParams(
            config=SampleConfig(concurrency=10),
            concurrency=5,  # Should be ignored
        )
        config = params.get_config()
        assert config.concurrency == 10

    def test_get_config_uses_defaults_for_missing_flat_fields(self):
        """Should use config class defaults for unset flat fields."""
        params = SampleParams(concurrency=7)  # Only set one field
        config = params.get_config()
        assert config.concurrency == 7
        assert config.timeout_ms == 30000  # Default
        assert config.engine == "default"  # Default


# ============================================================================
# Tests for build_config_from_flat_fields
# ============================================================================


class TestBuildConfigFromFlatFields:
    """Tests for build_config_from_flat_fields function."""

    def test_builds_config_from_all_fields(self):
        """Should build config with all specified fields."""
        params = SampleParams(
            concurrency=3,
            timeout_ms=10000,
            engine="turbo",
        )
        config = build_config_from_flat_fields(
            params,
            SampleConfig,
            ["concurrency", "timeout_ms", "engine"],
        )
        assert config.concurrency == 3
        assert config.timeout_ms == 10000
        assert config.engine == "turbo"

    def test_builds_config_with_partial_fields(self):
        """Should build config with subset of fields."""
        params = SampleParams(concurrency=4)
        config = build_config_from_flat_fields(
            params,
            SampleConfig,
            ["concurrency"],  # Only extract one field
        )
        assert config.concurrency == 4
        assert config.timeout_ms == 30000  # Default from SampleConfig
        assert config.engine == "default"  # Default from SampleConfig

    def test_skips_none_values(self):
        """Should not pass None values to config constructor."""

        class ConfigWithRequired(BaseModel):
            value: str = "default"
            optional: str | None = None

        class ParamsWithOptional(BaseModel):
            value: str | None = None
            optional: str | None = None

        params = ParamsWithOptional(optional="set")
        config = build_config_from_flat_fields(
            params,
            ConfigWithRequired,
            ["value", "optional"],
        )
        # value=None is skipped, so default is used
        assert config.value == "default"
        assert config.optional == "set"

    def test_handles_missing_fields_gracefully(self):
        """Should handle fields that don't exist on params."""
        params = SampleParams()
        config = build_config_from_flat_fields(
            params,
            SampleConfig,
            ["concurrency", "nonexistent_field"],  # nonexistent is ignored
        )
        assert config.concurrency == 5  # Default


# ============================================================================
# Integration Tests
# ============================================================================


class TestRealWorldUsage:
    """Integration tests simulating real tool usage patterns."""

    def test_executor_style_with_dicts(self):
        """Should work when executor passes raw dicts."""
        # Executors often pass dicts, not Pydantic models
        raw_data = [
            {"url": "https://exec1.com"},
            {"url": "https://exec2.com", "metadata": {"key": "value"}},
        ]
        params = SampleParams(
            input_data=[SampleInput(**d) for d in raw_data],
            concurrency=10,
        )
        inputs = params.get_inputs()
        config = params.get_config()

        assert len(inputs) == 2
        assert inputs[0].url == "https://exec1.com"
        assert inputs[1].metadata == {"key": "value"}
        assert config.concurrency == 10

    def test_api_style_with_nested_models(self):
        """Should work with nested Pydantic models from API."""
        params = SampleParams(
            inputs=[
                SampleInput(url="https://api.com"),
            ],
            config=SampleConfig(
                concurrency=2,
                timeout_ms=5000,
            ),
        )
        inputs = params.get_inputs()
        config = params.get_config()

        assert len(inputs) == 1
        assert inputs[0].url == "https://api.com"
        assert config.concurrency == 2
        assert config.timeout_ms == 5000

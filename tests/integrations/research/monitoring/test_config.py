"""Tests for research monitoring configuration management."""

from pathlib import Path

import pytest
import yaml

from kurt.integrations.research.monitoring.config import (
    get_enabled_sources,
    get_monitoring_config_path,
    get_project_research_dir,
    get_project_signals_dir,
    load_monitoring_config,
    monitoring_config_exists,
    validate_monitoring_config,
)


class TestMonitoringConfigPaths:
    """Test path generation functions."""

    def test_get_monitoring_config_path(self, tmp_path):
        """Test getting monitoring config path."""
        project_path = str(tmp_path / "my-project")
        config_path = get_monitoring_config_path(project_path)

        assert config_path == Path(project_path) / "monitoring-config.yaml"

    def test_get_project_research_dir_creates_directory(self, tmp_path):
        """Test that research directory is created if it doesn't exist."""
        project_path = str(tmp_path / "my-project")

        research_dir = get_project_research_dir(project_path)

        assert research_dir.exists()
        assert research_dir.is_dir()
        assert research_dir.name == "research"

    def test_get_project_research_dir_existing(self, tmp_path):
        """Test getting research directory when it already exists."""
        project_path = tmp_path / "my-project"
        project_path.mkdir()
        research_dir = project_path / "research"
        research_dir.mkdir()

        result = get_project_research_dir(str(project_path))

        assert result == research_dir

    def test_get_project_signals_dir_creates_directory(self, tmp_path):
        """Test that signals directory is created if it doesn't exist."""
        project_path = str(tmp_path / "my-project")

        signals_dir = get_project_signals_dir(project_path)

        assert signals_dir.exists()
        assert signals_dir.is_dir()
        assert signals_dir.name == "signals"
        assert signals_dir.parent.name == "research"

    def test_get_project_signals_dir_existing(self, tmp_path):
        """Test getting signals directory when it already exists."""
        project_path = tmp_path / "my-project"
        project_path.mkdir()
        research_dir = project_path / "research"
        research_dir.mkdir()
        signals_dir = research_dir / "signals"
        signals_dir.mkdir()

        result = get_project_signals_dir(str(project_path))

        assert result == signals_dir


class TestMonitoringConfigExists:
    """Test monitoring_config_exists function."""

    def test_config_exists_true(self, tmp_path):
        """Test when monitoring config exists."""
        project_path = tmp_path / "my-project"
        project_path.mkdir()
        config_file = project_path / "monitoring-config.yaml"
        config_file.write_text("project_name: test")

        assert monitoring_config_exists(str(project_path)) is True

    def test_config_exists_false(self, tmp_path):
        """Test when monitoring config doesn't exist."""
        project_path = tmp_path / "my-project"
        project_path.mkdir()

        assert monitoring_config_exists(str(project_path)) is False


class TestLoadMonitoringConfig:
    """Test load_monitoring_config function."""

    def test_load_valid_config(self, tmp_path):
        """Test loading valid monitoring config."""
        project_path = tmp_path / "my-project"
        project_path.mkdir()

        config_data = {
            "project_name": "Test Project",
            "sources": {"reddit": {"enabled": True, "subreddits": ["python", "machinelearning"]}},
        }

        config_file = project_path / "monitoring-config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        loaded = load_monitoring_config(str(project_path))

        assert loaded["project_name"] == "Test Project"
        assert "reddit" in loaded["sources"]
        assert loaded["sources"]["reddit"]["enabled"] is True
        assert loaded["sources"]["reddit"]["subreddits"] == ["python", "machinelearning"]

    def test_load_config_not_found(self, tmp_path):
        """Test loading config when file doesn't exist."""
        project_path = tmp_path / "my-project"
        project_path.mkdir()

        with pytest.raises(FileNotFoundError) as exc_info:
            load_monitoring_config(str(project_path))

        assert "Monitoring config not found" in str(exc_info.value)
        assert "monitoring-config.yaml" in str(exc_info.value)

    def test_load_invalid_yaml(self, tmp_path):
        """Test loading config with invalid YAML."""
        project_path = tmp_path / "my-project"
        project_path.mkdir()

        config_file = project_path / "monitoring-config.yaml"
        config_file.write_text("invalid: yaml: syntax: [unclosed")

        with pytest.raises(ValueError) as exc_info:
            load_monitoring_config(str(project_path))

        assert "Invalid YAML" in str(exc_info.value)

    def test_load_complex_config(self, tmp_path):
        """Test loading complex config with multiple sources."""
        project_path = tmp_path / "my-project"
        project_path.mkdir()

        config_data = {
            "project_name": "Multi-Source Project",
            "sources": {
                "reddit": {"enabled": True, "subreddits": ["python", "datascience"]},
                "hackernews": {"enabled": True, "keywords": ["AI", "machine learning"]},
                "feeds": {"enabled": False, "urls": ["https://example.com/feed"]},
            },
        }

        config_file = project_path / "monitoring-config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        loaded = load_monitoring_config(str(project_path))

        assert len(loaded["sources"]) == 3
        assert loaded["sources"]["reddit"]["enabled"] is True
        assert loaded["sources"]["hackernews"]["enabled"] is True
        assert loaded["sources"]["feeds"]["enabled"] is False


class TestGetEnabledSources:
    """Test get_enabled_sources function."""

    def test_get_enabled_sources_single(self, tmp_path):
        """Test getting enabled sources with one source enabled."""
        config = {"sources": {"reddit": {"enabled": True}, "hackernews": {"enabled": False}}}

        enabled = get_enabled_sources(config)

        assert enabled == ["reddit"]

    def test_get_enabled_sources_multiple(self, tmp_path):
        """Test getting enabled sources with multiple enabled."""
        config = {
            "sources": {
                "reddit": {"enabled": True},
                "hackernews": {"enabled": True},
                "feeds": {"enabled": False},
            }
        }

        enabled = get_enabled_sources(config)

        assert set(enabled) == {"reddit", "hackernews"}

    def test_get_enabled_sources_none(self, tmp_path):
        """Test getting enabled sources when none are enabled."""
        config = {"sources": {"reddit": {"enabled": False}, "hackernews": {"enabled": False}}}

        enabled = get_enabled_sources(config)

        assert enabled == []

    def test_get_enabled_sources_no_sources_key(self, tmp_path):
        """Test getting enabled sources when sources key missing."""
        config = {"project_name": "Test"}

        enabled = get_enabled_sources(config)

        assert enabled == []

    def test_get_enabled_sources_non_dict_source(self, tmp_path):
        """Test getting enabled sources with non-dict source config."""
        config = {"sources": {"reddit": "invalid_config", "hackernews": {"enabled": True}}}

        enabled = get_enabled_sources(config)

        # Should only include valid dict sources
        assert enabled == ["hackernews"]

    def test_get_enabled_sources_default_false(self, tmp_path):
        """Test that sources without 'enabled' key default to False."""
        config = {
            "sources": {
                "reddit": {"subreddits": ["python"]},  # No 'enabled' key
                "hackernews": {"enabled": True},
            }
        }

        enabled = get_enabled_sources(config)

        assert enabled == ["hackernews"]


class TestValidateMonitoringConfig:
    """Test validate_monitoring_config function."""

    def test_validate_valid_config(self, tmp_path):
        """Test validation with valid config."""
        config = {
            "project_name": "Test Project",
            "sources": {"reddit": {"enabled": True, "subreddits": ["python"]}},
        }

        warnings = validate_monitoring_config(config)

        assert warnings == []

    def test_validate_missing_project_name(self, tmp_path):
        """Test validation catches missing project_name."""
        config = {"sources": {"reddit": {"enabled": True}}}

        warnings = validate_monitoring_config(config)

        assert "Missing project_name" in warnings

    def test_validate_no_sources(self, tmp_path):
        """Test validation catches no sources configured."""
        config = {"project_name": "Test"}

        warnings = validate_monitoring_config(config)

        assert "No monitoring sources configured" in warnings

    def test_validate_no_enabled_sources(self, tmp_path):
        """Test validation catches no enabled sources."""
        config = {
            "project_name": "Test",
            "sources": {"reddit": {"enabled": False}, "hackernews": {"enabled": False}},
        }

        warnings = validate_monitoring_config(config)

        assert "No monitoring sources enabled" in warnings

    def test_validate_reddit_no_subreddits(self, tmp_path):
        """Test validation catches Reddit enabled without subreddits."""
        config = {
            "project_name": "Test",
            "sources": {
                "reddit": {"enabled": True}  # Missing subreddits
            },
        }

        warnings = validate_monitoring_config(config)

        assert any("Reddit" in w and "no subreddits" in w for w in warnings)

    def test_validate_reddit_empty_subreddits(self, tmp_path):
        """Test validation catches Reddit with empty subreddits list."""
        config = {
            "project_name": "Test",
            "sources": {"reddit": {"enabled": True, "subreddits": []}},
        }

        warnings = validate_monitoring_config(config)

        assert any("Reddit" in w and "no subreddits" in w for w in warnings)

    def test_validate_feeds_no_urls(self, tmp_path):
        """Test validation catches Feeds enabled without URLs."""
        config = {
            "project_name": "Test",
            "sources": {
                "feeds": {"enabled": True}  # Missing urls
            },
        }

        warnings = validate_monitoring_config(config)

        assert any("Feeds" in w and "no URLs" in w for w in warnings)

    def test_validate_feeds_empty_urls(self, tmp_path):
        """Test validation catches Feeds with empty URLs list."""
        config = {"project_name": "Test", "sources": {"feeds": {"enabled": True, "urls": []}}}

        warnings = validate_monitoring_config(config)

        assert any("Feeds" in w and "no URLs" in w for w in warnings)

    def test_validate_multiple_warnings(self, tmp_path):
        """Test validation returns multiple warnings."""
        config = {
            # Missing project_name
            "sources": {
                "reddit": {"enabled": True},  # Missing subreddits
                "feeds": {"enabled": True},  # Missing urls
            }
        }

        warnings = validate_monitoring_config(config)

        assert len(warnings) >= 3
        assert "Missing project_name" in warnings
        assert any("Reddit" in w for w in warnings)
        assert any("Feeds" in w for w in warnings)

    def test_validate_disabled_sources_not_validated(self, tmp_path):
        """Test that disabled sources are not validated."""
        config = {
            "project_name": "Test",
            "sources": {
                "reddit": {
                    "enabled": False
                    # No subreddits, but it's disabled so shouldn't warn
                }
            },
        }

        warnings = validate_monitoring_config(config)

        # Should warn about no enabled sources, but not about missing subreddits
        assert "No monitoring sources enabled" in warnings
        assert not any("subreddits" in w for w in warnings)


class TestIntegration:
    """Integration tests for monitoring config workflow."""

    def test_full_workflow(self, tmp_path):
        """Test complete workflow: create, load, validate."""
        project_path = tmp_path / "my-project"
        project_path.mkdir()

        # Create config
        config_data = {
            "project_name": "Integration Test",
            "sources": {
                "reddit": {"enabled": True, "subreddits": ["python", "machinelearning"]},
                "hackernews": {"enabled": False, "keywords": ["AI"]},
            },
        }

        config_file = get_monitoring_config_path(str(project_path))
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        # Check existence
        assert monitoring_config_exists(str(project_path)) is True

        # Load config
        loaded = load_monitoring_config(str(project_path))
        assert loaded["project_name"] == "Integration Test"

        # Validate
        warnings = validate_monitoring_config(loaded)
        assert warnings == []

        # Get enabled sources
        enabled = get_enabled_sources(loaded)
        assert enabled == ["reddit"]

        # Check research directories
        research_dir = get_project_research_dir(str(project_path))
        assert research_dir.exists()

        signals_dir = get_project_signals_dir(str(project_path))
        assert signals_dir.exists()
        assert signals_dir.parent == research_dir

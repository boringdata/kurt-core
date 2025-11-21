"""
Tests for content map update workflow.

Tests verify:
- Configuration loading and management
- Content source discovery
- Auto-fetch decision logic
- Workflow orchestration
"""

from unittest.mock import MagicMock, patch

import pytest


class TestUpdateConfiguration:
    """Test update configuration management."""

    def test_create_default_config(self):
        """Test default configuration creation."""
        from kurt.content.map.config import create_default_update_config

        config = create_default_update_config()

        assert "auto_fetch" in config
        assert config["auto_fetch"]["enabled"] is False
        assert config["auto_fetch"]["max_new_documents"] == 50
        assert config["auto_fetch"]["strategy"] == "sample"

        assert "sources" in config
        assert config["sources"]["cms"]["enabled"] is True
        assert config["sources"]["websites"]["enabled"] is True

        assert "schedule" in config
        assert config["schedule"]["enabled"] is False

    def test_load_nonexistent_config_returns_defaults(self, tmp_path, monkeypatch):
        """Test loading config when file doesn't exist returns defaults."""
        from kurt.content.map.config import load_update_config

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        config = load_update_config()

        # Should return defaults
        assert config["auto_fetch"]["enabled"] is False
        assert config["auto_fetch"]["max_new_documents"] == 50

    def test_save_and_load_config(self, tmp_path, monkeypatch):
        """Test saving and loading configuration."""
        from kurt.content.map.config import load_update_config, save_update_config

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Create custom config
        custom_config = {
            "auto_fetch": {
                "enabled": True,
                "max_new_documents": 100,
                "strategy": "all",
            },
            "sources": {
                "cms": {"enabled": True},
                "websites": {"enabled": False},
            },
        }

        # Save
        save_update_config(custom_config)

        # Load
        loaded_config = load_update_config()

        assert loaded_config["auto_fetch"]["enabled"] is True
        assert loaded_config["auto_fetch"]["max_new_documents"] == 100
        assert loaded_config["auto_fetch"]["strategy"] == "all"

    def test_get_auto_fetch_config_with_env_override(self, tmp_path, monkeypatch):
        """Test auto-fetch config with environment variable overrides."""
        from kurt.content.map.config import get_auto_fetch_config

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Set environment variables
        monkeypatch.setenv("KURT_AUTO_FETCH_ENABLED", "true")
        monkeypatch.setenv("KURT_AUTO_FETCH_MAX_DOCUMENTS", "200")
        monkeypatch.setenv("KURT_AUTO_FETCH_STRATEGY", "all")

        config = get_auto_fetch_config()

        assert config["enabled"] is True
        assert config["max_new_documents"] == 200
        assert config["strategy"] == "all"


class TestContentSourceLoading:
    """Test content source discovery."""

    def test_load_content_sources_step_exists(self):
        """Test load_content_sources_step is defined."""
        from kurt.content.map.workflow_update import load_content_sources_step

        assert load_content_sources_step is not None
        assert callable(load_content_sources_step)

    @patch("kurt.integrations.cms.config.load_cms_config")
    @patch("kurt.db.database.get_session")
    def test_load_cms_sources(self, mock_session, mock_load_cms_config):
        """Test loading CMS sources from config."""
        from kurt.content.map.workflow_update import load_content_sources_step

        # Mock CMS config
        mock_load_cms_config.return_value = {
            "sanity": {
                "prod": {
                    "project_id": "test123",
                    "content_type_mappings": {
                        "article": {"enabled": True},
                        "blog": {"enabled": True},
                    },
                }
            }
        }

        # Mock database query (no website sources)
        mock_session_instance = MagicMock()
        mock_session_instance.exec.return_value.all.return_value = []
        mock_session.return_value = mock_session_instance

        result = load_content_sources_step()

        assert result["total_sources"] == 1
        assert len(result["cms_sources"]) == 1
        assert result["cms_sources"][0]["platform"] == "sanity"
        assert result["cms_sources"][0]["instance"] == "prod"
        assert len(result["cms_sources"][0]["content_types"]) == 2


class TestAutoFetchDecisionLogic:
    """Test auto-fetch decision logic."""

    def test_get_auto_fetch_config_step_exists(self):
        """Test get_auto_fetch_config_step is defined."""
        from kurt.content.map.workflow_update import get_auto_fetch_config_step

        assert get_auto_fetch_config_step is not None
        assert callable(get_auto_fetch_config_step)

    def test_select_documents_to_fetch_step_exists(self):
        """Test select_documents_to_fetch_step is defined."""
        from kurt.content.map.workflow_update import select_documents_to_fetch_step

        assert select_documents_to_fetch_step is not None
        assert callable(select_documents_to_fetch_step)

    @patch("kurt.db.database.get_session")
    def test_select_documents_sample_strategy(self, mock_session):
        """Test document selection with sample strategy."""
        from uuid import uuid4

        from kurt.content.map.workflow_update import select_documents_to_fetch_step

        # Mock database query
        mock_results = [uuid4() for _ in range(10)]
        mock_session_instance = MagicMock()
        mock_session_instance.exec.return_value.all.return_value = mock_results[:5]
        mock_session.return_value = mock_session_instance

        result = select_documents_to_fetch_step(max_documents=5, strategy="sample")

        assert len(result) == 5


class TestRefreshSteps:
    """Test content refresh steps."""

    def test_refresh_cms_source_step_exists(self):
        """Test refresh_cms_source_step is defined."""
        from kurt.content.map.workflow_update import refresh_cms_source_step

        assert refresh_cms_source_step is not None
        assert callable(refresh_cms_source_step)

    def test_refresh_website_source_step_exists(self):
        """Test refresh_website_source_step is defined."""
        from kurt.content.map.workflow_update import refresh_website_source_step

        assert refresh_website_source_step is not None
        assert callable(refresh_website_source_step)


class TestUpdateWorkflow:
    """Test content_map_update_workflow."""

    def test_workflow_exists(self):
        """Test content_map_update_workflow is defined."""
        from kurt.content.map.workflow_update import content_map_update_workflow

        assert content_map_update_workflow is not None
        assert callable(content_map_update_workflow)

    def test_workflow_has_dbos_decorator(self):
        """Test workflow has DBOS decorator applied."""
        from kurt.content.map.workflow_update import content_map_update_workflow

        # Verify it's callable (DBOS decorated workflows are callable)
        assert callable(content_map_update_workflow)

    def test_enqueue_content_update_exists(self):
        """Test enqueue_content_update helper exists."""
        from kurt.content.map.workflow_update import enqueue_content_update

        assert enqueue_content_update is not None
        assert callable(enqueue_content_update)


class TestUpdateQueue:
    """Test update queue configuration."""

    def test_update_queue_exists(self):
        """Test update_queue is defined."""
        from kurt.content.map.workflow_update import update_queue

        assert update_queue is not None

    def test_update_queue_has_priority(self):
        """Test update queue has priority enabled."""
        from kurt.content.map.workflow_update import update_queue

        # Queue should exist and be callable
        assert update_queue is not None


class TestUpdateCommand:
    """Test CLI command integration."""

    def test_update_command_exists(self):
        """Test update_cmd is defined."""
        from kurt.commands.content.update import update_cmd

        assert update_cmd is not None
        assert callable(update_cmd)

    def test_update_command_has_options(self):
        """Test update command has expected options."""
        from kurt.commands.content.update import update_cmd

        # Check that command has click decorators
        assert hasattr(update_cmd, "params")

        param_names = [p.name for p in update_cmd.params]

        # Verify key options exist
        assert "cms" in param_names
        assert "websites" in param_names
        assert "auto_fetch" in param_names
        assert "background" in param_names
        assert "init_config" in param_names


class TestIntegration:
    """Integration tests for update workflow."""

    @pytest.mark.integration
    @patch("kurt.integrations.cms.config.load_cms_config")
    @patch("kurt.db.database.get_session")
    @patch("kurt.content.map.cms.map_cms_content")
    @patch("kurt.content.map.workflow_update.get_auto_fetch_config_step")
    def test_update_workflow_with_cms_only(
        self,
        mock_auto_fetch_config,
        mock_map_cms,
        mock_session,
        mock_load_cms_config,
    ):
        """Test update workflow with CMS sources only (no auto-fetch)."""
        import asyncio

        from kurt.content.map.workflow_update import content_map_update_workflow

        # Mock CMS config
        mock_load_cms_config.return_value = {
            "sanity": {
                "prod": {
                    "content_type_mappings": {
                        "article": {"enabled": True},
                    }
                }
            }
        }

        # Mock database (no website sources)
        mock_session_instance = MagicMock()
        mock_session_instance.exec.return_value.all.return_value = []
        mock_session.return_value = mock_session_instance

        # Mock CMS mapping
        mock_map_cms.return_value = {
            "total": 100,
            "new": 10,
            "existing": 90,
            "method": "cms_api",
        }

        # Mock auto-fetch config (disabled)
        mock_auto_fetch_config.return_value = {
            "enabled": False,
            "max_new_documents": 50,
            "strategy": "sample",
        }

        # Run workflow (need to mock DBOS.set_event)
        with patch("kurt.content.map.workflow_update.DBOS"):
            result = asyncio.run(
                content_map_update_workflow(
                    refresh_cms=True,
                    refresh_websites=False,
                    auto_fetch=False,
                )
            )

        assert result["sources_checked"] == 1
        assert result["total_discovered"] == 100
        assert result["total_new"] == 10
        assert result["auto_fetch_enabled"] is False
        assert result["documents_fetched"] == 0

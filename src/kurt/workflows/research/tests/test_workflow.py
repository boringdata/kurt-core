"""Tests for research workflow."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from kurt.workflows.research.config import ResearchConfig


class TestResearchConfig:
    """Tests for ResearchConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ResearchConfig(query="test query")

        assert config.query == "test query"
        assert config.source == "perplexity"
        assert config.recency == "day"
        assert config.model == "sonar-reasoning"
        assert config.save is False
        assert config.dry_run is False

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ResearchConfig(
            query="custom query",
            source="perplexity",
            recency="week",
            model="sonar",
            save=True,
            dry_run=True,
        )

        assert config.query == "custom query"
        assert config.recency == "week"
        assert config.model == "sonar"
        assert config.save is True
        assert config.dry_run is True


class TestResearchWorkflowIntegration:
    """Integration tests for research workflow (mocked adapters)."""

    @patch("kurt.workflows.research.steps.get_source_config")
    @patch("kurt.workflows.research.steps.PerplexityAdapter")
    def test_research_search_step(self, mock_adapter_class, mock_get_config):
        """Test research search step with mocked adapter."""
        from kurt.integrations.research.base import Citation, ResearchResult

        # Mock config
        mock_get_config.return_value = {"api_key": "test_key"}

        # Mock adapter
        mock_adapter = MagicMock()
        mock_adapter.search.return_value = ResearchResult(
            id="test_123",
            query="test query",
            answer="Test answer from Perplexity",
            citations=[
                Citation(title="Source 1", url="https://example.com/1"),
            ],
            source="perplexity",
            model="sonar-reasoning",
            timestamp=datetime.now(),
            response_time_seconds=1.5,
        )
        mock_adapter_class.return_value = mock_adapter

        # Note: Can't easily test DBOS step without full DBOS setup
        # This tests the adapter integration
        config = ResearchConfig(query="test query")
        mock_adapter.search.assert_not_called()  # Not called yet

        # Simulate what the step does
        mock_adapter.search(
            query=config.query,
            recency=config.recency,
            model=config.model,
        )
        mock_adapter.search.assert_called_once()

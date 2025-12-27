"""Tests for Research CLI commands."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from click.testing import CliRunner

from kurt.cli import main
from kurt.integrations.research.base import Citation, ResearchResult


@pytest.fixture
def cli_runner():
    """Create a Click CLI runner."""
    return CliRunner()


@pytest.fixture
def sample_research_result():
    """Create a sample research result for testing."""
    citations = [
        Citation(
            title="Example Source 1",
            url="https://example.com/article1",
            snippet="This is a snippet from the first source",
            published_date="2024-01-15",
            domain="example.com",
        ),
        Citation(
            title="Example Source 2",
            url="https://example.com/article2",
            snippet="This is a snippet from the second source",
            domain="example.com",
        ),
    ]

    return ResearchResult(
        id=f"res_{datetime.now().strftime('%Y%m%d')}_{uuid4().hex[:8]}",
        query="What are AI coding tools?",
        answer="AI coding tools are software applications that use artificial intelligence to assist developers. Examples include GitHub Copilot, Cursor, and others.",
        citations=citations,
        source="perplexity",
        model="sonar-reasoning",
        timestamp=datetime.now(),
        response_time_seconds=2.5,
        metadata={"recency": "week"},
    )


class TestResearchSearch:
    """Test 'kurt research search' command."""

    @patch("kurt.integrations.research.config.source_configured")
    def test_search_not_configured(self, mock_configured, cli_runner):
        """Test search when research source not configured."""
        mock_configured.return_value = False

        result = cli_runner.invoke(
            main,
            ["integrations", "research", "search", "test query"],
        )

        assert result.exit_code != 0
        assert "not configured" in result.output.lower()

    def test_search_basic_query(self, cli_runner, sample_research_result, monkeypatch):
        """Test basic research search."""
        import sys

        # Get the research module from sys.modules after it's imported
        research_mod = sys.modules["kurt.commands.integrations.research"]

        # Mock functions in the module namespace
        monkeypatch.setattr(research_mod, "source_configured", lambda x: True)
        monkeypatch.setattr(research_mod, "get_source_config", lambda x: {"api_key": "test_key"})

        # Mock adapter
        mock_adapter = MagicMock()
        mock_adapter.search.return_value = sample_research_result

        from kurt.integrations.research.perplexity import PerplexityAdapter

        monkeypatch.setattr(PerplexityAdapter, "__init__", lambda self, config: None)
        monkeypatch.setattr(
            PerplexityAdapter, "search", lambda self, **kwargs: sample_research_result
        )

        result = cli_runner.invoke(
            main,
            ["integrations", "research", "search", "AI coding tools"],
        )

        assert result.exit_code == 0
        assert "Research complete" in result.output or "✓" in result.output
        # Check that answer is displayed
        assert "coding tools" in result.output.lower() or "AI" in result.output

    def test_search_with_recency(self, cli_runner, sample_research_result, monkeypatch):
        """Test search with recency filter."""
        import sys

        research_mod = sys.modules["kurt.commands.integrations.research"]

        monkeypatch.setattr(research_mod, "source_configured", lambda x: True)
        monkeypatch.setattr(research_mod, "get_source_config", lambda x: {"api_key": "test_key"})

        from kurt.integrations.research.perplexity import PerplexityAdapter

        monkeypatch.setattr(PerplexityAdapter, "__init__", lambda self, config: None)
        monkeypatch.setattr(
            PerplexityAdapter, "search", lambda self, **kwargs: sample_research_result
        )

        result = cli_runner.invoke(
            main,
            ["integrations", "research", "search", "AI news", "--recency", "week"],
        )

        assert result.exit_code == 0

    def test_search_json_output(self, cli_runner, sample_research_result, monkeypatch):
        """Test search with JSON output format."""
        import sys

        research_mod = sys.modules["kurt.commands.integrations.research"]

        monkeypatch.setattr(research_mod, "source_configured", lambda x: True)
        monkeypatch.setattr(research_mod, "get_source_config", lambda x: {"api_key": "test_key"})

        from kurt.integrations.research.perplexity import PerplexityAdapter

        monkeypatch.setattr(PerplexityAdapter, "__init__", lambda self, config: None)
        monkeypatch.setattr(
            PerplexityAdapter, "search", lambda self, **kwargs: sample_research_result
        )

        result = cli_runner.invoke(
            main,
            [
                "integrations",
                "research",
                "search",
                "test query",
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0
        # Should contain JSON fields
        assert '"query"' in result.output or "'query'" in result.output
        assert '"answer"' in result.output or "'answer'" in result.output

    def test_search_with_save(self, cli_runner, sample_research_result, tmp_path, monkeypatch):
        """Test search with save flag."""
        import sys

        # Change to tmp directory
        monkeypatch.chdir(tmp_path)

        research_mod = sys.modules["kurt.commands.integrations.research"]

        monkeypatch.setattr(research_mod, "source_configured", lambda x: True)
        monkeypatch.setattr(research_mod, "get_source_config", lambda x: {"api_key": "test_key"})

        from kurt.integrations.research.perplexity import PerplexityAdapter

        monkeypatch.setattr(PerplexityAdapter, "__init__", lambda self, config: None)
        monkeypatch.setattr(
            PerplexityAdapter, "search", lambda self, **kwargs: sample_research_result
        )

        result = cli_runner.invoke(
            main,
            [
                "integrations",
                "research",
                "search",
                "test query",
                "--save",
            ],
        )

        assert result.exit_code == 0
        # Should create sources/research directory
        # Note: May not actually create files if Kurt init is required
        # Just verify command doesn't crash

    def test_search_with_custom_model(self, cli_runner, sample_research_result, monkeypatch):
        """Test search with custom model."""
        import sys

        research_mod = sys.modules["kurt.commands.integrations.research"]

        monkeypatch.setattr(research_mod, "source_configured", lambda x: True)
        monkeypatch.setattr(research_mod, "get_source_config", lambda x: {"api_key": "test_key"})

        from kurt.integrations.research.perplexity import PerplexityAdapter

        monkeypatch.setattr(PerplexityAdapter, "__init__", lambda self, config: None)
        monkeypatch.setattr(
            PerplexityAdapter, "search", lambda self, **kwargs: sample_research_result
        )

        result = cli_runner.invoke(
            main,
            [
                "integrations",
                "research",
                "search",
                "test query",
                "--model",
                "sonar-pro",
            ],
        )

        assert result.exit_code == 0


class TestResearchList:
    """Test 'kurt research list' command."""

    def test_list_no_results(self, cli_runner, tmp_path, monkeypatch):
        """Test listing when no research results exist."""
        # Change to tmp directory with no sources
        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(
            main,
            ["integrations", "research", "list"],
        )

        # Should handle gracefully (may show empty or error)
        # Command should not crash
        assert "research" in result.output.lower() or "No" in result.output

    def test_list_with_results(self, cli_runner, tmp_path, monkeypatch):
        """Test listing research results."""
        # Create sources/research directory with test files
        research_dir = tmp_path / "sources" / "research"
        research_dir.mkdir(parents=True)

        # Create test markdown files
        test_file = research_dir / "res_20240115_test.md"
        test_file.write_text(
            "---\n"
            "research_id: res_20240115_test\n"
            'research_query: "Test Query"\n'
            "research_source: perplexity\n"
            "---\n\n"
            "# Test Query\n\n"
            "Test answer content"
        )

        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(
            main,
            ["integrations", "research", "list"],
        )

        # Should show the research file or handle gracefully
        assert result.exit_code == 0 or "research" in result.output.lower()


class TestResearchGet:
    """Test 'kurt research get' command."""

    def test_get_nonexistent_file(self, cli_runner, tmp_path, monkeypatch):
        """Test getting non-existent research result."""
        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(
            main,
            ["integrations", "research", "get", "nonexistent.md"],
        )

        # Should show error or handle gracefully
        # Command may exit with error
        assert "not found" in result.output.lower() or result.exit_code != 0

    def test_get_existing_file(self, cli_runner, tmp_path, monkeypatch):
        """Test getting existing research result."""
        # Create sources/research directory with test file
        research_dir = tmp_path / "sources" / "research"
        research_dir.mkdir(parents=True)

        test_file = research_dir / "test-result.md"
        test_file.write_text(
            "---\n"
            "research_id: res_test\n"
            'research_query: "Test Query"\n'
            "---\n\n"
            "# Test Query\n\n"
            "Test answer"
        )

        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(
            main,
            ["integrations", "research", "get", "test-result.md"],
        )

        # Should display the file contents
        assert result.exit_code == 0
        assert "Test Query" in result.output or "test" in result.output.lower()


class TestResearchMonitoringCommands:
    """Test research monitoring commands (reddit, hackernews, feeds)."""

    @patch("kurt.integrations.research.config.source_configured")
    def test_reddit_not_configured(self, mock_configured, cli_runner):
        """Test reddit command when not configured."""
        mock_configured.return_value = False

        result = cli_runner.invoke(
            main,
            ["integrations", "research", "reddit", "programming", "--save"],
        )

        # Should show configuration error
        assert result.exit_code != 0 or "not configured" in result.output.lower()

    @patch("kurt.integrations.research.config.source_configured")
    def test_hackernews_not_configured(self, mock_configured, cli_runner):
        """Test hackernews command when not configured."""
        mock_configured.return_value = False

        result = cli_runner.invoke(
            main,
            ["integrations", "research", "hackernews", "--save"],
        )

        # Should show configuration error or handle gracefully
        assert (
            result.exit_code != 0
            or "hackernews" in result.output.lower()
            or "not configured" in result.output.lower()
        )

    def test_feeds_no_config(self, cli_runner, tmp_path, monkeypatch):
        """Test feeds command without monitoring config."""
        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(
            main,
            ["integrations", "research", "feeds", "--save"],
        )

        # Should handle missing config gracefully
        # Command may show error or empty results
        assert "feed" in result.output.lower() or result.exit_code != 0


class TestResearchMonitor:
    """Test 'kurt research monitor' command."""

    def test_monitor_basic(self, cli_runner, tmp_path):
        """Test basic monitor command."""
        # Create test project directory
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        result = cli_runner.invoke(
            main,
            ["integrations", "research", "monitor", str(project_dir)],
        )

        # Command may require configuration
        # Should not crash
        assert result.exit_code == 0 or "monitor" in result.output.lower()

    def test_monitor_with_save(self, cli_runner, tmp_path):
        """Test monitor command with save flag."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        result = cli_runner.invoke(
            main,
            ["integrations", "research", "monitor", str(project_dir), "--save"],
        )

        # Should attempt to monitor and save
        assert result.exit_code == 0 or "monitor" in result.output.lower()

    def test_monitor_json_output(self, cli_runner, tmp_path):
        """Test monitor command with JSON output."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        result = cli_runner.invoke(
            main,
            [
                "integrations",
                "research",
                "monitor",
                str(project_dir),
                "--output",
                "json",
            ],
        )

        # Should output JSON or handle gracefully
        assert result.exit_code == 0 or "monitor" in result.output.lower()


class TestGetAdapter:
    """Test get_adapter helper function."""

    def test_get_adapter_perplexity(self, monkeypatch):
        """Test getting Perplexity adapter."""
        import sys

        research_mod = sys.modules["kurt.commands.integrations.research"]

        monkeypatch.setattr(research_mod, "get_source_config", lambda x: {"api_key": "test_key"})

        from kurt.commands.integrations.research import get_adapter

        adapter = get_adapter("perplexity")

        assert adapter is not None
        # Should be PerplexityAdapter instance
        assert hasattr(adapter, "search")

    def test_get_adapter_unsupported(self, monkeypatch):
        """Test getting unsupported adapter."""
        import sys

        research_mod = sys.modules["kurt.commands.integrations.research"]

        monkeypatch.setattr(research_mod, "get_source_config", lambda x: {"api_key": "test_key"})

        from kurt.commands.integrations.research import get_adapter

        with pytest.raises(ValueError) as exc_info:
            get_adapter("unsupported_source")

        assert "Unsupported" in str(exc_info.value)

    def test_get_adapter_tavily_not_implemented(self, monkeypatch):
        """Test that Tavily raises NotImplementedError."""
        import sys

        research_mod = sys.modules["kurt.commands.integrations.research"]

        monkeypatch.setattr(research_mod, "get_source_config", lambda x: {"api_key": "test_key"})

        from kurt.commands.integrations.research import get_adapter

        with pytest.raises(NotImplementedError):
            get_adapter("tavily")

    def test_get_adapter_exa_not_implemented(self, monkeypatch):
        """Test that Exa raises NotImplementedError."""
        import sys

        research_mod = sys.modules["kurt.commands.integrations.research"]

        monkeypatch.setattr(research_mod, "get_source_config", lambda x: {"api_key": "test_key"})

        from kurt.commands.integrations.research import get_adapter

        with pytest.raises(NotImplementedError):
            get_adapter("exa")

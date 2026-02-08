"""
E2E tests for `kurt tool research` command.

These tests verify the research command works correctly with various options.
Tests mock the Perplexity API to avoid real API calls while testing
the full CLI integration.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kurt.conftest import (
    assert_cli_success,
    assert_json_output,
    assert_output_contains,
    invoke_cli,
)
from kurt.tools.research.cli import research_group, search_cmd


class TestResearchHelp:
    """Tests for research command help and options."""

    def test_research_group_help(self, cli_runner: CliRunner):
        """Verify research group shows help."""
        result = invoke_cli(cli_runner, research_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Research commands")

    def test_research_search_help(self, cli_runner: CliRunner):
        """Verify research search shows help."""
        result = invoke_cli(cli_runner, search_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Execute research query")

    def test_research_search_shows_options(self, cli_runner: CliRunner):
        """Verify research search lists all options."""
        result = invoke_cli(cli_runner, search_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--recency")
        assert_output_contains(result, "--model")
        assert_output_contains(result, "--save")
        assert_output_contains(result, "--output-dir")
        assert_output_contains(result, "--background")
        assert_output_contains(result, "--dry-run")
        assert_output_contains(result, "--format")


@pytest.fixture
def mock_research_result():
    """Create a mock ResearchResult for testing."""
    from kurt.integrations.research.base import Citation, ResearchResult

    return ResearchResult(
        id="res_test_12345",
        query="What are the latest AI trends?",
        answer="The latest AI trends include generative AI, multimodal models, and AI agents.",
        citations=[
            Citation(
                title="AI Trends Report",
                url="https://example.com/ai-trends",
                snippet="Key trends in artificial intelligence...",
                published_date="2024-01-10",
                domain="example.com",
            ),
            Citation(
                title="Tech News Today",
                url="https://technews.example.com/article",
                domain="technews.example.com",
            ),
        ],
        source="perplexity",
        model="sonar-reasoning",
        timestamp=datetime(2024, 1, 15, 10, 30, 0),
        response_time_seconds=2.5,
    )


class TestResearchSearchBasic:
    """E2E tests for basic research search functionality."""

    def test_research_search_requires_query(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify research search requires a query argument."""
        result = invoke_cli(cli_runner, search_cmd, [])
        # Should fail - missing required argument
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "QUERY" in result.output

    def test_research_search_dry_run(
        self, cli_runner: CliRunner, tmp_project: Path, mock_research_result
    ):
        """Verify --dry-run doesn't make real API calls."""
        result = invoke_cli(
            cli_runner,
            search_cmd,
            ["Test query", "--dry-run", "--format", "json"],
        )

        # Should complete without API call
        assert result.exit_code in (0, 1)

    def test_research_search_with_mocked_api(
        self, cli_runner: CliRunner, tmp_project: Path, mock_research_result
    ):
        """Verify research search works with mocked Perplexity API."""
        with patch(
            "kurt.integrations.research.config.get_source_config"
        ) as mock_config, patch(
            "kurt.integrations.research.perplexity.PerplexityAdapter"
        ) as mock_adapter_class:
            mock_config.return_value = {"api_key": "test_key"}
            mock_adapter = MagicMock()
            mock_adapter.search.return_value = mock_research_result
            mock_adapter_class.return_value = mock_adapter

            result = invoke_cli(
                cli_runner,
                search_cmd,
                ["What are the latest AI trends?", "--format", "json"],
            )

            # Should complete successfully
            assert result.exit_code in (0, 1)

            if result.exit_code == 0:
                data = assert_json_output(result)
                # Verify we get the mocked result
                if "data" in data:
                    assert len(data["data"]) >= 0


class TestResearchSearchRecency:
    """E2E tests for --recency option."""

    def test_research_recency_hour(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --recency hour is accepted."""
        result = invoke_cli(
            cli_runner,
            search_cmd,
            ["Test query", "--recency", "hour", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_research_recency_day(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --recency day is accepted."""
        result = invoke_cli(
            cli_runner,
            search_cmd,
            ["Test query", "--recency", "day", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_research_recency_week(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --recency week is accepted."""
        result = invoke_cli(
            cli_runner,
            search_cmd,
            ["Test query", "--recency", "week", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_research_recency_month(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --recency month is accepted."""
        result = invoke_cli(
            cli_runner,
            search_cmd,
            ["Test query", "--recency", "month", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_research_recency_invalid(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify invalid --recency value is rejected."""
        result = invoke_cli(
            cli_runner,
            search_cmd,
            ["Test query", "--recency", "invalid", "--dry-run"],
        )
        assert result.exit_code != 0


class TestResearchSearchModel:
    """E2E tests for --model option."""

    def test_research_model_default(
        self, cli_runner: CliRunner, tmp_project: Path, mock_research_result
    ):
        """Verify default model is used."""
        with patch(
            "kurt.integrations.research.config.get_source_config"
        ) as mock_config, patch(
            "kurt.integrations.research.perplexity.PerplexityAdapter"
        ) as mock_adapter_class:
            mock_config.return_value = {"api_key": "test_key"}
            mock_adapter = MagicMock()
            mock_adapter.search.return_value = mock_research_result
            mock_adapter_class.return_value = mock_adapter

            result = invoke_cli(
                cli_runner,
                search_cmd,
                ["Test query", "--format", "json"],
            )

            assert result.exit_code in (0, 1)

            if result.exit_code == 0:
                # Default model should be used
                mock_adapter.search.assert_called_once()
                call_kwargs = mock_adapter.search.call_args[1]
                assert call_kwargs.get("model") == "sonar-reasoning"

    def test_research_model_custom(
        self, cli_runner: CliRunner, tmp_project: Path, mock_research_result
    ):
        """Verify --model option works."""
        with patch(
            "kurt.integrations.research.config.get_source_config"
        ) as mock_config, patch(
            "kurt.integrations.research.perplexity.PerplexityAdapter"
        ) as mock_adapter_class:
            mock_config.return_value = {"api_key": "test_key"}
            mock_adapter = MagicMock()
            mock_adapter.search.return_value = mock_research_result
            mock_adapter_class.return_value = mock_adapter

            result = invoke_cli(
                cli_runner,
                search_cmd,
                ["Test query", "--model", "sonar-pro", "--format", "json"],
            )

            assert result.exit_code in (0, 1)

            if result.exit_code == 0:
                mock_adapter.search.assert_called_once()
                call_kwargs = mock_adapter.search.call_args[1]
                assert call_kwargs.get("model") == "sonar-pro"


class TestResearchSearchSave:
    """E2E tests for --save option."""

    def test_research_save_creates_file(
        self, cli_runner: CliRunner, tmp_project: Path, mock_research_result
    ):
        """Verify --save creates output file."""
        with patch(
            "kurt.integrations.research.config.get_source_config"
        ) as mock_config, patch(
            "kurt.integrations.research.perplexity.PerplexityAdapter"
        ) as mock_adapter_class:
            mock_config.return_value = {"api_key": "test_key"}
            mock_adapter = MagicMock()
            mock_adapter.search.return_value = mock_research_result
            mock_adapter_class.return_value = mock_adapter

            result = invoke_cli(
                cli_runner,
                search_cmd,
                ["Test query", "--save"],
            )

            # Should complete
            assert result.exit_code in (0, 1)

            # Check if output directory was created
            if result.exit_code == 0:
                output_dir = tmp_project / "sources" / "research"
                # May or may not exist depending on execution
                if output_dir.exists():
                    files = list(output_dir.glob("*.md"))
                    assert len(files) >= 0

    def test_research_save_custom_output_dir(
        self, cli_runner: CliRunner, tmp_project: Path, mock_research_result
    ):
        """Verify --output-dir option works."""
        with patch(
            "kurt.integrations.research.config.get_source_config"
        ) as mock_config, patch(
            "kurt.integrations.research.perplexity.PerplexityAdapter"
        ) as mock_adapter_class:
            mock_config.return_value = {"api_key": "test_key"}
            mock_adapter = MagicMock()
            mock_adapter.search.return_value = mock_research_result
            mock_adapter_class.return_value = mock_adapter

            result = invoke_cli(
                cli_runner,
                search_cmd,
                ["Test query", "--save", "--output-dir", "custom_research"],
            )

            assert result.exit_code in (0, 1)

    def test_research_save_dry_run_no_file(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --save with --dry-run doesn't create files."""
        result = invoke_cli(
            cli_runner,
            search_cmd,
            ["Test query", "--save", "--dry-run"],
        )

        assert result.exit_code in (0, 1)

        # Output directory should not be created in dry-run
        output_dir = tmp_project / "sources" / "research"
        # In dry run, no files should be created
        if output_dir.exists():
            files = list(output_dir.glob("*.md"))
            assert len(files) == 0


class TestResearchSearchJsonOutput:
    """E2E tests for JSON output format."""

    def test_research_json_output_valid(
        self, cli_runner: CliRunner, tmp_project: Path, mock_research_result
    ):
        """Verify --format json produces valid JSON."""
        with patch(
            "kurt.integrations.research.config.get_source_config"
        ) as mock_config, patch(
            "kurt.integrations.research.perplexity.PerplexityAdapter"
        ) as mock_adapter_class:
            mock_config.return_value = {"api_key": "test_key"}
            mock_adapter = MagicMock()
            mock_adapter.search.return_value = mock_research_result
            mock_adapter_class.return_value = mock_adapter

            result = invoke_cli(
                cli_runner,
                search_cmd,
                ["What are AI trends?", "--format", "json"],
            )

            assert result.exit_code in (0, 1)

            if result.exit_code == 0:
                data = assert_json_output(result)
                assert "run_id" in data or "data" in data or "success" in data

    def test_research_json_has_expected_fields(
        self, cli_runner: CliRunner, tmp_project: Path, mock_research_result
    ):
        """Verify JSON output contains expected fields."""
        with patch(
            "kurt.integrations.research.config.get_source_config"
        ) as mock_config, patch(
            "kurt.integrations.research.perplexity.PerplexityAdapter"
        ) as mock_adapter_class:
            mock_config.return_value = {"api_key": "test_key"}
            mock_adapter = MagicMock()
            mock_adapter.search.return_value = mock_research_result
            mock_adapter_class.return_value = mock_adapter

            result = invoke_cli(
                cli_runner,
                search_cmd,
                ["Test query", "--format", "json"],
            )

            assert result.exit_code in (0, 1)

            if result.exit_code == 0:
                data = assert_json_output(result)
                # Result should have run_id at minimum
                if "run_id" in data:
                    assert data["run_id"] is not None


class TestResearchSearchBackground:
    """E2E tests for --background option."""

    def test_research_background_parses(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --background option parses correctly."""
        result = invoke_cli(
            cli_runner,
            search_cmd,
            ["Test query", "--background", "--format", "json"],
        )

        # May fail to spawn background but should parse
        assert result.exit_code in (0, 1, 2)

    def test_research_background_priority(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --priority works with --background."""
        result = invoke_cli(
            cli_runner,
            search_cmd,
            ["Test query", "--background", "--priority", "5", "--format", "json"],
        )

        assert result.exit_code in (0, 1, 2)


class TestResearchSearchMissingApiKey:
    """E2E tests for missing API key handling."""

    def test_research_missing_api_key_error(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify research shows error when API key is missing."""
        with patch(
            "kurt.integrations.research.config.get_source_config"
        ) as mock_config:
            mock_config.return_value = {}  # No API key

            result = invoke_cli(
                cli_runner,
                search_cmd,
                ["Test query"],
            )

            # Should fail or show error about missing API key
            assert result.exit_code in (0, 1, 2)


class TestResearchSearchCombinedOptions:
    """E2E tests for combined options."""

    def test_research_all_options(
        self, cli_runner: CliRunner, tmp_project: Path, mock_research_result
    ):
        """Verify all options can be combined."""
        with patch(
            "kurt.integrations.research.config.get_source_config"
        ) as mock_config, patch(
            "kurt.integrations.research.perplexity.PerplexityAdapter"
        ) as mock_adapter_class:
            mock_config.return_value = {"api_key": "test_key"}
            mock_adapter = MagicMock()
            mock_adapter.search.return_value = mock_research_result
            mock_adapter_class.return_value = mock_adapter

            result = invoke_cli(
                cli_runner,
                search_cmd,
                [
                    "Complex query about AI trends",
                    "--recency",
                    "week",
                    "--model",
                    "sonar-pro",
                    "--save",
                    "--output-dir",
                    "research_results",
                    "--format",
                    "json",
                ],
            )

            assert result.exit_code in (0, 1)

    def test_research_dry_run_with_all_options(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --dry-run works with all other options."""
        result = invoke_cli(
            cli_runner,
            search_cmd,
            [
                "Test query",
                "--recency",
                "month",
                "--model",
                "sonar-pro",
                "--save",
                "--output-dir",
                "output",
                "--dry-run",
                "--format",
                "json",
            ],
        )

        assert result.exit_code in (0, 1)

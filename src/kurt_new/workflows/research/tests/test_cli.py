"""Tests for research workflow CLI."""

from unittest.mock import patch

from click.testing import CliRunner

from kurt_new.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)


class TestResearchGroupHelp:
    """Tests for research group help and options."""

    def test_research_group_help(self, cli_runner: CliRunner):
        """Test research group shows help."""
        from kurt_new.workflows.research.cli import research_group

        result = invoke_cli(cli_runner, research_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Research commands")

    def test_search_help(self, cli_runner: CliRunner):
        """Test search command shows help."""
        from kurt_new.workflows.research.cli import research_group

        result = invoke_cli(cli_runner, research_group, ["search", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Execute research query")

    def test_search_shows_options(self, cli_runner: CliRunner):
        """Test search command lists options in help."""
        from kurt_new.workflows.research.cli import research_group

        result = invoke_cli(cli_runner, research_group, ["search", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--recency")
        assert_output_contains(result, "--model")
        assert_output_contains(result, "--save")
        assert_output_contains(result, "--background")
        assert_output_contains(result, "--dry-run")
        assert_output_contains(result, "--format")

    def test_search_recency_choices(self, cli_runner: CliRunner):
        """Test search --recency shows valid choices."""
        from kurt_new.workflows.research.cli import research_group

        result = invoke_cli(cli_runner, research_group, ["search", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "hour")
        assert_output_contains(result, "day")
        assert_output_contains(result, "week")
        assert_output_contains(result, "month")


class TestSearchCommand:
    """Tests for search command."""

    @patch("kurt_new.workflows.research.workflow.run_research")
    def test_search_basic(self, mock_run):
        """Test basic search command."""
        from kurt_new.workflows.research.cli import research_group

        mock_run.return_value = {
            "workflow_id": "test_123",
            "query": "test query",
            "source": "perplexity",
            "citations_count": 3,
            "response_time_seconds": 2.0,
            "result": {
                "answer": "Test answer",
                "citations": [],
                "model": "sonar-reasoning",
            },
            "dry_run": False,
        }

        runner = CliRunner()
        result = runner.invoke(research_group, ["search", "test query"])

        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("kurt_new.workflows.research.workflow.run_research")
    def test_search_with_options(self, mock_run):
        """Test search command with options."""
        from kurt_new.workflows.research.cli import research_group

        mock_run.return_value = {
            "workflow_id": "test_123",
            "query": "test query",
            "source": "perplexity",
            "citations_count": 0,
            "result": {"answer": "Test", "citations": []},
            "dry_run": True,
        }

        runner = CliRunner()
        result = runner.invoke(
            research_group,
            ["search", "test query", "--recency", "week", "--dry-run"],
        )

        assert result.exit_code == 0
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args.recency == "week"
        assert call_args.dry_run is True

    @patch("kurt_new.workflows.research.workflow.run_research")
    def test_search_json_output(self, mock_run):
        """Test search command with JSON output."""
        from kurt_new.workflows.research.cli import research_group

        mock_run.return_value = {
            "workflow_id": "test_123",
            "query": "test query",
            "result": {"answer": "Test", "citations": []},
        }

        runner = CliRunner()
        result = runner.invoke(
            research_group,
            ["search", "test query", "--format", "json"],
        )

        assert result.exit_code == 0
        assert '"workflow_id"' in result.output

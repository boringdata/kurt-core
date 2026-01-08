"""Tests for research workflow CLI."""

from unittest.mock import patch

from click.testing import CliRunner


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

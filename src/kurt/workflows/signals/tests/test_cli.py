"""Tests for signals workflow CLI."""

from unittest.mock import patch

from click.testing import CliRunner

from kurt.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)


class TestSignalsGroupHelp:
    """Tests for signals group help and options."""

    def test_signals_group_help(self, cli_runner: CliRunner):
        """Test signals group shows help."""
        from kurt.workflows.signals.cli import signals_group

        result = invoke_cli(cli_runner, signals_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Signal monitoring commands")

    def test_signals_list_commands(self, cli_runner: CliRunner):
        """Test signals group lists all commands."""
        from kurt.workflows.signals.cli import signals_group

        result = invoke_cli(cli_runner, signals_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "reddit")
        assert_output_contains(result, "hackernews")
        assert_output_contains(result, "feeds")


class TestRedditCommandHelp:
    """Tests for reddit command help and options."""

    def test_reddit_help(self, cli_runner: CliRunner):
        """Test reddit command shows help."""
        from kurt.workflows.signals.cli import signals_group

        result = invoke_cli(cli_runner, signals_group, ["reddit", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Monitor Reddit")

    def test_reddit_shows_options(self, cli_runner: CliRunner):
        """Test reddit command lists options in help."""
        from kurt.workflows.signals.cli import signals_group

        result = invoke_cli(cli_runner, signals_group, ["reddit", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--subreddit")
        assert_output_contains(result, "--timeframe")
        assert_output_contains(result, "--sort")
        assert_output_contains(result, "--keywords")
        assert_output_contains(result, "--min-score")
        assert_output_contains(result, "--limit")
        assert_output_contains(result, "--background")
        assert_output_contains(result, "--dry-run")
        assert_output_contains(result, "--format")

    def test_reddit_requires_subreddit(self, cli_runner: CliRunner):
        """Test reddit command requires --subreddit option."""
        from kurt.workflows.signals.cli import signals_group

        result = cli_runner.invoke(signals_group, ["reddit"])
        assert result.exit_code != 0


class TestHackernewsCommandHelp:
    """Tests for hackernews command help and options."""

    def test_hackernews_help(self, cli_runner: CliRunner):
        """Test hackernews command shows help."""
        from kurt.workflows.signals.cli import signals_group

        result = invoke_cli(cli_runner, signals_group, ["hackernews", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Monitor HackerNews")

    def test_hackernews_shows_options(self, cli_runner: CliRunner):
        """Test hackernews command lists options in help."""
        from kurt.workflows.signals.cli import signals_group

        result = invoke_cli(cli_runner, signals_group, ["hackernews", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--timeframe")
        assert_output_contains(result, "--keywords")
        assert_output_contains(result, "--min-score")
        assert_output_contains(result, "--limit")
        assert_output_contains(result, "--background")
        assert_output_contains(result, "--dry-run")
        assert_output_contains(result, "--format")


class TestFeedsCommandHelp:
    """Tests for feeds command help and options."""

    def test_feeds_help(self, cli_runner: CliRunner):
        """Test feeds command shows help."""
        from kurt.workflows.signals.cli import signals_group

        result = invoke_cli(cli_runner, signals_group, ["feeds", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Monitor RSS/Atom")

    def test_feeds_shows_options(self, cli_runner: CliRunner):
        """Test feeds command lists options in help."""
        from kurt.workflows.signals.cli import signals_group

        result = invoke_cli(cli_runner, signals_group, ["feeds", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--keywords")
        assert_output_contains(result, "--limit")
        assert_output_contains(result, "--background")
        assert_output_contains(result, "--dry-run")
        assert_output_contains(result, "--format")


class TestRedditCommand:
    """Tests for reddit command."""

    @patch("kurt.workflows.signals.workflow.run_signals")
    def test_reddit_basic(self, mock_run):
        """Test basic reddit command."""
        from kurt.workflows.signals.cli import signals_group

        mock_run.return_value = {
            "workflow_id": "test_123",
            "source": "reddit",
            "total_signals": 2,
            "signals": [
                {"title": "Post 1", "score": 100, "comment_count": 20},
                {"title": "Post 2", "score": 50, "comment_count": 10},
            ],
            "dry_run": False,
        }

        runner = CliRunner()
        result = runner.invoke(signals_group, ["reddit", "-s", "python"])

        assert result.exit_code == 0
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args.source == "reddit"
        assert call_args.subreddit == "python"

    @patch("kurt.workflows.signals.workflow.run_signals")
    def test_reddit_with_filters(self, mock_run):
        """Test reddit command with filters."""
        from kurt.workflows.signals.cli import signals_group

        mock_run.return_value = {
            "workflow_id": "test_123",
            "source": "reddit",
            "total_signals": 0,
            "signals": [],
            "dry_run": False,
        }

        runner = CliRunner()
        result = runner.invoke(
            signals_group,
            [
                "reddit",
                "-s",
                "python",
                "--timeframe",
                "week",
                "--min-score",
                "50",
                "--keywords",
                "async,fastapi",
            ],
        )

        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        assert call_args.timeframe == "week"
        assert call_args.min_score == 50
        assert call_args.keywords == "async,fastapi"


class TestHackernewsCommand:
    """Tests for hackernews command."""

    @patch("kurt.workflows.signals.workflow.run_signals")
    def test_hackernews_basic(self, mock_run):
        """Test basic hackernews command."""
        from kurt.workflows.signals.cli import signals_group

        mock_run.return_value = {
            "workflow_id": "test_123",
            "source": "hackernews",
            "total_signals": 1,
            "signals": [
                {"title": "HN Story", "score": 200, "comment_count": 50},
            ],
            "dry_run": False,
        }

        runner = CliRunner()
        result = runner.invoke(signals_group, ["hackernews"])

        assert result.exit_code == 0
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args.source == "hackernews"


class TestFeedsCommand:
    """Tests for feeds command."""

    @patch("kurt.workflows.signals.workflow.run_signals")
    def test_feeds_basic(self, mock_run):
        """Test basic feeds command."""
        from kurt.workflows.signals.cli import signals_group

        mock_run.return_value = {
            "workflow_id": "test_123",
            "source": "feeds",
            "total_signals": 1,
            "signals": [
                {"title": "RSS Entry", "score": 0, "comment_count": 0},
            ],
            "dry_run": False,
        }

        runner = CliRunner()
        result = runner.invoke(
            signals_group,
            ["feeds", "https://example.com/feed.xml"],
        )

        assert result.exit_code == 0
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args.source == "feeds"
        assert call_args.feed_url == "https://example.com/feed.xml"

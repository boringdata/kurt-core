"""Tests for signals workflow CLI."""

from unittest.mock import patch

from click.testing import CliRunner


class TestRedditCommand:
    """Tests for reddit command."""

    @patch("kurt_new.workflows.signals.workflow.run_signals")
    def test_reddit_basic(self, mock_run):
        """Test basic reddit command."""
        from kurt_new.workflows.signals.cli import signals_group

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

    @patch("kurt_new.workflows.signals.workflow.run_signals")
    def test_reddit_with_filters(self, mock_run):
        """Test reddit command with filters."""
        from kurt_new.workflows.signals.cli import signals_group

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

    @patch("kurt_new.workflows.signals.workflow.run_signals")
    def test_hackernews_basic(self, mock_run):
        """Test basic hackernews command."""
        from kurt_new.workflows.signals.cli import signals_group

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

    @patch("kurt_new.workflows.signals.workflow.run_signals")
    def test_feeds_basic(self, mock_run):
        """Test basic feeds command."""
        from kurt_new.workflows.signals.cli import signals_group

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

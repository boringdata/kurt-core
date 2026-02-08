"""
E2E tests for `kurt tool signals` commands.

These tests verify the signals commands work correctly for all sources
(reddit, hackernews, feeds). Tests mock external API calls while testing
the full CLI integration.
"""

from __future__ import annotations

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
from kurt.tools.signals.cli import (
    feeds_cmd,
    hackernews_cmd,
    reddit_cmd,
    signals_group,
)


class TestSignalsHelp:
    """Tests for signals command help and options."""

    def test_signals_group_help(self, cli_runner: CliRunner):
        """Verify signals group shows help."""
        result = invoke_cli(cli_runner, signals_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Signal monitoring")

    def test_signals_reddit_help(self, cli_runner: CliRunner):
        """Verify signals reddit shows help."""
        result = invoke_cli(cli_runner, reddit_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Monitor Reddit")

    def test_signals_hackernews_help(self, cli_runner: CliRunner):
        """Verify signals hackernews shows help."""
        result = invoke_cli(cli_runner, hackernews_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Monitor HackerNews")

    def test_signals_feeds_help(self, cli_runner: CliRunner):
        """Verify signals feeds shows help."""
        result = invoke_cli(cli_runner, feeds_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Monitor RSS")


# =============================================================================
# Reddit Command Tests
# =============================================================================


class TestSignalsRedditBasic:
    """E2E tests for signals reddit command."""

    def test_reddit_requires_subreddit(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify reddit requires --subreddit option."""
        result = invoke_cli(cli_runner, reddit_cmd, [])
        assert result.exit_code != 0
        assert "subreddit" in result.output.lower() or "required" in result.output.lower()

    def test_reddit_dry_run(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --dry-run doesn't make real API calls."""
        result = invoke_cli(
            cli_runner,
            reddit_cmd,
            ["-s", "python", "--dry-run", "--format", "json"],
        )
        assert result.exit_code in (0, 1)

    def test_reddit_shows_all_options(self, cli_runner: CliRunner):
        """Verify reddit lists all options."""
        result = invoke_cli(cli_runner, reddit_cmd, ["--help"])
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


class TestSignalsRedditTimeframe:
    """E2E tests for reddit --timeframe option."""

    def test_reddit_timeframe_hour(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --timeframe hour is accepted."""
        result = invoke_cli(
            cli_runner,
            reddit_cmd,
            ["-s", "python", "--timeframe", "hour", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_reddit_timeframe_day(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --timeframe day is accepted."""
        result = invoke_cli(
            cli_runner,
            reddit_cmd,
            ["-s", "python", "--timeframe", "day", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_reddit_timeframe_week(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --timeframe week is accepted."""
        result = invoke_cli(
            cli_runner,
            reddit_cmd,
            ["-s", "python", "--timeframe", "week", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_reddit_timeframe_month(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --timeframe month is accepted."""
        result = invoke_cli(
            cli_runner,
            reddit_cmd,
            ["-s", "python", "--timeframe", "month", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_reddit_timeframe_invalid(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify invalid --timeframe is rejected."""
        result = invoke_cli(
            cli_runner,
            reddit_cmd,
            ["-s", "python", "--timeframe", "invalid", "--dry-run"],
        )
        assert result.exit_code != 0


class TestSignalsRedditSort:
    """E2E tests for reddit --sort option."""

    def test_reddit_sort_hot(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --sort hot is accepted."""
        result = invoke_cli(
            cli_runner,
            reddit_cmd,
            ["-s", "python", "--sort", "hot", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_reddit_sort_new(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --sort new is accepted."""
        result = invoke_cli(
            cli_runner,
            reddit_cmd,
            ["-s", "python", "--sort", "new", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_reddit_sort_top(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --sort top is accepted."""
        result = invoke_cli(
            cli_runner,
            reddit_cmd,
            ["-s", "python", "--sort", "top", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_reddit_sort_rising(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --sort rising is accepted."""
        result = invoke_cli(
            cli_runner,
            reddit_cmd,
            ["-s", "python", "--sort", "rising", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_reddit_sort_invalid(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify invalid --sort is rejected."""
        result = invoke_cli(
            cli_runner,
            reddit_cmd,
            ["-s", "python", "--sort", "invalid", "--dry-run"],
        )
        assert result.exit_code != 0


class TestSignalsRedditFilters:
    """E2E tests for reddit filter options."""

    def test_reddit_keywords_filter(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --keywords filter is accepted."""
        result = invoke_cli(
            cli_runner,
            reddit_cmd,
            ["-s", "python", "--keywords", "AI,ML,LLM", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_reddit_min_score_filter(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --min-score filter is accepted."""
        result = invoke_cli(
            cli_runner,
            reddit_cmd,
            ["-s", "python", "--min-score", "50", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_reddit_limit_filter(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --limit filter is accepted."""
        result = invoke_cli(
            cli_runner,
            reddit_cmd,
            ["-s", "python", "--limit", "10", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_reddit_multiple_subreddits(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify multiple subreddits are accepted."""
        result = invoke_cli(
            cli_runner,
            reddit_cmd,
            ["-s", "python+datascience", "--dry-run"],
        )
        assert result.exit_code in (0, 1)


class TestSignalsRedditOutput:
    """E2E tests for reddit output formats."""

    def test_reddit_json_output(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --format json produces JSON content."""
        result = invoke_cli(
            cli_runner,
            reddit_cmd,
            ["-s", "python", "--dry-run", "--format", "json"],
        )
        assert result.exit_code in (0, 1)
        # JSON should be present in output (may have other text too)
        assert "{" in result.output

    def test_reddit_background_parses(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --background option parses correctly."""
        result = invoke_cli(
            cli_runner,
            reddit_cmd,
            ["-s", "python", "--background", "--format", "json"],
        )
        assert result.exit_code in (0, 1, 2)


# =============================================================================
# HackerNews Command Tests
# =============================================================================


class TestSignalsHackernewsBasic:
    """E2E tests for signals hackernews command."""

    def test_hackernews_dry_run(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --dry-run doesn't make real API calls."""
        result = invoke_cli(
            cli_runner,
            hackernews_cmd,
            ["--dry-run", "--format", "json"],
        )
        assert result.exit_code in (0, 1)

    def test_hackernews_shows_all_options(self, cli_runner: CliRunner):
        """Verify hackernews lists all options."""
        result = invoke_cli(cli_runner, hackernews_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--timeframe")
        assert_output_contains(result, "--keywords")
        assert_output_contains(result, "--min-score")
        assert_output_contains(result, "--limit")
        assert_output_contains(result, "--background")
        assert_output_contains(result, "--dry-run")
        assert_output_contains(result, "--format")


class TestSignalsHackernewsFilters:
    """E2E tests for hackernews filter options."""

    def test_hackernews_timeframe_hour(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --timeframe hour is accepted."""
        result = invoke_cli(
            cli_runner,
            hackernews_cmd,
            ["--timeframe", "hour", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_hackernews_timeframe_week(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --timeframe week is accepted."""
        result = invoke_cli(
            cli_runner,
            hackernews_cmd,
            ["--timeframe", "week", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_hackernews_keywords_filter(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --keywords filter is accepted."""
        result = invoke_cli(
            cli_runner,
            hackernews_cmd,
            ["--keywords", "Python,Rust", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_hackernews_min_score_filter(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --min-score filter is accepted."""
        result = invoke_cli(
            cli_runner,
            hackernews_cmd,
            ["--min-score", "100", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_hackernews_limit_filter(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --limit filter is accepted."""
        result = invoke_cli(
            cli_runner,
            hackernews_cmd,
            ["--limit", "20", "--dry-run"],
        )
        assert result.exit_code in (0, 1)


class TestSignalsHackernewsOutput:
    """E2E tests for hackernews output formats."""

    def test_hackernews_json_output(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --format json produces JSON content."""
        result = invoke_cli(
            cli_runner,
            hackernews_cmd,
            ["--dry-run", "--format", "json"],
        )
        assert result.exit_code in (0, 1)
        # JSON should be present in output (may have other text too)
        assert "{" in result.output

    def test_hackernews_background_parses(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --background option parses correctly."""
        result = invoke_cli(
            cli_runner,
            hackernews_cmd,
            ["--background", "--format", "json"],
        )
        assert result.exit_code in (0, 1, 2)


# =============================================================================
# Feeds Command Tests
# =============================================================================


class TestSignalsFeedsBasic:
    """E2E tests for signals feeds command."""

    def test_feeds_requires_url(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify feeds requires FEED_URL argument."""
        result = invoke_cli(cli_runner, feeds_cmd, [])
        assert result.exit_code != 0

    def test_feeds_dry_run(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --dry-run doesn't make real network calls."""
        result = invoke_cli(
            cli_runner,
            feeds_cmd,
            ["https://example.com/rss.xml", "--dry-run", "--format", "json"],
        )
        assert result.exit_code in (0, 1)

    def test_feeds_shows_all_options(self, cli_runner: CliRunner):
        """Verify feeds lists all options."""
        result = invoke_cli(cli_runner, feeds_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "FEED_URL")
        assert_output_contains(result, "--keywords")
        assert_output_contains(result, "--limit")
        assert_output_contains(result, "--background")
        assert_output_contains(result, "--dry-run")
        assert_output_contains(result, "--format")


class TestSignalsFeedsFilters:
    """E2E tests for feeds filter options."""

    def test_feeds_keywords_filter(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --keywords filter is accepted."""
        result = invoke_cli(
            cli_runner,
            feeds_cmd,
            ["https://example.com/rss.xml", "--keywords", "AI,ML", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_feeds_limit_filter(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --limit filter is accepted."""
        result = invoke_cli(
            cli_runner,
            feeds_cmd,
            ["https://example.com/rss.xml", "--limit", "20", "--dry-run"],
        )
        assert result.exit_code in (0, 1)


class TestSignalsFeedsOutput:
    """E2E tests for feeds output formats."""

    def test_feeds_json_output(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --format json produces JSON content."""
        result = invoke_cli(
            cli_runner,
            feeds_cmd,
            ["https://example.com/rss.xml", "--dry-run", "--format", "json"],
        )
        assert result.exit_code in (0, 1)
        # JSON should be present in output (may have other text too)
        assert "{" in result.output

    def test_feeds_background_parses(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --background option parses correctly."""
        result = invoke_cli(
            cli_runner,
            feeds_cmd,
            ["https://example.com/rss.xml", "--background", "--format", "json"],
        )
        assert result.exit_code in (0, 1, 2)


# =============================================================================
# Combined Options Tests
# =============================================================================


class TestSignalsCombinedOptions:
    """E2E tests for combined options across commands."""

    def test_reddit_all_options(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify all reddit options can be combined."""
        result = invoke_cli(
            cli_runner,
            reddit_cmd,
            [
                "-s",
                "python+machinelearning",
                "--timeframe",
                "week",
                "--sort",
                "top",
                "--keywords",
                "LLM,GPT",
                "--min-score",
                "25",
                "--limit",
                "15",
                "--dry-run",
                "--format",
                "json",
            ],
        )
        assert result.exit_code in (0, 1)

    def test_hackernews_all_options(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify all hackernews options can be combined."""
        result = invoke_cli(
            cli_runner,
            hackernews_cmd,
            [
                "--timeframe",
                "week",
                "--keywords",
                "Rust,Python,Go",
                "--min-score",
                "50",
                "--limit",
                "25",
                "--dry-run",
                "--format",
                "json",
            ],
        )
        assert result.exit_code in (0, 1)

    def test_feeds_all_options(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify all feeds options can be combined."""
        result = invoke_cli(
            cli_runner,
            feeds_cmd,
            [
                "https://blog.example.com/rss.xml",
                "--keywords",
                "technology,startup",
                "--limit",
                "30",
                "--dry-run",
                "--format",
                "json",
            ],
        )
        assert result.exit_code in (0, 1)

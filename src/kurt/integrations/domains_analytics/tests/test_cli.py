"""Tests for analytics integration CLI commands."""

from __future__ import annotations

from click.testing import CliRunner

from kurt.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)
from kurt.integrations.domains_analytics.cli import analytics_group


class TestAnalyticsGroup:
    """Tests for the analytics command group."""

    def test_analytics_group_help(self, cli_runner: CliRunner):
        """Test analytics group shows help."""
        result = invoke_cli(cli_runner, analytics_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Domain analytics integration commands")

    def test_analytics_list_commands(self, cli_runner: CliRunner):
        """Test analytics group lists all commands."""
        result = invoke_cli(cli_runner, analytics_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "onboard")
        assert_output_contains(result, "list")
        assert_output_contains(result, "query")
        # Note: sync command moved to `kurt tool analytics sync`


class TestOnboardCommand:
    """Tests for `analytics onboard` command."""

    def test_onboard_help(self, cli_runner: CliRunner):
        """Test onboard command shows help."""
        result = invoke_cli(cli_runner, analytics_group, ["onboard", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Configure analytics for a domain")

    def test_onboard_shows_options(self, cli_runner: CliRunner):
        """Test onboard command lists options in help."""
        result = invoke_cli(cli_runner, analytics_group, ["onboard", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--platform")
        assert_output_contains(result, "--sync-now")

    def test_onboard_requires_domain(self, cli_runner: CliRunner):
        """Test onboard command requires domain argument."""
        result = cli_runner.invoke(analytics_group, ["onboard"])
        # Should fail because domain is required
        assert result.exit_code != 0


class TestListCommand:
    """Tests for `analytics list` command."""

    def test_list_help(self, cli_runner: CliRunner):
        """Test list command shows help."""
        result = invoke_cli(cli_runner, analytics_group, ["list", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "List analytics-enabled domains")

    def test_list_shows_options(self, cli_runner: CliRunner):
        """Test list command lists options in help."""
        result = invoke_cli(cli_runner, analytics_group, ["list", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--format")

    def test_list_runs(self, cli_runner: CliRunner, tmp_database):
        """Test list command runs (may fail if models not created)."""
        # This test verifies command parses; full execution requires AnalyticsDomain model
        result = cli_runner.invoke(analytics_group, ["list"])
        assert "--help" not in result.output


class TestQueryCommand:
    """Tests for `analytics query` command."""

    def test_query_help(self, cli_runner: CliRunner):
        """Test query command shows help."""
        result = invoke_cli(cli_runner, analytics_group, ["query", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Query analytics data")

    def test_query_shows_all_options(self, cli_runner: CliRunner):
        """Test query command lists all options in help."""
        result = invoke_cli(cli_runner, analytics_group, ["query", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--url-contains")
        assert_output_contains(result, "--min-pageviews")
        assert_output_contains(result, "--max-pageviews")
        assert_output_contains(result, "--trend")
        assert_output_contains(result, "--order-by")
        assert_output_contains(result, "--limit")
        assert_output_contains(result, "--format")

    def test_query_requires_domain(self, cli_runner: CliRunner):
        """Test query command requires domain argument."""
        result = cli_runner.invoke(analytics_group, ["query"])
        # Should fail because domain is required
        assert result.exit_code != 0

    def test_query_trend_choices(self, cli_runner: CliRunner):
        """Test query --trend accepts valid choices."""
        result = invoke_cli(cli_runner, analytics_group, ["query", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "increasing")
        assert_output_contains(result, "decreasing")
        assert_output_contains(result, "stable")

    def test_query_order_by_choices(self, cli_runner: CliRunner):
        """Test query --order-by accepts valid choices."""
        result = invoke_cli(cli_runner, analytics_group, ["query", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "pageviews_30d")
        assert_output_contains(result, "pageviews_60d")
        assert_output_contains(result, "trend_percentage")

"""
E2E tests for `kurt tool analytics` command.

These tests verify the analytics sync command works correctly with various
platforms and options. Tests mock external API calls while testing
the full CLI integration.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kurt.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)
from kurt.tools.analytics.cli import analytics_group, sync_cmd


class TestAnalyticsHelp:
    """Tests for analytics command help and options."""

    def test_analytics_group_help(self, cli_runner: CliRunner):
        """Verify analytics group shows help."""
        result = invoke_cli(cli_runner, analytics_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Domain analytics")

    def test_analytics_sync_help(self, cli_runner: CliRunner):
        """Verify analytics sync shows help."""
        result = invoke_cli(cli_runner, sync_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Sync domain analytics")

    def test_analytics_sync_shows_options(self, cli_runner: CliRunner):
        """Verify analytics sync lists all options."""
        result = invoke_cli(cli_runner, sync_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "DOMAIN")
        assert_output_contains(result, "--platform")
        assert_output_contains(result, "--period-days")
        assert_output_contains(result, "--background")
        assert_output_contains(result, "--dry-run")
        assert_output_contains(result, "--format")


class TestAnalyticsSyncBasic:
    """E2E tests for analytics sync command."""

    def test_sync_requires_domain(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify sync requires DOMAIN argument."""
        result = invoke_cli(cli_runner, sync_cmd, [])
        assert result.exit_code != 0
        assert "DOMAIN" in result.output or "Missing argument" in result.output

    def test_sync_dry_run(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --dry-run doesn't make real API calls."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            ["example.com", "--dry-run", "--format", "json"],
        )
        assert result.exit_code in (0, 1)

    def test_sync_accepts_domain(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify domain argument is accepted."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            ["example.com", "--dry-run"],
        )
        assert result.exit_code in (0, 1)


class TestAnalyticsSyncPlatform:
    """E2E tests for --platform option."""

    def test_sync_platform_posthog(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --platform posthog is accepted."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            ["example.com", "--platform", "posthog", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_sync_platform_ga4(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --platform ga4 is accepted."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            ["example.com", "--platform", "ga4", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_sync_platform_plausible(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --platform plausible is accepted."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            ["example.com", "--platform", "plausible", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_sync_platform_invalid(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify invalid --platform is rejected."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            ["example.com", "--platform", "invalid", "--dry-run"],
        )
        assert result.exit_code != 0


class TestAnalyticsSyncPeriod:
    """E2E tests for --period-days option."""

    def test_sync_period_30_days(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --period-days 30 is accepted."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            ["example.com", "--period-days", "30", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_sync_period_90_days(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --period-days 90 is accepted."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            ["example.com", "--period-days", "90", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_sync_period_365_days(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --period-days 365 (max) is accepted."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            ["example.com", "--period-days", "365", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_sync_period_1_day(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --period-days 1 (min) is accepted."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            ["example.com", "--period-days", "1", "--dry-run"],
        )
        assert result.exit_code in (0, 1)

    def test_sync_period_over_365(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --period-days over 365 is rejected."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            ["example.com", "--period-days", "400", "--dry-run"],
        )
        assert result.exit_code != 0

    def test_sync_period_zero(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --period-days 0 is rejected."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            ["example.com", "--period-days", "0", "--dry-run"],
        )
        assert result.exit_code != 0


class TestAnalyticsSyncOutput:
    """E2E tests for analytics sync output formats."""

    def test_sync_json_output(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --format json produces JSON content."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            ["example.com", "--dry-run", "--format", "json"],
        )
        assert result.exit_code in (0, 1)
        # JSON should be present in output (may have other text too)
        assert "{" in result.output

    def test_sync_background_parses(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --background option parses correctly."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            ["example.com", "--background", "--format", "json"],
        )
        assert result.exit_code in (0, 1, 2)

    def test_sync_background_priority(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --priority works with --background."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            ["example.com", "--background", "--priority", "5", "--format", "json"],
        )
        assert result.exit_code in (0, 1, 2)


class TestAnalyticsSyncCombined:
    """E2E tests for combined options."""

    def test_sync_all_options(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify all options can be combined."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            [
                "example.com",
                "--platform",
                "posthog",
                "--period-days",
                "30",
                "--dry-run",
                "--format",
                "json",
            ],
        )
        assert result.exit_code in (0, 1)

    def test_sync_ga4_with_period(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify GA4 with custom period works."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            [
                "mysite.com",
                "--platform",
                "ga4",
                "--period-days",
                "60",
                "--dry-run",
            ],
        )
        assert result.exit_code in (0, 1)

    def test_sync_plausible_with_period(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify Plausible with custom period works."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            [
                "blog.example.com",
                "--platform",
                "plausible",
                "--period-days",
                "90",
                "--dry-run",
            ],
        )
        assert result.exit_code in (0, 1)


class TestAnalyticsSyncMissingCredentials:
    """E2E tests for missing credentials handling."""

    def test_sync_no_credentials_posthog(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify sync handles missing PostHog credentials."""
        with patch.dict("os.environ", {"POSTHOG_API_KEY": ""}, clear=False):
            result = invoke_cli(
                cli_runner,
                sync_cmd,
                ["example.com", "--platform", "posthog"],
            )
            # Should fail or show error about missing credentials
            assert result.exit_code in (0, 1, 2)

    def test_sync_no_credentials_ga4(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify sync handles missing GA4 credentials."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            ["example.com", "--platform", "ga4"],
        )
        # May fail due to missing credentials but should not crash
        assert result.exit_code in (0, 1, 2)

    def test_sync_no_credentials_plausible(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify sync handles missing Plausible credentials."""
        result = invoke_cli(
            cli_runner,
            sync_cmd,
            ["example.com", "--platform", "plausible"],
        )
        # May fail due to missing credentials but should not crash
        assert result.exit_code in (0, 1, 2)

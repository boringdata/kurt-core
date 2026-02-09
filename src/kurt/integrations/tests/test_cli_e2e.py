"""
E2E tests for `kurt connect` command (integrations group).

These tests verify the integrations CLI commands work correctly.
Tests verify the command structure and options.
"""

from __future__ import annotations

from click.testing import CliRunner

from kurt.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)
from kurt.integrations.cli import integrations_group


class TestIntegrationsGroupHelp:
    """Tests for integrations command group help."""

    def test_integrations_group_help(self, cli_runner: CliRunner):
        """Verify integrations group shows help."""
        result = invoke_cli(cli_runner, integrations_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "External service integrations")

    def test_integrations_lists_subgroups(self, cli_runner: CliRunner):
        """Verify integrations group lists all subgroups."""
        result = invoke_cli(cli_runner, integrations_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "cms")
        assert_output_contains(result, "analytics")
        assert_output_contains(result, "research")


class TestCmsSubgroup:
    """E2E tests for cms subgroup under integrations."""

    def test_cms_help(self, cli_runner: CliRunner):
        """Verify cms subgroup shows help."""
        result = invoke_cli(cli_runner, integrations_group, ["cms", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "CMS")

    def test_cms_lists_commands(self, cli_runner: CliRunner):
        """Verify cms lists its commands."""
        result = invoke_cli(cli_runner, integrations_group, ["cms", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "onboard")
        assert_output_contains(result, "status")
        assert_output_contains(result, "types")


class TestAnalyticsSubgroup:
    """E2E tests for analytics subgroup under integrations."""

    def test_analytics_help(self, cli_runner: CliRunner):
        """Verify analytics subgroup shows help."""
        result = invoke_cli(cli_runner, integrations_group, ["analytics", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "analytics")

    def test_analytics_lists_commands(self, cli_runner: CliRunner):
        """Verify analytics lists its commands."""
        result = invoke_cli(cli_runner, integrations_group, ["analytics", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "onboard")
        assert_output_contains(result, "list")
        assert_output_contains(result, "query")


class TestResearchSubgroup:
    """E2E tests for research subgroup under integrations."""

    def test_research_help(self, cli_runner: CliRunner):
        """Verify research subgroup shows help."""
        result = invoke_cli(cli_runner, integrations_group, ["research", "--help"])
        assert_cli_success(result)
        # Should show research-related content
        assert "research" in result.output.lower()


class TestIntegrationsFromMainCli:
    """E2E tests for integrations accessed via main CLI."""

    def test_connect_alias_works(self, cli_runner: CliRunner):
        """Verify 'connect' alias is registered in main CLI."""
        from kurt.cli.main import main

        result = cli_runner.invoke(main, ["connect", "--help"], catch_exceptions=False)
        assert_cli_success(result)
        assert_output_contains(result, "cms")
        assert_output_contains(result, "analytics")

    def test_connect_cms_via_main(self, cli_runner: CliRunner):
        """Verify cms is accessible via connect."""
        from kurt.cli.main import main

        result = cli_runner.invoke(
            main, ["connect", "cms", "--help"], catch_exceptions=False
        )
        assert_cli_success(result)
        assert_output_contains(result, "CMS")

    def test_connect_analytics_via_main(self, cli_runner: CliRunner):
        """Verify analytics is accessible via connect."""
        from kurt.cli.main import main

        result = cli_runner.invoke(
            main, ["connect", "analytics", "--help"], catch_exceptions=False
        )
        assert_cli_success(result)
        # Should show analytics help


class TestCmsOnboard:
    """E2E tests for cms onboard command options."""

    def test_cms_onboard_platform_options(self, cli_runner: CliRunner):
        """Verify cms onboard shows platform options."""
        result = invoke_cli(
            cli_runner, integrations_group, ["cms", "onboard", "--help"]
        )
        assert_cli_success(result)
        assert_output_contains(result, "--platform")
        # Platform choices should be shown
        assert "sanity" in result.output.lower()

    def test_cms_onboard_instance_option(self, cli_runner: CliRunner):
        """Verify cms onboard has instance option."""
        result = invoke_cli(
            cli_runner, integrations_group, ["cms", "onboard", "--help"]
        )
        assert_cli_success(result)
        assert_output_contains(result, "--instance")


class TestAnalyticsOnboard:
    """E2E tests for analytics onboard command options."""

    def test_analytics_onboard_platform_options(self, cli_runner: CliRunner):
        """Verify analytics onboard shows platform options."""
        result = invoke_cli(
            cli_runner, integrations_group, ["analytics", "onboard", "--help"]
        )
        assert_cli_success(result)
        assert_output_contains(result, "--platform")

    def test_analytics_onboard_requires_domain(self, cli_runner: CliRunner):
        """Verify analytics onboard requires domain argument."""
        result = cli_runner.invoke(
            integrations_group, ["analytics", "onboard"]
        )
        assert result.exit_code != 0


class TestAnalyticsQuery:
    """E2E tests for analytics query command options."""

    def test_analytics_query_filter_options(self, cli_runner: CliRunner):
        """Verify analytics query has filter options."""
        result = invoke_cli(
            cli_runner, integrations_group, ["analytics", "query", "--help"]
        )
        assert_cli_success(result)
        assert_output_contains(result, "--url-contains")
        assert_output_contains(result, "--min-pageviews")
        assert_output_contains(result, "--limit")

    def test_analytics_query_format_option(self, cli_runner: CliRunner):
        """Verify analytics query has format option."""
        result = invoke_cli(
            cli_runner, integrations_group, ["analytics", "query", "--help"]
        )
        assert_cli_success(result)
        assert_output_contains(result, "--format")

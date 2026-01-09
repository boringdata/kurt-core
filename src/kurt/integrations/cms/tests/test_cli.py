"""Tests for CMS integration CLI commands."""

from __future__ import annotations

from click.testing import CliRunner

from kurt.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)
from kurt.integrations.cms.cli import cms_group


class TestCmsGroup:
    """Tests for the cms command group."""

    def test_cms_group_help(self, cli_runner: CliRunner):
        """Test cms group shows help."""
        result = invoke_cli(cli_runner, cms_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "CMS integration commands")

    def test_cms_list_commands(self, cli_runner: CliRunner):
        """Test cms group lists all commands."""
        result = invoke_cli(cli_runner, cms_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "onboard")
        assert_output_contains(result, "status")
        assert_output_contains(result, "types")
        assert_output_contains(result, "search")
        assert_output_contains(result, "fetch")
        assert_output_contains(result, "publish")


class TestOnboardCommand:
    """Tests for `cms onboard` command."""

    def test_onboard_help(self, cli_runner: CliRunner):
        """Test onboard command shows help."""
        result = invoke_cli(cli_runner, cms_group, ["onboard", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Configure CMS credentials")

    def test_onboard_shows_all_options(self, cli_runner: CliRunner):
        """Test onboard command lists all options in help."""
        result = invoke_cli(cli_runner, cms_group, ["onboard", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--platform")
        assert_output_contains(result, "--instance")
        assert_output_contains(result, "--project-id")
        assert_output_contains(result, "--dataset")
        assert_output_contains(result, "--token")
        assert_output_contains(result, "--base-url")

    def test_onboard_platform_default(self, cli_runner: CliRunner):
        """Test onboard default platform is sanity."""
        result = invoke_cli(cli_runner, cms_group, ["onboard", "--help"])
        assert_cli_success(result)
        # Default shown in help
        assert "sanity" in result.output.lower()


class TestStatusCommand:
    """Tests for `cms status` command."""

    def test_status_help(self, cli_runner: CliRunner):
        """Test status command shows help."""
        result = invoke_cli(cli_runner, cms_group, ["status", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Show configured CMS integrations")

    def test_status_shows_options(self, cli_runner: CliRunner):
        """Test status command lists options in help."""
        result = invoke_cli(cli_runner, cms_group, ["status", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--check-health")

    def test_status_no_config(self, cli_runner: CliRunner, tmp_database):
        """Test status when no CMS configured."""
        result = invoke_cli(cli_runner, cms_group, ["status"])
        assert_cli_success(result)
        assert_output_contains(result, "No CMS integrations configured")


class TestTypesCommand:
    """Tests for `cms types` command."""

    def test_types_help(self, cli_runner: CliRunner):
        """Test types command shows help."""
        result = invoke_cli(cli_runner, cms_group, ["types", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "List available content types")

    def test_types_shows_options(self, cli_runner: CliRunner):
        """Test types command lists options in help."""
        result = invoke_cli(cli_runner, cms_group, ["types", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--platform")
        assert_output_contains(result, "--instance")


class TestSearchCommand:
    """Tests for `cms search` command."""

    def test_search_help(self, cli_runner: CliRunner):
        """Test search command shows help."""
        result = invoke_cli(cli_runner, cms_group, ["search", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Search CMS content")

    def test_search_shows_all_options(self, cli_runner: CliRunner):
        """Test search command lists all options in help."""
        result = invoke_cli(cli_runner, cms_group, ["search", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--platform")
        assert_output_contains(result, "--instance")
        assert_output_contains(result, "--query")
        assert_output_contains(result, "--content-type")
        assert_output_contains(result, "--limit")
        assert_output_contains(result, "--format")


class TestFetchCommand:
    """Tests for `cms fetch` command."""

    def test_fetch_help(self, cli_runner: CliRunner):
        """Test fetch command shows help."""
        result = invoke_cli(cli_runner, cms_group, ["fetch", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Fetch document content")

    def test_fetch_shows_all_options(self, cli_runner: CliRunner):
        """Test fetch command lists all options in help."""
        result = invoke_cli(cli_runner, cms_group, ["fetch", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--platform")
        assert_output_contains(result, "--instance")
        assert_output_contains(result, "--id")
        assert_output_contains(result, "--output-dir")
        assert_output_contains(result, "--output-format")

    def test_fetch_requires_id(self, cli_runner: CliRunner):
        """Test fetch command requires --id option."""
        result = cli_runner.invoke(cms_group, ["fetch"])
        # Should fail because --id is required
        assert result.exit_code != 0


class TestPublishCommand:
    """Tests for `cms publish` command."""

    def test_publish_help(self, cli_runner: CliRunner):
        """Test publish command shows help."""
        result = invoke_cli(cli_runner, cms_group, ["publish", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Publish markdown file")

    def test_publish_shows_all_options(self, cli_runner: CliRunner):
        """Test publish command lists all options in help."""
        result = invoke_cli(cli_runner, cms_group, ["publish", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--platform")
        assert_output_contains(result, "--instance")
        assert_output_contains(result, "--file")
        assert_output_contains(result, "--id")
        assert_output_contains(result, "--content-type")

    def test_publish_requires_file(self, cli_runner: CliRunner):
        """Test publish command requires --file option."""
        result = cli_runner.invoke(cms_group, ["publish"])
        # Should fail because --file is required
        assert result.exit_code != 0

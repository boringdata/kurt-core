"""Tests for map workflow CLI commands."""

from __future__ import annotations

from click.testing import CliRunner

from kurt.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)
from kurt.tools.map.cli import map_cmd


class TestMapCommand:
    """Tests for `content map` command."""

    def test_map_help(self, cli_runner: CliRunner):
        """Test map command shows help."""
        result = invoke_cli(cli_runner, map_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Discover content sources")

    def test_map_shows_all_options(self, cli_runner: CliRunner):
        """Test map command lists all options in help."""
        result = invoke_cli(cli_runner, map_cmd, ["--help"])
        assert_cli_success(result)
        # Source options
        assert_output_contains(result, "--url")
        assert_output_contains(result, "--folder")
        assert_output_contains(result, "--cms")
        # Discovery options
        assert_output_contains(result, "--method")
        assert_output_contains(result, "--sitemap-path")
        assert_output_contains(result, "--max-depth")
        # Filter options
        assert_output_contains(result, "--include")
        assert_output_contains(result, "--exclude")
        assert_output_contains(result, "--limit")
        # Background options
        assert_output_contains(result, "--background")
        assert_output_contains(result, "--priority")
        # Other options
        assert_output_contains(result, "--dry-run")
        assert_output_contains(result, "--format")

    def test_map_no_source_error(self, cli_runner: CliRunner, tmp_database):
        """Test map shows error when no source specified."""
        result = invoke_cli(cli_runner, map_cmd, [])
        assert_cli_success(result)  # Returns 0 but shows error message
        assert_output_contains(result, "No source specified")

    def test_map_with_url_argument(self, cli_runner: CliRunner, tmp_database):
        """Test map with URL as positional argument."""
        # This will fail network request but should parse correctly
        result = cli_runner.invoke(map_cmd, ["https://example.com", "--dry-run"])
        # Just checking it parses, may fail on network
        assert "--help" not in result.output

    def test_map_with_url_option(self, cli_runner: CliRunner, tmp_database):
        """Test map --url option."""
        result = cli_runner.invoke(map_cmd, ["--url", "https://example.com", "--dry-run"])
        assert "--help" not in result.output

    def test_map_with_folder_option(self, cli_runner: CliRunner, tmp_database):
        """Test map --folder option parses correctly."""
        # Just verify the option parses - execution may fail due to workflow internals
        result = cli_runner.invoke(map_cmd, ["--folder", ".", "--dry-run"])
        assert "--help" not in result.output

    def test_map_with_cms_option(self, cli_runner: CliRunner, tmp_database):
        """Test map --cms option."""
        result = cli_runner.invoke(
            map_cmd,
            ["--cms", "sanity:production", "--dry-run"],
        )
        # May fail because CMS not configured, but should parse
        assert "--help" not in result.output

    def test_map_method_options_in_help(self, cli_runner: CliRunner, tmp_database):
        """Test map --method options are documented in help."""
        result = invoke_cli(cli_runner, map_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "sitemap")
        assert_output_contains(result, "crawl")
        assert_output_contains(result, "folder")
        assert_output_contains(result, "cms")

    def test_map_method_crawl_forces_crawler(self, cli_runner: CliRunner, tmp_database):
        """Test --method crawl skips sitemap and uses crawler directly."""
        from unittest.mock import patch

        async def mock_crawl(*args, **kwargs):
            return [{"url": "https://example.com/page1", "source_type": "page", "depth": 0}]

        # Mock discover_from_crawl in map_tool.py (where it's actually called)
        with patch("kurt.tools.map_tool.discover_from_crawl", new=mock_crawl):
            # Also mock discover_from_sitemap to verify it's NOT called
            with patch("kurt.tools.map_tool.discover_from_sitemap") as mock_sitemap:
                mock_sitemap.side_effect = Exception("sitemap should not be tried")

                result = cli_runner.invoke(
                    map_cmd,
                    ["https://example.com", "--method", "crawl", "--dry-run", "--format", "json"],
                )

                assert result.exit_code == 0, f"Failed: {result.output}"
                # Sitemap should not be called when method=crawl
                assert not mock_sitemap.called, "Sitemap should NOT be called when method=crawl"

    def test_map_method_sitemap_does_not_fallback(self, cli_runner: CliRunner, tmp_database):
        """Test --method sitemap raises error instead of falling back to crawl."""
        from unittest.mock import MagicMock, patch

        with patch("kurt.tools.map.url.httpx.get") as mock_httpx:
            # Sitemap returns 404
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.text = ""
            mock_httpx.return_value = mock_response

            with patch("kurt.tools.map.url.focused_crawler") as mock_crawler:
                result = cli_runner.invoke(
                    map_cmd,
                    [
                        "https://example.com",
                        "--method",
                        "sitemap",
                        "--max-depth",
                        "2",  # Would normally trigger fallback
                        "--dry-run",
                        "--format",
                        "json",
                    ],
                )

                # Should fail because sitemap not found and no fallback
                assert "No sitemap found" in result.output or result.exit_code != 0
                assert not mock_crawler.called, "Crawler should NOT be called when method=sitemap"

    def test_map_with_sitemap_path(self, cli_runner: CliRunner, tmp_database):
        """Test map --sitemap-path option."""
        result = cli_runner.invoke(
            map_cmd,
            ["--url", "https://example.com", "--sitemap-path", "/custom-sitemap.xml", "--dry-run"],
        )
        assert "--help" not in result.output

    def test_map_with_max_depth(self, cli_runner: CliRunner, tmp_database):
        """Test map --max-depth option."""
        result = cli_runner.invoke(map_cmd, ["--folder", ".", "--max-depth", "2", "--dry-run"])
        assert "--help" not in result.output

    def test_map_with_include_exclude(self, cli_runner: CliRunner, tmp_database):
        """Test map --include and --exclude options parse correctly."""
        # Just verify options parse - execution may fail due to workflow internals
        result = cli_runner.invoke(
            map_cmd,
            ["--folder", ".", "--include", "*.md", "--exclude", "*test*", "--dry-run"],
        )
        assert "--help" not in result.output

    def test_map_with_limit(self, cli_runner: CliRunner, tmp_database):
        """Test map --limit option parses correctly."""
        result = cli_runner.invoke(map_cmd, ["--folder", ".", "--limit", "100", "--dry-run"])
        assert "--help" not in result.output

    def test_map_with_dry_run(self, cli_runner: CliRunner, tmp_database):
        """Test map --dry-run option parses correctly."""
        result = cli_runner.invoke(map_cmd, ["--folder", ".", "--dry-run"])
        assert "--help" not in result.output

    def test_map_with_json_format(self, cli_runner: CliRunner, tmp_database):
        """Test map --format json option parses correctly."""
        result = cli_runner.invoke(map_cmd, ["--folder", ".", "--dry-run", "--format", "json"])
        assert "--help" not in result.output

    def test_map_combined_options(self, cli_runner: CliRunner, tmp_database):
        """Test map with multiple options combined parses correctly."""
        result = cli_runner.invoke(
            map_cmd,
            [
                "--folder",
                ".",
                "--method",
                "folder",
                "--include",
                "*.py",
                "--limit",
                "50",
                "--dry-run",
                "--format",
                "json",
            ],
        )
        assert "--help" not in result.output

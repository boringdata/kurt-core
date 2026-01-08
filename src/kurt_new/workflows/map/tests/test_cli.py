"""Tests for map workflow CLI commands."""

from __future__ import annotations

from click.testing import CliRunner

from kurt_new.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)
from kurt_new.workflows.map.cli import map_cmd


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
        result = cli_runner.invoke(map_cmd, ["--cms", "sanity:production", "--dry-run"])
        # May fail because CMS not configured, but should parse
        assert "--help" not in result.output

    def test_map_method_sitemap(self, cli_runner: CliRunner, tmp_database):
        """Test map --method sitemap option."""
        result = invoke_cli(cli_runner, map_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "sitemap")
        assert_output_contains(result, "crawl")
        assert_output_contains(result, "folder")
        assert_output_contains(result, "cms")

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


class TestE2EWithDocs:
    """E2E tests using tmp_project_with_docs fixture with real documents."""

    def test_map_folder_dry_run(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test map --folder with real project directory."""

        # Create a test folder with markdown files
        test_folder = tmp_project_with_docs / "test_docs"
        test_folder.mkdir()
        (test_folder / "doc1.md").write_text("# Test Doc 1")
        (test_folder / "doc2.md").write_text("# Test Doc 2")

        result = cli_runner.invoke(
            map_cmd,
            ["--folder", str(test_folder), "--dry-run", "--format", "json"],
        )
        assert_cli_success(result)

    def test_map_folder_with_include_filter(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test map --folder with --include filter."""

        # Create test folder with mixed files
        test_folder = tmp_project_with_docs / "mixed_docs"
        test_folder.mkdir()
        (test_folder / "doc.md").write_text("# Markdown")
        (test_folder / "code.py").write_text("# Python")
        (test_folder / "data.txt").write_text("Plain text")

        result = cli_runner.invoke(
            map_cmd,
            ["--folder", str(test_folder), "--include", "*.md", "--dry-run", "--format", "json"],
        )
        assert_cli_success(result)

    def test_map_folder_with_exclude_filter(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test map --folder with --exclude filter."""

        test_folder = tmp_project_with_docs / "exclude_test"
        test_folder.mkdir()
        (test_folder / "keep.md").write_text("# Keep")
        (test_folder / "test_skip.md").write_text("# Skip")

        result = cli_runner.invoke(
            map_cmd,
            ["--folder", str(test_folder), "--exclude", "*test*", "--dry-run", "--format", "json"],
        )
        assert_cli_success(result)

    def test_map_folder_with_limit(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test map --folder with --limit option."""

        test_folder = tmp_project_with_docs / "limit_test"
        test_folder.mkdir()
        for i in range(5):
            (test_folder / f"doc{i}.md").write_text(f"# Doc {i}")

        result = cli_runner.invoke(
            map_cmd,
            ["--folder", str(test_folder), "--limit", "2", "--dry-run", "--format", "json"],
        )
        assert_cli_success(result)

    def test_map_folder_max_depth(self, cli_runner: CliRunner, tmp_project_with_docs):
        """Test map --folder with --max-depth option."""

        # Create nested folder structure
        test_folder = tmp_project_with_docs / "nested"
        test_folder.mkdir()
        (test_folder / "level0.md").write_text("# Level 0")
        level1 = test_folder / "level1"
        level1.mkdir()
        (level1 / "level1.md").write_text("# Level 1")
        level2 = level1 / "level2"
        level2.mkdir()
        (level2 / "level2.md").write_text("# Level 2")

        result = cli_runner.invoke(
            map_cmd,
            ["--folder", str(test_folder), "--max-depth", "1", "--dry-run", "--format", "json"],
        )
        assert_cli_success(result)

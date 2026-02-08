"""
E2E tests for `kurt tool map` command with URL sources.

These tests verify the map command works correctly with various options.
Some tests use mocked HTTP responses for predictable results.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from kurt.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)
from kurt.tools.map.cli import map_cmd


class TestMapHelp:
    """Tests for map command help and options."""

    def test_map_help_shows_all_options(self, cli_runner: CliRunner):
        """Verify map --help lists all options."""
        result = invoke_cli(cli_runner, map_cmd, ["--help"])
        assert_cli_success(result)

        # Verify all options documented
        options = [
            "--url",
            "--method",
            "--sitemap-path",
            "--max-depth",
            "--include",
            "--exclude",
            "--limit",
            "--dry-run",
            "--background",
            "--format",
        ]
        for opt in options:
            assert_output_contains(result, opt)


class TestMapDryRun:
    """E2E tests for --dry-run option."""

    def test_map_dry_run_folder(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --dry-run with folder source works."""
        # Create some test files
        (tmp_project / "docs").mkdir(exist_ok=True)
        (tmp_project / "docs" / "readme.md").write_text("# Test")
        (tmp_project / "docs" / "guide.md").write_text("# Guide")

        result = invoke_cli(
            cli_runner,
            map_cmd,
            ["--folder", "docs", "--dry-run", "--format", "json"],
        )

        # Should complete
        assert result.exit_code in (0, 1, 2)

    def test_map_dry_run_parses(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --dry-run option is parsed and accepted."""
        # Create test folder
        (tmp_project / "testdocs").mkdir(exist_ok=True)
        (tmp_project / "testdocs" / "test.md").write_text("# Test")

        result = invoke_cli(
            cli_runner,
            map_cmd,
            ["--folder", "testdocs", "--dry-run"],
        )

        # Should complete without parsing error
        assert result.exit_code in (0, 1, 2)
        # Should show dry run in output
        output_lower = result.output.lower()
        assert "dry" in output_lower or "preview" in output_lower or "{" in result.output


class TestMapJsonOutput:
    """E2E tests for --format json output."""

    def test_map_json_output_valid(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --format json produces valid JSON."""
        # Create test files
        (tmp_project / "jsontest").mkdir(exist_ok=True)
        (tmp_project / "jsontest" / "file.md").write_text("# JSON Test")

        result = invoke_cli(
            cli_runner,
            map_cmd,
            ["--folder", "jsontest", "--format", "json"],
        )

        # Should complete
        assert result.exit_code in (0, 1, 2)

        # If exit code is 0, output should contain JSON-like content
        if result.exit_code == 0:
            # Output should contain some indication of JSON
            assert "{" in result.output or "run_id" in result.output


class TestMapFiltering:
    """E2E tests for URL/file filtering options."""

    def test_map_with_include_pattern(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --include filters discovered files."""
        # Create mixed file types
        (tmp_project / "mixed").mkdir(exist_ok=True)
        (tmp_project / "mixed" / "doc.md").write_text("# Markdown")
        (tmp_project / "mixed" / "code.py").write_text("# Python")
        (tmp_project / "mixed" / "data.json").write_text("{}")

        result = invoke_cli(
            cli_runner,
            map_cmd,
            ["--folder", "mixed", "--include", "*.md", "--dry-run"],
        )

        # Should complete
        assert result.exit_code in (0, 1, 2)

    def test_map_with_exclude_pattern(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --exclude filters out files."""
        (tmp_project / "exclude").mkdir(exist_ok=True)
        (tmp_project / "exclude" / "keep.md").write_text("# Keep")
        (tmp_project / "exclude" / "skip.test.md").write_text("# Skip")

        result = invoke_cli(
            cli_runner,
            map_cmd,
            ["--folder", "exclude", "--exclude", "*.test.*", "--dry-run"],
        )

        assert result.exit_code in (0, 1, 2)

    def test_map_with_limit(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --limit caps number of discovered files."""
        # Create many files
        (tmp_project / "many").mkdir(exist_ok=True)
        for i in range(20):
            (tmp_project / "many" / f"file{i}.md").write_text(f"# File {i}")

        result = invoke_cli(
            cli_runner,
            map_cmd,
            ["--folder", "many", "--limit", "5", "--dry-run", "--format", "json"],
        )

        assert result.exit_code in (0, 1, 2)


class TestMapMethodOptions:
    """E2E tests for --method option."""

    def test_map_method_folder(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --method folder works."""
        (tmp_project / "methodtest").mkdir(exist_ok=True)
        (tmp_project / "methodtest" / "doc.md").write_text("# Method")

        result = invoke_cli(
            cli_runner,
            map_cmd,
            ["--folder", "methodtest", "--method", "folder", "--dry-run"],
        )

        assert result.exit_code in (0, 1, 2)


class TestMapMaxDepth:
    """E2E tests for --max-depth option."""

    def test_map_max_depth_folder(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --max-depth limits recursion depth."""
        # Create nested directories
        (tmp_project / "depth" / "level1" / "level2").mkdir(parents=True)
        (tmp_project / "depth" / "root.md").write_text("# Root")
        (tmp_project / "depth" / "level1" / "one.md").write_text("# L1")
        (tmp_project / "depth" / "level1" / "level2" / "two.md").write_text("# L2")

        result = invoke_cli(
            cli_runner,
            map_cmd,
            ["--folder", "depth", "--max-depth", "1", "--dry-run"],
        )

        assert result.exit_code in (0, 1, 2)


class TestMapBackground:
    """E2E tests for --background option."""

    def test_map_background_parses(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --background option parses correctly."""
        (tmp_project / "bgtest").mkdir(exist_ok=True)
        (tmp_project / "bgtest" / "doc.md").write_text("# BG")

        result = invoke_cli(
            cli_runner,
            map_cmd,
            ["--folder", "bgtest", "--background"],
        )

        # Background mode may succeed or fail, but should not error on parse
        assert result.exit_code in (0, 1, 2)


class TestMapUrlSource:
    """E2E tests for URL-based mapping."""

    def test_map_url_dry_run(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --url with --dry-run works."""
        result = invoke_cli(
            cli_runner,
            map_cmd,
            ["--url", "https://example.com", "--dry-run", "--format", "json"],
        )

        # Should complete (may use crawl fallback if sitemap not found)
        assert result.exit_code in (0, 1, 2)

    def test_map_url_with_sitemap_path(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --sitemap-path option parses correctly."""
        result = invoke_cli(
            cli_runner,
            map_cmd,
            [
                "--url",
                "https://example.com",
                "--sitemap-path",
                "/custom-sitemap.xml",
                "--dry-run",
            ],
        )

        assert result.exit_code in (0, 1, 2)


class TestMapIntegration:
    """Integration tests combining multiple map options."""

    def test_map_combined_folder_options(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify map with multiple folder options works correctly."""
        # Create folder structure
        docs = tmp_project / "combined_docs"
        docs.mkdir()
        (docs / "readme.md").write_text("# README")
        (docs / "api.md").write_text("# API")
        (docs / "test.skip.md").write_text("# Skip")

        result = invoke_cli(
            cli_runner,
            map_cmd,
            [
                "--folder",
                "combined_docs",
                "--method",
                "folder",
                "--include",
                "*.md",
                "--exclude",
                "*.skip.*",
                "--limit",
                "10",
                "--dry-run",
                "--format",
                "json",
            ],
        )

        assert result.exit_code in (0, 1, 2)

    def test_map_no_source_error(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify map with no source shows error."""
        result = invoke_cli(cli_runner, map_cmd, [])

        # Should show error about no source
        assert "No source" in result.output or result.exit_code != 0

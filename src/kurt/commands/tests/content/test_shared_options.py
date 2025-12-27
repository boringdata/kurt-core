"""Tests for shared CLI options consistency across commands."""

from kurt.cli import main


class TestSharedOptionsConsistency:
    """Test that shared options behave consistently across commands."""

    def test_include_option_consistent_across_commands(self, isolated_cli_runner):
        """Verify --include option exists and works same in index/fetch/list/stats."""
        runner, project_dir = isolated_cli_runner

        # Test index --help
        result = runner.invoke(main, ["content", "index", "--help"])
        assert "--include" in result.output
        assert "glob pattern" in result.output.lower()

        # Test fetch --help
        result = runner.invoke(main, ["content", "fetch", "--help"])
        assert "--include" in result.output
        assert "glob pattern" in result.output.lower()

        # Test list --help
        result = runner.invoke(main, ["content", "list", "--help"])
        assert "--include" in result.output
        assert "glob pattern" in result.output.lower() or "pattern" in result.output.lower()

        # Test stats --help
        result = runner.invoke(main, ["content", "stats", "--help"])
        assert "--include" in result.output
        assert "glob pattern" in result.output.lower() or "pattern" in result.output.lower()

    def test_with_status_option_consistent(self, isolated_cli_runner):
        """Verify --with-status accepts same values in all commands."""
        runner, project_dir = isolated_cli_runner

        # Test index --help
        result = runner.invoke(main, ["content", "index", "--help"])
        assert "--with-status" in result.output
        assert "NOT_FETCHED" in result.output or "FETCHED" in result.output

        # Test fetch --help
        result = runner.invoke(main, ["content", "fetch", "--help"])
        assert "--with-status" in result.output

        # Test list --help
        result = runner.invoke(main, ["content", "list", "--help"])
        assert "--with-status" in result.output

        # Test stats --help
        result = runner.invoke(main, ["content", "stats", "--help"])
        assert "--with-status" in result.output

    def test_limit_option_consistent(self, isolated_cli_runner):
        """Verify --limit exists across commands."""
        runner, project_dir = isolated_cli_runner

        # Test index --help
        result = runner.invoke(main, ["content", "index", "--help"])
        assert "--limit" in result.output

        # Test fetch --help
        result = runner.invoke(main, ["content", "fetch", "--help"])
        assert "--limit" in result.output

        # Test list --help
        result = runner.invoke(main, ["content", "list", "--help"])
        assert "--limit" in result.output

        # Test stats --help
        result = runner.invoke(main, ["content", "stats", "--help"])
        assert "--limit" in result.output

    def test_in_cluster_option_consistent(self, isolated_cli_runner):
        """Verify --in-cluster exists across commands."""
        runner, project_dir = isolated_cli_runner

        # Test index --help
        result = runner.invoke(main, ["content", "index", "--help"])
        assert "--in-cluster" in result.output

        # Test fetch --help
        result = runner.invoke(main, ["content", "fetch", "--help"])
        assert "--in-cluster" in result.output

        # Test list --help
        result = runner.invoke(main, ["content", "list", "--help"])
        assert "--in-cluster" in result.output

        # Test stats --help (newly added)
        result = runner.invoke(main, ["content", "stats", "--help"])
        assert "--in-cluster" in result.output

    def test_with_content_type_option_consistent(self, isolated_cli_runner):
        """Verify --with-content-type exists across commands."""
        runner, project_dir = isolated_cli_runner

        # Test index --help
        result = runner.invoke(main, ["content", "index", "--help"])
        assert "--with-content-type" in result.output

        # Test fetch --help
        result = runner.invoke(main, ["content", "fetch", "--help"])
        assert "--with-content-type" in result.output

        # Test list --help
        result = runner.invoke(main, ["content", "list", "--help"])
        assert "--with-content-type" in result.output

        # Test stats --help (newly added)
        result = runner.invoke(main, ["content", "stats", "--help"])
        assert "--with-content-type" in result.output


class TestSharedOptionsHelp:
    """Test that help text is consistent for shared options."""

    def test_include_help_mentions_glob(self, isolated_cli_runner):
        """Verify --include help text consistently mentions glob pattern."""
        runner, project_dir = isolated_cli_runner

        for cmd in ["index", "list", "stats"]:
            result = runner.invoke(main, ["content", cmd, "--help"])
            help_text = result.output.lower()
            # Should mention glob or pattern
            assert "glob" in help_text or "pattern" in help_text

    def test_ids_help_mentions_capabilities(self, isolated_cli_runner):
        """Verify --ids help mentions partial UUIDs, URLs, file paths."""
        runner, project_dir = isolated_cli_runner

        result = runner.invoke(main, ["content", "index", "--help"])
        help_text = result.output
        # New help text should mention multiple identifier types
        assert "comma-separated" in help_text.lower() or "ids" in help_text.lower()

    def test_with_status_shows_choices(self, isolated_cli_runner):
        """Verify --with-status shows available choices."""
        runner, project_dir = isolated_cli_runner

        result = runner.invoke(main, ["content", "index", "--help"])
        help_text = result.output
        # Should show the status choices
        assert "NOT_FETCHED" in help_text or "FETCHED" in help_text or "ERROR" in help_text

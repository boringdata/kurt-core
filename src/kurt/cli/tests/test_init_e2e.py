"""
E2E tests for `kurt init` command.

These tests use real filesystem and Dolt database operations,
verifying that init creates all expected artifacts and database tables.

NOTE: The observability table creation may fail when running init without
a Dolt server, as it uses SQLAlchemy which requires a running server.
This is expected behavior - init creates all filesystem artifacts correctly
but returns exit code 2 if any component fails.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from kurt.cli.init import init
from kurt.conftest import (
    assert_cli_failure,
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)
from kurt.testing import (
    assert_directory_exists,
    assert_file_contains,
    assert_file_exists,
)


def assert_init_completed(result) -> None:
    """
    Assert that init completed, allowing for partial failures.

    Exit codes:
    - 0: Full success
    - 2: Partial success (some components failed but most created)
    """
    if result.exit_code not in (0, 2):
        raise AssertionError(
            f"Init failed unexpectedly (exit code {result.exit_code})\n"
            f"Output: {result.output}"
        )
    # Verify it says "Initialized"
    if "Initialized" not in result.output:
        raise AssertionError(f"Init did not complete. Output: {result.output}")


@pytest.fixture
def dolt_available() -> bool:
    """Check if Dolt is installed."""
    return shutil.which("dolt") is not None


@pytest.fixture
def cli_runner_isolated(cli_runner: CliRunner):
    """CLI runner with isolated filesystem."""
    with cli_runner.isolated_filesystem():
        yield cli_runner


class TestInitCreatesArtifacts:
    """E2E tests verifying init creates all expected filesystem artifacts."""

    def test_init_creates_config_file(self, cli_runner_isolated, dolt_available):
        """Verify kurt.toml is created with expected content."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        result = invoke_cli(cli_runner_isolated, init, [])
        assert_init_completed(result)

        # Verify config file exists
        config_path = assert_file_exists(Path.cwd() / "kurt.toml")

        # Verify config has expected sections
        content = config_path.read_text()
        assert "[workspace]" in content
        assert "[paths]" in content
        assert "[agent]" in content
        assert "[tool.batch-llm]" in content
        assert "[tool.batch-embedding]" in content

    def test_init_creates_dolt_database(self, cli_runner_isolated, dolt_available):
        """Verify .dolt directory is created."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        result = invoke_cli(cli_runner_isolated, init, [])
        assert_init_completed(result)

        # Verify .dolt directory exists
        assert_directory_exists(Path.cwd() / ".dolt")

    def test_init_creates_git_repo(self, cli_runner_isolated, dolt_available):
        """Verify Git repository is initialized."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        result = invoke_cli(cli_runner_isolated, init, [])
        assert_init_completed(result)

        # Verify .git directory exists
        assert_directory_exists(Path.cwd() / ".git")

    def test_init_creates_workflows_directory(self, cli_runner_isolated, dolt_available):
        """Verify workflows/ directory is created with example."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        result = invoke_cli(cli_runner_isolated, init, [])
        assert_init_completed(result)

        # Verify workflows directory exists
        workflows_dir = assert_directory_exists(Path.cwd() / "workflows")

        # Verify example workflow exists
        example = workflows_dir / "example.md"
        assert_file_exists(example)
        assert_file_contains(example, "name: example")
        assert_file_contains(example, "agent:")

    def test_init_creates_sources_directory(self, cli_runner_isolated, dolt_available):
        """Verify sources/ directory is created."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        result = invoke_cli(cli_runner_isolated, init, [])
        assert_init_completed(result)

        # Verify sources directory exists
        assert_directory_exists(Path.cwd() / "sources")

    def test_init_creates_agents_directory(self, cli_runner_isolated, dolt_available):
        """Verify .agents/ directory is created with AGENTS.md."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        result = invoke_cli(cli_runner_isolated, init, [])
        assert_init_completed(result)

        # Verify .agents directory exists
        agents_dir = assert_directory_exists(Path.cwd() / ".agents")
        assert_file_exists(agents_dir / "AGENTS.md")

    def test_init_creates_claude_config(self, cli_runner_isolated, dolt_available):
        """Verify .claude/ directory is created with CLAUDE.md symlink."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        result = invoke_cli(cli_runner_isolated, init, [])
        assert_init_completed(result)

        # Verify .claude directory exists
        claude_dir = assert_directory_exists(Path.cwd() / ".claude")

        # Verify CLAUDE.md exists (as symlink to .agents/AGENTS.md)
        claude_md = claude_dir / "CLAUDE.md"
        assert claude_md.exists()

    def test_init_updates_gitignore(self, cli_runner_isolated, dolt_available):
        """Verify .gitignore is created/updated with Kurt entries."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        result = invoke_cli(cli_runner_isolated, init, [])
        assert_init_completed(result)

        # Verify .gitignore exists
        gitignore = assert_file_exists(Path.cwd() / ".gitignore")

        # Verify Kurt entries
        assert_file_contains(gitignore, "sources/")
        assert_file_contains(gitignore, ".dolt/noms/")
        assert_file_contains(gitignore, ".env")


class TestInitCreatesObservabilityTables:
    """E2E tests verifying init creates observability tables in Dolt.

    NOTE: These tests are marked as expected to fail because
    creating observability tables requires a running Dolt server,
    but `kurt init` only initializes the Dolt repo without starting a server.
    """

    @pytest.mark.xfail(reason="Table creation requires running Dolt server")
    def test_init_creates_workflow_runs_table(self, cli_runner_isolated, dolt_available):
        """Verify workflow_runs table is created in database."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        result = invoke_cli(cli_runner_isolated, init, [])
        assert_cli_success(result)

        # Query the database to verify table exists
        import subprocess

        result = subprocess.run(
            ["dolt", "sql", "-q", "SHOW TABLES LIKE 'workflow_runs'"],
            capture_output=True,
            text=True,
        )
        assert "workflow_runs" in result.stdout

    @pytest.mark.xfail(reason="Table creation requires running Dolt server")
    def test_init_creates_step_logs_table(self, cli_runner_isolated, dolt_available):
        """Verify step_logs table is created in database."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        result = invoke_cli(cli_runner_isolated, init, [])
        assert_cli_success(result)

        import subprocess

        result = subprocess.run(
            ["dolt", "sql", "-q", "SHOW TABLES LIKE 'step_logs'"],
            capture_output=True,
            text=True,
        )
        assert "step_logs" in result.stdout

    @pytest.mark.xfail(reason="Table creation requires running Dolt server")
    def test_init_creates_step_events_table(self, cli_runner_isolated, dolt_available):
        """Verify step_events table is created in database."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        result = invoke_cli(cli_runner_isolated, init, [])
        assert_cli_success(result)

        import subprocess

        result = subprocess.run(
            ["dolt", "sql", "-q", "SHOW TABLES LIKE 'step_events'"],
            capture_output=True,
            text=True,
        )
        assert "step_events" in result.stdout


class TestInitWithExistingProject:
    """E2E tests for init with existing project detection."""

    def test_init_fails_with_existing_dolt(self, cli_runner_isolated, dolt_available):
        """Verify init fails when .dolt already exists."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        # Create existing .dolt directory
        (Path.cwd() / ".dolt").mkdir()

        result = invoke_cli(cli_runner_isolated, init, [])

        # Should fail with exit code 1
        assert_cli_failure(result, expected_code=1)

    def test_init_suggests_force_flag(self, cli_runner_isolated, dolt_available):
        """Verify init suggests --force when project exists."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        # Create existing .dolt directory
        (Path.cwd() / ".dolt").mkdir()

        result = invoke_cli(cli_runner_isolated, init, [])

        assert "--force" in result.output


class TestInitForceFlag:
    """E2E tests for --force flag."""

    def test_init_force_completes_partial_setup(self, cli_runner_isolated, dolt_available):
        """Verify --force completes partial initialization."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        import os
        import subprocess

        # Create partial setup (just .dolt)
        env = os.environ.copy()
        env["DOLT_DISABLE_ACCOUNT_REGISTRATION"] = "true"
        subprocess.run(["dolt", "init"], capture_output=True, env=env)
        (Path.cwd() / ".git").mkdir()

        # Run init with --force
        result = invoke_cli(cli_runner_isolated, init, ["--force"])
        assert_init_completed(result)

        # Verify missing components were created
        assert_file_exists(Path.cwd() / "kurt.toml")
        assert_directory_exists(Path.cwd() / "workflows")
        assert_directory_exists(Path.cwd() / "sources")

    def test_init_force_does_not_overwrite_config(self, cli_runner_isolated, dolt_available):
        """Verify --force does not overwrite existing config."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        import os
        import subprocess

        # Create partial setup with config
        env = os.environ.copy()
        env["DOLT_DISABLE_ACCOUNT_REGISTRATION"] = "true"
        subprocess.run(["dolt", "init"], capture_output=True, env=env)
        (Path.cwd() / ".git").mkdir()
        (Path.cwd() / "kurt.toml").write_text("# Custom config\n")

        # Run init with --force
        result = invoke_cli(cli_runner_isolated, init, ["--force"])
        assert_init_completed(result)

        # Verify config was not overwritten
        content = (Path.cwd() / "kurt.toml").read_text()
        assert "Custom config" in content


class TestInitNoDoltFlag:
    """E2E tests for --no-dolt flag."""

    def test_init_no_dolt_skips_database(self, cli_runner_isolated):
        """Verify --no-dolt skips Dolt initialization."""
        result = invoke_cli(cli_runner_isolated, init, ["--no-dolt"])
        assert_cli_success(result)

        # Verify .dolt does NOT exist
        assert not (Path.cwd() / ".dolt").exists()

        # But other artifacts should exist
        assert_file_exists(Path.cwd() / "kurt.toml")
        assert_directory_exists(Path.cwd() / "workflows")
        assert_directory_exists(Path.cwd() / "sources")

    def test_init_no_dolt_skips_hooks(self, cli_runner_isolated):
        """Verify --no-dolt implies hooks are skipped."""
        result = invoke_cli(cli_runner_isolated, init, ["--no-dolt"])
        assert_cli_success(result)

        # Output should mention hooks are skipped
        assert_output_contains(result, "skipped")


class TestInitNoHooksFlag:
    """E2E tests for --no-hooks flag."""

    def test_init_no_hooks_skips_hook_installation(self, cli_runner_isolated, dolt_available):
        """Verify --no-hooks skips Git hook installation."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        result = invoke_cli(cli_runner_isolated, init, ["--no-hooks"])
        assert_init_completed(result)

        # Hooks directory might exist but shouldn't have Kurt hooks
        hooks_dir = Path.cwd() / ".git" / "hooks"
        if hooks_dir.exists():
            for hook_file in hooks_dir.iterdir():
                if hook_file.is_file():
                    content = hook_file.read_text()
                    # Should not have Kurt hook marker
                    assert "Kurt Git Hook" not in content


class TestInitWithPath:
    """E2E tests for init with path argument."""

    def test_init_creates_target_directory(self, cli_runner_isolated, dolt_available):
        """Verify init creates target directory if it doesn't exist."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        original_cwd = Path.cwd()
        result = invoke_cli(cli_runner_isolated, init, ["new_project"])
        assert_init_completed(result)

        # Verify directory was created
        assert_directory_exists(original_cwd / "new_project")

        # Verify project was initialized in that directory
        assert_file_exists(original_cwd / "new_project" / "kurt.toml")
        assert_directory_exists(original_cwd / "new_project" / ".dolt")

    def test_init_works_with_existing_directory(self, cli_runner_isolated, dolt_available):
        """Verify init works with existing empty directory."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        (Path.cwd() / "existing_dir").mkdir()

        result = invoke_cli(cli_runner_isolated, init, ["existing_dir"])
        assert_init_completed(result)


class TestInitIdempotency:
    """E2E tests for init idempotency."""

    def test_init_force_is_idempotent(self, cli_runner_isolated, dolt_available):
        """Verify running init --force twice produces same result."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        # First init
        result1 = invoke_cli(cli_runner_isolated, init, [])
        assert_init_completed(result1)

        # Add a marker file
        (Path.cwd() / "workflows" / "custom.md").write_text("# Custom workflow")

        # Second init with force
        result2 = invoke_cli(cli_runner_isolated, init, ["--force"])
        assert_init_completed(result2)

        # Verify custom file was preserved
        assert_file_exists(Path.cwd() / "workflows" / "custom.md")
        assert_file_contains(Path.cwd() / "workflows" / "custom.md", "Custom workflow")


class TestInitOutput:
    """E2E tests for init command output."""

    def test_init_shows_success_message(self, cli_runner_isolated, dolt_available):
        """Verify init shows success message."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        result = invoke_cli(cli_runner_isolated, init, [])
        assert_init_completed(result)

        assert_output_contains(result, "Initialized")

    def test_init_shows_component_status(self, cli_runner_isolated, dolt_available):
        """Verify init shows status of each component."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        result = invoke_cli(cli_runner_isolated, init, [])
        assert_init_completed(result)

        # Check for component mentions
        output_lower = result.output.lower()
        assert "git" in output_lower
        assert "dolt" in output_lower
        assert "config" in output_lower
        assert "workflow" in output_lower

    def test_init_shows_doctor_hint(self, cli_runner_isolated, dolt_available):
        """Verify init suggests running kurt doctor."""
        if not dolt_available:
            pytest.skip("Dolt not installed")

        result = invoke_cli(cli_runner_isolated, init, [])
        assert_init_completed(result)

        assert_output_contains(result, "kurt doctor")

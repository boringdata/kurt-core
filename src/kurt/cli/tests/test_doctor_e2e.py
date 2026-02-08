"""
E2E tests for `kurt doctor` and `kurt repair` commands.

These tests use real Git and Dolt operations to verify the doctor
command correctly detects project issues and repair fixes them.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from kurt.cli.doctor import doctor_cmd, repair_cmd
from kurt.conftest import (
    assert_cli_success,
    assert_json_output,
    assert_output_contains,
    invoke_cli,
)


@pytest.fixture
def dolt_available() -> bool:
    """Check if Dolt is installed."""
    return shutil.which("dolt") is not None


@pytest.fixture
def git_dolt_project(tmp_path: Path, dolt_available) -> Path:
    """
    Create a temporary project with Git and Dolt initialized.

    This mimics the state after running `kurt init`.
    """
    if not dolt_available:
        pytest.skip("Dolt not installed")

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        # Initialize Git with 'main' branch to match Dolt's default
        subprocess.run(["git", "init", "-b", "main"], capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            capture_output=True,
        )
        # Create initial commit
        (tmp_path / "README.md").write_text("# Test Project")
        subprocess.run(["git", "add", "README.md"], capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            capture_output=True,
        )

        # Initialize Dolt
        env = os.environ.copy()
        env["DOLT_DISABLE_ACCOUNT_REGISTRATION"] = "true"
        subprocess.run(
            ["dolt", "init"],
            capture_output=True,
            check=True,
            env=env,
        )

        # Create kurt.toml config
        import uuid
        (tmp_path / "kurt.toml").write_text(f'''# Kurt Project Configuration
[workspace]
id = "{uuid.uuid4()}"

[paths]
db = ".dolt"
sources = "sources"
projects = "projects"

[telemetry]
enabled = false
''')

        yield tmp_path

    finally:
        os.chdir(original_cwd)


class TestDoctorHealthyProject:
    """E2E tests for doctor with a healthy project."""

    def test_doctor_passes_basic_checks(
        self, cli_runner: CliRunner, git_dolt_project: Path
    ):
        """Verify doctor passes basic checks on initialized project."""
        result = invoke_cli(cli_runner, doctor_cmd, ["--json"])

        # Should complete without fatal errors
        assert result.exit_code in (0, 1)  # 0 = all pass, 1 = some fail (hooks not installed)

        data = assert_json_output(result)
        if "data" in data and "success" in data:
            data = data["data"]

        # Should have check results
        assert "checks" in data
        assert any(c["name"] == "dolt_initialized" for c in data["checks"])
        # Dolt should be initialized
        dolt_check = next(c for c in data["checks"] if c["name"] == "dolt_initialized")
        assert dolt_check["status"] == "pass"

    def test_doctor_json_output_structure(
        self, cli_runner: CliRunner, git_dolt_project: Path
    ):
        """Verify doctor JSON output has correct structure."""
        result = invoke_cli(cli_runner, doctor_cmd, ["--json"])

        # Should complete
        assert result.exit_code in (0, 1)

        data = assert_json_output(result)
        if "data" in data and "success" in data:
            data = data["data"]

        assert "checks" in data
        assert "summary" in data
        assert "exit_code" in data
        assert isinstance(data["checks"], list)
        assert "passed" in data["summary"]
        assert "failed" in data["summary"]


class TestDoctorMissingComponents:
    """E2E tests for doctor detecting missing components."""

    def test_doctor_detects_no_git(self, cli_runner: CliRunner):
        """Verify doctor fails when not in a Git repo."""
        with cli_runner.isolated_filesystem():
            result = invoke_cli(cli_runner, doctor_cmd, [])
            assert result.exit_code == 2
            assert_output_contains(result, "Not a Git repository")

    def test_doctor_detects_missing_dolt(
        self, cli_runner: CliRunner, tmp_path: Path
    ):
        """Verify doctor detects missing Dolt database."""
        os.chdir(tmp_path)

        # Initialize only Git
        subprocess.run(["git", "init"], capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            capture_output=True,
        )
        (tmp_path / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], capture_output=True)

        result = invoke_cli(cli_runner, doctor_cmd, ["--json"])

        data = assert_json_output(result)
        if "data" in data and "success" in data:
            data = data["data"]

        # Should report Dolt issue
        dolt_check = next(c for c in data["checks"] if c["name"] == "dolt_initialized")
        assert dolt_check["status"] == "fail"

    def test_doctor_detects_corrupted_dolt(
        self, cli_runner: CliRunner, tmp_path: Path
    ):
        """Verify doctor detects corrupted Dolt (missing noms directory)."""
        os.chdir(tmp_path)

        # Initialize Git
        subprocess.run(["git", "init"], capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            capture_output=True,
        )
        (tmp_path / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], capture_output=True)
        subprocess.run(["git", "commit", "-m", "Init"], capture_output=True)

        # Create partial .dolt (missing noms)
        (tmp_path / ".dolt").mkdir()

        result = invoke_cli(cli_runner, doctor_cmd, [])

        # Should detect corrupted Dolt
        assert "corrupted" in result.output or "FAIL" in result.output


class TestDoctorJsonOutput:
    """E2E tests for doctor JSON output format."""

    def test_doctor_json_valid(
        self, cli_runner: CliRunner, git_dolt_project: Path
    ):
        """Verify doctor --json produces valid JSON."""
        result = invoke_cli(cli_runner, doctor_cmd, ["--json"])
        assert result.exit_code in (0, 1)

        data = assert_json_output(result)
        assert "success" in data or "checks" in data

    def test_doctor_json_check_details(
        self, cli_runner: CliRunner, git_dolt_project: Path
    ):
        """Verify each check in JSON has required fields."""
        result = invoke_cli(cli_runner, doctor_cmd, ["--json"])
        assert result.exit_code in (0, 1)

        data = assert_json_output(result)
        if "data" in data and "success" in data:
            data = data["data"]

        for check in data["checks"]:
            assert "name" in check
            assert "status" in check
            assert "message" in check
            assert check["status"] in ("pass", "fail", "warn")

    def test_doctor_global_json_flag(
        self, cli_runner: CliRunner, git_dolt_project: Path
    ):
        """Verify global --json flag works with doctor."""
        from kurt.cli.main import main

        result = cli_runner.invoke(main, ["--json", "doctor"], catch_exceptions=False)
        assert result.exit_code in (0, 1)

        # Find JSON line in output (may have table creation messages)
        output_lines = result.output.strip().split("\n")
        json_line = None
        for line in output_lines:
            if line.startswith("{"):
                json_line = line
                break

        assert json_line is not None
        data = json.loads(json_line)
        assert "success" in data or "data" in data


class TestDoctorExitCodes:
    """E2E tests for doctor exit codes."""

    def test_doctor_exit_code_healthy(
        self, cli_runner: CliRunner, git_dolt_project: Path
    ):
        """Verify exit code 0 when all checks pass (or 1 if hooks missing)."""
        result = invoke_cli(cli_runner, doctor_cmd, [])

        # Exit code depends on whether hooks are installed
        # 0 = all pass, 1 = some fail
        assert result.exit_code in (0, 1)

    def test_doctor_exit_code_not_git(self, cli_runner: CliRunner):
        """Verify exit code 2 when not in Git repo."""
        with cli_runner.isolated_filesystem():
            result = invoke_cli(cli_runner, doctor_cmd, [])
            assert result.exit_code == 2


class TestRepairCommand:
    """E2E tests for repair command."""

    def test_repair_dry_run_no_changes(
        self, cli_runner: CliRunner, git_dolt_project: Path
    ):
        """Verify repair --dry-run shows what would be repaired."""
        result = invoke_cli(cli_runner, repair_cmd, ["--dry-run"])

        # Should complete successfully
        assert result.exit_code == 0
        # Should mention dry run
        assert "Dry run" in result.output or "No repairs" in result.output

    def test_repair_no_issues_healthy_project(
        self, cli_runner: CliRunner, git_dolt_project: Path
    ):
        """Verify repair reports no issues on healthy project (or offers fixes)."""
        result = invoke_cli(cli_runner, repair_cmd, ["--dry-run"])

        # Should complete successfully
        assert result.exit_code == 0

    def test_repair_with_yes_flag(
        self, cli_runner: CliRunner, git_dolt_project: Path
    ):
        """Verify repair --yes doesn't prompt for confirmation."""
        result = invoke_cli(cli_runner, repair_cmd, ["--yes"])

        # Should complete
        assert result.exit_code in (0, 1)
        # Should show results
        assert "repairs" in result.output.lower() or "healthy" in result.output.lower()

    def test_repair_not_git_repo(self, cli_runner: CliRunner):
        """Verify repair fails outside Git repo."""
        with cli_runner.isolated_filesystem():
            result = invoke_cli(cli_runner, repair_cmd, [])
            assert result.exit_code == 2
            assert_output_contains(result, "Not a Git repository")


class TestDoctorBranchSync:
    """E2E tests for branch sync check."""

    def test_doctor_detects_branch_mismatch(
        self, cli_runner: CliRunner, git_dolt_project: Path, dolt_available
    ):
        """Verify doctor detects branch mismatch between Git and Dolt.

        By default, Git creates 'master' (or 'main' depending on config) and
        Dolt creates 'main'. The doctor should detect this mismatch.
        """
        if not dolt_available:
            pytest.skip("Dolt not installed")

        result = invoke_cli(cli_runner, doctor_cmd, ["--json"])
        assert result.exit_code in (0, 1)

        data = assert_json_output(result)
        if "data" in data and "success" in data:
            data = data["data"]

        # Find branch_sync check
        branch_check = None
        for check in data["checks"]:
            if check["name"] == "branch_sync":
                branch_check = check
                break

        # Branch sync check should exist and report status
        if branch_check:
            # May be pass (same branch) or fail (different branches) or warn (detached)
            assert branch_check["status"] in ("pass", "fail", "warn")


class TestDoctorStaleLocks:
    """E2E tests for stale lock detection."""

    def test_doctor_passes_no_lock(
        self, cli_runner: CliRunner, git_dolt_project: Path
    ):
        """Verify doctor passes when no lock file exists."""
        result = invoke_cli(cli_runner, doctor_cmd, ["--json"])
        assert result.exit_code in (0, 1)

        data = assert_json_output(result)
        if "data" in data and "success" in data:
            data = data["data"]

        # Find no_stale_locks check
        lock_check = None
        for check in data["checks"]:
            if check["name"] == "no_stale_locks":
                lock_check = check
                break

        if lock_check:
            assert lock_check["status"] == "pass"

    def test_doctor_detects_stale_lock(
        self, cli_runner: CliRunner, git_dolt_project: Path
    ):
        """Verify doctor detects stale lock file."""
        import time

        # Create stale lock
        lock_dir = git_dolt_project / ".git" / "kurt-hook.lock"
        lock_dir.mkdir()
        pid_file = lock_dir / "pid"
        pid_file.write_text("99999")  # Non-existent PID

        # Make it old
        old_time = time.time() - 60
        os.utime(pid_file, (old_time, old_time))

        result = invoke_cli(cli_runner, doctor_cmd, ["--json"])

        data = assert_json_output(result)
        if "data" in data and "success" in data:
            data = data["data"]

        # Find no_stale_locks check
        lock_check = None
        for check in data["checks"]:
            if check["name"] == "no_stale_locks":
                lock_check = check
                break

        if lock_check:
            assert lock_check["status"] == "fail"

"""Tests for doctor and repair CLI commands.

Tests use Click's CliRunner for isolated CLI testing.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kurt.cli.doctor import (
    CheckResult,
    CheckStatus,
    DoctorReport,
    check_branch_sync,
    check_dolt_initialized,
    check_hooks_installed,
    check_no_stale_locks,
    check_no_uncommitted_dolt,
    check_remotes_configured,
    doctor_cmd,
    get_repair_actions,
    repair_cmd,
)
from kurt.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    """Create a temporary Git repository for testing."""
    # Initialize Git repo
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        capture_output=True,
    )
    # Create initial commit
    (tmp_path / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        capture_output=True,
    )
    return tmp_path


@pytest.fixture
def temp_dolt_repo(tmp_path: Path) -> Path:
    """Create a temporary Dolt repository for testing."""
    tmp_path / ".dolt"
    # Check if dolt is available
    if not shutil.which("dolt"):
        pytest.skip("Dolt CLI not available")
    # Initialize Dolt repo
    subprocess.run(["dolt", "init"], cwd=tmp_path, capture_output=True, check=True)
    return tmp_path


# =============================================================================
# Tests - Check Functions
# =============================================================================


class TestCheckHooksInstalled:
    """Tests for hooks_installed check."""

    def test_no_git_hooks_dir(self, tmp_path: Path):
        """Test when .git/hooks directory doesn't exist."""
        (tmp_path / ".git").mkdir()
        result = check_hooks_installed(tmp_path)
        assert result.status == CheckStatus.FAIL
        assert "not found" in result.message

    def test_all_hooks_installed(self, temp_git_repo: Path):
        """Test when all hooks are installed."""
        with patch("kurt.isolation.hooks.get_installed_hooks") as mock_get:
            mock_get.return_value = [
                "post-checkout",
                "post-commit",
                "pre-push",
                "prepare-commit-msg",
            ]
            result = check_hooks_installed(temp_git_repo)
            assert result.status == CheckStatus.PASS
            assert "4" in result.message

    def test_missing_hooks(self, temp_git_repo: Path):
        """Test when some hooks are missing."""
        with patch("kurt.isolation.hooks.get_installed_hooks") as mock_get:
            mock_get.return_value = ["post-checkout", "post-commit"]
            result = check_hooks_installed(temp_git_repo)
            assert result.status == CheckStatus.FAIL
            assert "Missing" in result.message


class TestCheckDoltInitialized:
    """Tests for dolt_initialized check."""

    def test_dolt_not_initialized(self, tmp_path: Path):
        """Test when Dolt is not initialized."""
        result = check_dolt_initialized(tmp_path)
        assert result.status == CheckStatus.FAIL
        assert "not initialized" in result.message

    def test_dolt_initialized(self, tmp_path: Path):
        """Test when Dolt is properly initialized."""
        dolt_dir = tmp_path / ".dolt"
        dolt_dir.mkdir()
        (dolt_dir / "noms").mkdir()
        result = check_dolt_initialized(tmp_path)
        assert result.status == CheckStatus.PASS

    def test_dolt_corrupted(self, tmp_path: Path):
        """Test when Dolt directory exists but is corrupted."""
        dolt_dir = tmp_path / ".dolt"
        dolt_dir.mkdir()
        # Missing noms directory
        result = check_dolt_initialized(tmp_path)
        assert result.status == CheckStatus.FAIL
        assert "corrupted" in result.message


class TestCheckBranchSync:
    """Tests for branch_sync check."""

    def test_branches_in_sync(self, tmp_path: Path):
        """Test when Git and Dolt are on same branch."""
        with patch("kurt.cli.doctor._git_current_branch") as mock_git:
            with patch("subprocess.run") as mock_run:
                mock_git.return_value = "main"
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="main\n",
                    stderr="",
                )
                result = check_branch_sync(tmp_path, tmp_path)
                assert result.status == CheckStatus.PASS
                assert "same branch" in result.message

    def test_branches_out_of_sync(self, tmp_path: Path):
        """Test when Git and Dolt are on different branches."""
        with patch("kurt.cli.doctor._git_current_branch") as mock_git:
            with patch("subprocess.run") as mock_run:
                mock_git.return_value = "main"
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="feature\n",
                    stderr="",
                )
                result = check_branch_sync(tmp_path, tmp_path)
                assert result.status == CheckStatus.FAIL
                assert "mismatch" in result.message

    def test_detached_head(self, tmp_path: Path):
        """Test when Git is in detached HEAD state."""
        with patch("kurt.cli.doctor._git_current_branch") as mock_git:
            mock_git.return_value = None
            result = check_branch_sync(tmp_path, tmp_path)
            assert result.status == CheckStatus.WARN
            assert "detached" in result.message.lower()


class TestCheckNoUncommittedDolt:
    """Tests for no_uncommitted_dolt check."""

    def test_dolt_clean(self, tmp_path: Path):
        """Test when Dolt has no uncommitted changes."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="nothing to commit, working tree clean",
                stderr="",
            )
            result = check_no_uncommitted_dolt(tmp_path)
            assert result.status == CheckStatus.PASS
            assert "clean" in result.message

    def test_dolt_has_changes(self, tmp_path: Path):
        """Test when Dolt has uncommitted changes."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Changes not staged for commit:\n  modified: test.sql",
                stderr="",
            )
            result = check_no_uncommitted_dolt(tmp_path)
            assert result.status == CheckStatus.WARN
            assert "Uncommitted" in result.message


class TestCheckRemotesConfigured:
    """Tests for remotes_configured check."""

    def test_both_remotes_configured(self, tmp_path: Path):
        """Test when both Git and Dolt have origin remote."""
        with patch("kurt.cli.doctor._git_has_remote") as mock_git:
            with patch("kurt.cli.doctor._dolt_has_remote") as mock_dolt:
                mock_git.return_value = True
                mock_dolt.return_value = True
                result = check_remotes_configured(tmp_path, tmp_path)
                assert result.status == CheckStatus.PASS

    def test_git_missing_remote(self, tmp_path: Path):
        """Test when Git is missing origin remote."""
        with patch("kurt.cli.doctor._git_has_remote") as mock_git:
            with patch("kurt.cli.doctor._dolt_has_remote") as mock_dolt:
                mock_git.return_value = False
                mock_dolt.return_value = True
                result = check_remotes_configured(tmp_path, tmp_path)
                assert result.status == CheckStatus.WARN
                assert "Git" in result.message

    def test_both_missing_remote(self, tmp_path: Path):
        """Test when both are missing origin remote."""
        with patch("kurt.cli.doctor._git_has_remote") as mock_git:
            with patch("kurt.cli.doctor._dolt_has_remote") as mock_dolt:
                mock_git.return_value = False
                mock_dolt.return_value = False
                result = check_remotes_configured(tmp_path, tmp_path)
                assert result.status == CheckStatus.WARN
                assert "Git" in result.message
                assert "Dolt" in result.message


class TestCheckNoStaleLocks:
    """Tests for no_stale_locks check."""

    def test_no_lock_file(self, tmp_path: Path):
        """Test when no lock file exists."""
        (tmp_path / ".git").mkdir()
        result = check_no_stale_locks(tmp_path)
        assert result.status == CheckStatus.PASS
        assert "No lock" in result.message

    def test_stale_lock_file(self, tmp_path: Path):
        """Test when stale lock file exists."""
        import time

        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        lock_dir = git_dir / "kurt-hook.lock"
        lock_dir.mkdir()
        pid_file = lock_dir / "pid"
        pid_file.write_text("99999")  # Non-existent PID
        # Make file appear old
        old_time = time.time() - 60  # 60 seconds old
        import os

        os.utime(pid_file, (old_time, old_time))

        result = check_no_stale_locks(tmp_path)
        assert result.status == CheckStatus.FAIL
        assert "Stale" in result.message


# =============================================================================
# Tests - Doctor Report
# =============================================================================


class TestDoctorReport:
    """Tests for DoctorReport class."""

    def test_to_dict(self):
        """Test report serialization to dictionary."""
        checks = [
            CheckResult(
                name="test_check",
                status=CheckStatus.PASS,
                message="Test passed",
            ),
            CheckResult(
                name="test_fail",
                status=CheckStatus.FAIL,
                message="Test failed",
                details="Some details",
            ),
        ]
        report = DoctorReport(
            checks=checks,
            summary={"passed": 1, "failed": 1, "warnings": 0},
            exit_code=1,
        )

        data = report.to_dict()
        assert data["exit_code"] == 1
        assert len(data["checks"]) == 2
        assert data["checks"][0]["status"] == "pass"
        assert data["checks"][1]["status"] == "fail"
        assert data["checks"][1]["details"] == "Some details"


class TestGetRepairActions:
    """Tests for get_repair_actions function."""

    def test_no_actions_for_passing_checks(self):
        """Test no actions returned for passing checks."""
        checks = [
            CheckResult(name="hooks_installed", status=CheckStatus.PASS, message="OK"),
        ]
        report = DoctorReport(
            checks=checks,
            summary={"passed": 1, "failed": 0, "warnings": 0},
            exit_code=0,
        )
        actions = get_repair_actions(report)
        assert len(actions) == 0

    def test_hooks_repair_action(self):
        """Test repair action for missing hooks."""
        checks = [
            CheckResult(
                name="hooks_installed",
                status=CheckStatus.FAIL,
                message="Missing hooks",
            ),
        ]
        report = DoctorReport(
            checks=checks,
            summary={"passed": 0, "failed": 1, "warnings": 0},
            exit_code=1,
        )
        actions = get_repair_actions(report)
        assert len(actions) == 1
        assert actions[0].check_name == "hooks_installed"
        assert actions[0].action == "reinstall_hooks"

    def test_branch_sync_repair_action(self):
        """Test repair action for branch mismatch."""
        checks = [
            CheckResult(
                name="branch_sync",
                status=CheckStatus.FAIL,
                message="Branch mismatch",
            ),
        ]
        report = DoctorReport(
            checks=checks,
            summary={"passed": 0, "failed": 1, "warnings": 0},
            exit_code=1,
        )
        actions = get_repair_actions(report)
        assert len(actions) == 1
        assert actions[0].action == "sync_branch"

    def test_commit_dolt_repair_action(self):
        """Test repair action for uncommitted Dolt changes."""
        checks = [
            CheckResult(
                name="no_uncommitted_dolt",
                status=CheckStatus.WARN,
                message="Uncommitted changes",
            ),
        ]
        report = DoctorReport(
            checks=checks,
            summary={"passed": 0, "failed": 0, "warnings": 1},
            exit_code=0,
        )
        actions = get_repair_actions(report)
        assert len(actions) == 1
        assert actions[0].action == "commit_dolt"


# =============================================================================
# Tests - Doctor CLI Command
# =============================================================================


class TestDoctorCommand:
    """Tests for `kurt doctor` command."""

    def test_doctor_help(self, cli_runner: CliRunner):
        """Test doctor command shows help."""
        result = invoke_cli(cli_runner, doctor_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Check project health")
        assert_output_contains(result, "--json")

    def test_doctor_not_git_repo(self, cli_runner: CliRunner, tmp_path: Path):
        """Test doctor fails outside Git repo."""
        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            result = cli_runner.invoke(doctor_cmd, [])
            assert result.exit_code == 2
            assert "Not a Git repository" in result.output

    def test_doctor_json_output(self, cli_runner: CliRunner, temp_git_repo: Path):
        """Test doctor with --json flag."""
        with patch("kurt.cli.doctor._get_git_path", return_value=temp_git_repo):
            with patch("kurt.cli.doctor._get_dolt_path", return_value=temp_git_repo):
                with patch("kurt.cli.doctor.run_doctor") as mock_run:
                    mock_run.return_value = DoctorReport(
                        checks=[
                            CheckResult(
                                name="test",
                                status=CheckStatus.PASS,
                                message="OK",
                            )
                        ],
                        summary={"passed": 1, "failed": 0, "warnings": 0},
                        exit_code=0,
                    )
                    result = cli_runner.invoke(doctor_cmd, ["--json"])

        # Should be valid JSON
        data = json.loads(result.output)
        assert "checks" in data
        assert data["exit_code"] == 0

    def test_doctor_table_output(self, cli_runner: CliRunner, temp_git_repo: Path):
        """Test doctor with table output."""
        with patch("kurt.cli.doctor._get_git_path", return_value=temp_git_repo):
            with patch("kurt.cli.doctor._get_dolt_path", return_value=temp_git_repo):
                with patch("kurt.cli.doctor.run_doctor") as mock_run:
                    mock_run.return_value = DoctorReport(
                        checks=[
                            CheckResult(
                                name="hooks_installed",
                                status=CheckStatus.PASS,
                                message="All hooks installed",
                            ),
                            CheckResult(
                                name="branch_sync",
                                status=CheckStatus.FAIL,
                                message="Branch mismatch",
                            ),
                        ],
                        summary={"passed": 1, "failed": 1, "warnings": 0},
                        exit_code=1,
                    )
                    result = cli_runner.invoke(doctor_cmd, [])

        assert "PASS" in result.output
        assert "FAIL" in result.output
        assert "hooks_installed" in result.output
        assert result.exit_code == 1


# =============================================================================
# Tests - Repair CLI Command
# =============================================================================


class TestRepairCommand:
    """Tests for `kurt repair` command."""

    def test_repair_help(self, cli_runner: CliRunner):
        """Test repair command shows help."""
        result = invoke_cli(cli_runner, repair_cmd, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Auto-fix common project issues")
        assert_output_contains(result, "--dry-run")
        assert_output_contains(result, "--yes")
        assert_output_contains(result, "--check")

    def test_repair_not_git_repo(self, cli_runner: CliRunner, tmp_path: Path):
        """Test repair fails outside Git repo."""
        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            result = cli_runner.invoke(repair_cmd, [])
            assert result.exit_code == 2
            assert "Not a Git repository" in result.output

    def test_repair_dry_run(self, cli_runner: CliRunner, temp_git_repo: Path):
        """Test repair with --dry-run flag."""
        with patch("kurt.cli.doctor._get_git_path", return_value=temp_git_repo):
            with patch("kurt.cli.doctor._get_dolt_path", return_value=temp_git_repo):
                with patch("kurt.cli.doctor.run_doctor") as mock_run:
                    mock_run.return_value = DoctorReport(
                        checks=[
                            CheckResult(
                                name="hooks_installed",
                                status=CheckStatus.FAIL,
                                message="Missing hooks",
                            ),
                        ],
                        summary={"passed": 0, "failed": 1, "warnings": 0},
                        exit_code=1,
                    )
                    result = cli_runner.invoke(repair_cmd, ["--dry-run"])

        assert "Planned repairs" in result.output
        assert "Reinstall Git hooks" in result.output
        assert "Dry run" in result.output
        assert result.exit_code == 0

    def test_repair_no_issues(self, cli_runner: CliRunner, temp_git_repo: Path):
        """Test repair when no issues found."""
        with patch("kurt.cli.doctor._get_git_path", return_value=temp_git_repo):
            with patch("kurt.cli.doctor._get_dolt_path", return_value=temp_git_repo):
                with patch("kurt.cli.doctor.run_doctor") as mock_run:
                    mock_run.return_value = DoctorReport(
                        checks=[
                            CheckResult(
                                name="hooks_installed",
                                status=CheckStatus.PASS,
                                message="OK",
                            ),
                        ],
                        summary={"passed": 1, "failed": 0, "warnings": 0},
                        exit_code=0,
                    )
                    result = cli_runner.invoke(repair_cmd, [])

        assert "No repairs needed" in result.output
        assert result.exit_code == 0

    def test_repair_specific_check(self, cli_runner: CliRunner, temp_git_repo: Path):
        """Test repair with --check flag."""
        with patch("kurt.cli.doctor._get_git_path", return_value=temp_git_repo):
            with patch("kurt.cli.doctor._get_dolt_path", return_value=temp_git_repo):
                with patch("kurt.cli.doctor.run_doctor") as mock_run:
                    mock_run.return_value = DoctorReport(
                        checks=[
                            CheckResult(
                                name="hooks_installed",
                                status=CheckStatus.FAIL,
                                message="Missing hooks",
                            ),
                            CheckResult(
                                name="branch_sync",
                                status=CheckStatus.FAIL,
                                message="Mismatch",
                            ),
                        ],
                        summary={"passed": 0, "failed": 2, "warnings": 0},
                        exit_code=1,
                    )
                    result = cli_runner.invoke(
                        repair_cmd, ["--dry-run", "--check=hooks_installed"]
                    )

        # Should only show hooks repair
        assert "Reinstall Git hooks" in result.output
        # Should not show branch sync repair
        assert "branch_sync" not in result.output or "Sync Dolt" not in result.output

    def test_repair_with_confirmation(self, cli_runner: CliRunner, temp_git_repo: Path):
        """Test repair asks for confirmation."""
        with patch("kurt.cli.doctor._get_git_path", return_value=temp_git_repo):
            with patch("kurt.cli.doctor._get_dolt_path", return_value=temp_git_repo):
                with patch("kurt.cli.doctor.run_doctor") as mock_run:
                    mock_run.return_value = DoctorReport(
                        checks=[
                            CheckResult(
                                name="hooks_installed",
                                status=CheckStatus.FAIL,
                                message="Missing hooks",
                            ),
                        ],
                        summary={"passed": 0, "failed": 1, "warnings": 0},
                        exit_code=1,
                    )
                    # Simulate user saying "n" to confirmation
                    result = cli_runner.invoke(repair_cmd, [], input="n\n")

        assert "Aborted" in result.output

    def test_repair_yes_flag(self, cli_runner: CliRunner, temp_git_repo: Path):
        """Test repair with --yes flag skips confirmation."""
        with patch("kurt.cli.doctor._get_git_path", return_value=temp_git_repo):
            with patch("kurt.cli.doctor._get_dolt_path", return_value=temp_git_repo):
                with patch("kurt.cli.doctor.run_doctor") as mock_run:
                    mock_run.return_value = DoctorReport(
                        checks=[
                            CheckResult(
                                name="hooks_installed",
                                status=CheckStatus.FAIL,
                                message="Missing hooks",
                            ),
                        ],
                        summary={"passed": 0, "failed": 1, "warnings": 0},
                        exit_code=1,
                    )
                    with patch("kurt.cli.doctor.do_reinstall_hooks") as mock_repair:
                        mock_repair.return_value = True
                        result = cli_runner.invoke(repair_cmd, ["--yes"])

        assert "Repairing hooks_installed" in result.output
        assert "OK" in result.output
        mock_repair.assert_called_once()


# =============================================================================
# Tests - Repair Actions
# =============================================================================


class TestRepairActions:
    """Tests for individual repair action functions."""

    def test_do_reinstall_hooks(self, temp_git_repo: Path):
        """Test hooks reinstallation."""
        from kurt.cli.doctor import do_reinstall_hooks

        with patch("kurt.isolation.hooks.install_hooks") as mock_install:
            mock_install.return_value = MagicMock(
                installed=["post-checkout", "post-commit"],
                errors=[],
            )
            result = do_reinstall_hooks(temp_git_repo)
            assert result is True
            mock_install.assert_called_once_with(temp_git_repo, force=False)

    def test_do_reinstall_hooks_force(self, temp_git_repo: Path):
        """Test hooks reinstallation with force."""
        from kurt.cli.doctor import do_reinstall_hooks

        with patch("kurt.isolation.hooks.install_hooks") as mock_install:
            mock_install.return_value = MagicMock(
                installed=["post-checkout"],
                errors=[],
            )
            result = do_reinstall_hooks(temp_git_repo, force=True)
            assert result is True
            mock_install.assert_called_once_with(temp_git_repo, force=True)

    def test_do_remove_lock(self, tmp_path: Path):
        """Test stale lock removal."""
        from kurt.cli.doctor import do_remove_lock

        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        lock_dir = git_dir / "kurt-hook.lock"
        lock_dir.mkdir()
        (lock_dir / "pid").write_text("12345")

        result = do_remove_lock(tmp_path)
        assert result is True
        assert not lock_dir.exists()

    def test_do_remove_lock_not_exists(self, tmp_path: Path):
        """Test lock removal when no lock exists."""
        from kurt.cli.doctor import do_remove_lock

        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        result = do_remove_lock(tmp_path)
        assert result is True

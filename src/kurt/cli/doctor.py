"""Doctor and repair CLI commands for project health.

Provides commands for diagnosing and fixing common issues:
- kurt doctor: Check project health with actionable messages
- kurt repair: Auto-fix common issues non-destructively

Doctor checks:
1. hooks_installed: All 4 Git hooks present and executable
2. dolt_initialized: .dolt/ exists and valid
3. branch_sync: Git branch matches Dolt branch
4. no_uncommitted_dolt: Dolt status is clean
5. remotes_configured: Both Git and Dolt have 'origin' remote
6. no_stale_locks: No .git/kurt-hook.lock older than 30s
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import click
from rich.console import Console

from kurt.cli.robot import ErrorCode, OutputContext, robot_error, robot_success

console = Console()


# =============================================================================
# Check Status Types
# =============================================================================


class CheckStatus(str, Enum):
    """Status of a doctor check."""

    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


@dataclass
class CheckResult:
    """Result of a single doctor check."""

    name: str
    status: CheckStatus
    message: str
    details: str | None = None


@dataclass
class DoctorReport:
    """Full doctor report with all checks."""

    checks: list[CheckResult]
    summary: dict[str, int]
    exit_code: int

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary for JSON output."""
        return {
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "details": c.details,
                }
                for c in self.checks
            ],
            "summary": self.summary,
            "exit_code": self.exit_code,
        }


# =============================================================================
# Helper Functions
# =============================================================================


def _get_dolt_path() -> Path:
    """Get the Dolt repository path.

    Looks for .dolt directory in the current working directory.
    Future: Could be configurable via kurt.config.
    """
    return Path.cwd() / ".dolt"


def _get_dolt_db():
    """Get DoltDB instance for the current project."""
    from kurt.db.utils import get_dolt_db

    return get_dolt_db()


def _get_git_path() -> Path:
    """Get the Git repository path."""
    return Path.cwd()


def _run_git(args: list[str], path: Path | None = None) -> subprocess.CompletedProcess:
    """Run a git command and return result."""
    cmd = ["git"]
    if path:
        cmd.extend(["-C", str(path)])
    cmd.extend(args)
    return subprocess.run(cmd, capture_output=True, text=True)


def _is_git_repo(path: Path) -> bool:
    """Check if path is inside a Git repository."""
    result = _run_git(["rev-parse", "--is-inside-work-tree"], path)
    return result.returncode == 0 and result.stdout.strip() == "true"


def _git_current_branch(path: Path) -> str | None:
    """Get current Git branch name."""
    result = _run_git(["symbolic-ref", "--short", "HEAD"], path)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _git_has_remote(path: Path, remote: str = "origin") -> bool:
    """Check if Git has a specific remote configured."""
    result = _run_git(["remote", "get-url", remote], path)
    return result.returncode == 0


def _dolt_has_remote(dolt_path: Path, remote: str = "origin") -> bool:
    """Check if Dolt has a specific remote configured.

    Args:
        dolt_path: The .dolt directory path (commands run from parent)
    """
    result = subprocess.run(
        ["dolt", "remote", "-v"],
        cwd=dolt_path.parent,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    return remote in result.stdout


def _dolt_status_clean(dolt_path: Path) -> tuple[bool, str]:
    """Check if Dolt working directory is clean.

    Args:
        dolt_path: The .dolt directory path (commands run from parent)

    Returns:
        Tuple of (is_clean, status_output)
    """
    result = subprocess.run(
        ["dolt", "status"],
        cwd=dolt_path.parent,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False, result.stderr
    # Clean status contains "nothing to commit"
    is_clean = "nothing to commit" in result.stdout.lower()
    return is_clean, result.stdout


# =============================================================================
# Doctor Checks
# =============================================================================


def check_hooks_installed(git_path: Path) -> CheckResult:
    """Check if all Git hooks are installed and executable."""
    from kurt.db.isolation.hooks import HOOK_NAMES, get_installed_hooks

    hooks_dir = git_path / ".git" / "hooks"
    if not hooks_dir.is_dir():
        return CheckResult(
            name="hooks_installed",
            status=CheckStatus.FAIL,
            message="Git hooks directory not found",
            details=f"Expected: {hooks_dir}",
        )

    installed = get_installed_hooks(git_path)
    missing = set(HOOK_NAMES) - set(installed)

    if not missing:
        return CheckResult(
            name="hooks_installed",
            status=CheckStatus.PASS,
            message=f"All {len(HOOK_NAMES)} Git hooks installed",
        )

    # Check if hooks exist but aren't Kurt hooks
    non_kurt = []
    for hook in missing:
        hook_path = hooks_dir / hook
        if hook_path.exists():
            non_kurt.append(hook)

    if non_kurt:
        return CheckResult(
            name="hooks_installed",
            status=CheckStatus.WARN,
            message=f"Missing {len(missing)} Kurt hook(s), {len(non_kurt)} non-Kurt hook(s) exist",
            details=f"Missing: {', '.join(sorted(missing))}. Use --force to overwrite.",
        )

    return CheckResult(
        name="hooks_installed",
        status=CheckStatus.FAIL,
        message=f"Missing {len(missing)} Git hook(s)",
        details=f"Missing: {', '.join(sorted(missing))}",
    )


def check_dolt_initialized(dolt_path: Path) -> CheckResult:
    """Check if Dolt repository is initialized.

    Args:
        dolt_path: The .dolt directory path (not the project root)
    """
    # dolt_path is already the .dolt directory
    if not dolt_path.exists():
        return CheckResult(
            name="dolt_initialized",
            status=CheckStatus.FAIL,
            message="Dolt repository not initialized",
            details=f"Run 'dolt init' in {dolt_path.parent}",
        )

    # Check for essential Dolt files
    noms_dir = dolt_path / "noms"
    if not noms_dir.exists():
        return CheckResult(
            name="dolt_initialized",
            status=CheckStatus.FAIL,
            message="Dolt repository appears corrupted",
            details="Missing .dolt/noms directory",
        )

    return CheckResult(
        name="dolt_initialized",
        status=CheckStatus.PASS,
        message="Dolt repository initialized",
    )


def check_branch_sync(git_path: Path, dolt_path: Path) -> CheckResult:
    """Check if Git and Dolt branches match.

    Args:
        git_path: The git repository root
        dolt_path: The .dolt directory path (commands run from parent)
    """
    git_branch = _git_current_branch(git_path)
    if git_branch is None:
        return CheckResult(
            name="branch_sync",
            status=CheckStatus.WARN,
            message="Git is in detached HEAD state",
            details="Checkout a branch to enable sync",
        )

    # Get Dolt current branch
    result = subprocess.run(
        ["dolt", "branch", "--show-current"],
        cwd=dolt_path.parent,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return CheckResult(
            name="branch_sync",
            status=CheckStatus.FAIL,
            message="Could not determine Dolt branch",
            details=result.stderr.strip() if result.stderr else None,
        )

    dolt_branch = result.stdout.strip()

    if git_branch == dolt_branch:
        return CheckResult(
            name="branch_sync",
            status=CheckStatus.PASS,
            message=f"Git and Dolt on same branch: {git_branch}",
        )

    return CheckResult(
        name="branch_sync",
        status=CheckStatus.FAIL,
        message=f"Branch mismatch: Git={git_branch}, Dolt={dolt_branch}",
        details=f"Run 'kurt repair' to sync Dolt to '{git_branch}'",
    )


def check_no_uncommitted_dolt(dolt_path: Path) -> CheckResult:
    """Check if Dolt has uncommitted changes."""
    is_clean, status_output = _dolt_status_clean(dolt_path)

    if is_clean:
        return CheckResult(
            name="no_uncommitted_dolt",
            status=CheckStatus.PASS,
            message="Dolt working directory clean",
        )

    return CheckResult(
        name="no_uncommitted_dolt",
        status=CheckStatus.WARN,
        message="Uncommitted Dolt changes detected",
        details="Run 'kurt repair' to commit or 'dolt status' for details",
    )


def check_remotes_configured(git_path: Path, dolt_path: Path) -> CheckResult:
    """Check if both Git and Dolt have remotes configured."""
    git_has_origin = _git_has_remote(git_path, "origin")
    dolt_has_origin = _dolt_has_remote(dolt_path, "origin")

    if git_has_origin and dolt_has_origin:
        return CheckResult(
            name="remotes_configured",
            status=CheckStatus.PASS,
            message="Both Git and Dolt have 'origin' remote",
        )

    missing = []
    if not git_has_origin:
        missing.append("Git")
    if not dolt_has_origin:
        missing.append("Dolt")

    return CheckResult(
        name="remotes_configured",
        status=CheckStatus.WARN,
        message=f"Missing 'origin' remote in: {', '.join(missing)}",
        details="Remote push/pull operations may not work",
    )


def check_no_stale_locks(git_path: Path) -> CheckResult:
    """Check for stale kurt-hook.lock files."""
    lock_dir = git_path / ".git" / "kurt-hook.lock"

    if not lock_dir.exists():
        return CheckResult(
            name="no_stale_locks",
            status=CheckStatus.PASS,
            message="No lock files present",
        )

    # Check lock age
    try:
        pid_file = lock_dir / "pid"
        if pid_file.exists():
            mtime = pid_file.stat().st_mtime
            age = time.time() - mtime
            if age < 30:
                return CheckResult(
                    name="no_stale_locks",
                    status=CheckStatus.PASS,
                    message=f"Active lock ({age:.0f}s old)",
                )

            # Check if process is still running
            pid = pid_file.read_text().strip()
            if pid.isdigit():
                try:
                    os.kill(int(pid), 0)  # Check if process exists
                    return CheckResult(
                        name="no_stale_locks",
                        status=CheckStatus.PASS,
                        message=f"Lock held by active process (PID {pid})",
                    )
                except OSError:
                    pass  # Process doesn't exist

            return CheckResult(
                name="no_stale_locks",
                status=CheckStatus.FAIL,
                message=f"Stale lock file ({age:.0f}s old)",
                details="Run 'kurt repair' to remove stale lock",
            )
    except Exception as e:
        return CheckResult(
            name="no_stale_locks",
            status=CheckStatus.WARN,
            message="Could not check lock file",
            details=str(e),
        )

    return CheckResult(
        name="no_stale_locks",
        status=CheckStatus.WARN,
        message="Lock directory exists but no PID file",
    )


# =============================================================================
# Doctor Command
# =============================================================================


def run_doctor(git_path: Path, dolt_path: Path) -> DoctorReport:
    """Run all doctor checks and return report."""
    checks: list[CheckResult] = []

    # Run all checks
    checks.append(check_hooks_installed(git_path))
    checks.append(check_dolt_initialized(dolt_path))

    # Only check branch sync if Dolt is initialized
    dolt_init_result = checks[-1]
    if dolt_init_result.status == CheckStatus.PASS:
        checks.append(check_branch_sync(git_path, dolt_path))
        checks.append(check_no_uncommitted_dolt(dolt_path))
        checks.append(check_remotes_configured(git_path, dolt_path))

    checks.append(check_no_stale_locks(git_path))

    # Calculate summary
    summary = {
        "passed": sum(1 for c in checks if c.status == CheckStatus.PASS),
        "failed": sum(1 for c in checks if c.status == CheckStatus.FAIL),
        "warnings": sum(1 for c in checks if c.status == CheckStatus.WARN),
    }

    # Determine exit code
    if summary["failed"] > 0:
        exit_code = 1
    else:
        exit_code = 0

    return DoctorReport(checks=checks, summary=summary, exit_code=exit_code)


@click.command(name="doctor")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON (deprecated: use global --json)")
@click.pass_context
def doctor_cmd(ctx, as_json: bool):
    """Check project health and report issues.

    Runs a series of checks to verify the Kurt project is properly configured:

    \b
    1. hooks_installed: All Git hooks present and executable
    2. dolt_initialized: .dolt/ exists and valid
    3. branch_sync: Git branch matches Dolt branch
    4. no_uncommitted_dolt: Dolt status is clean
    5. remotes_configured: Both Git and Dolt have 'origin' remote
    6. sql_server: Dolt SQL server is reachable (server mode required)
    7. no_stale_locks: No .git/kurt-hook.lock older than 30s

    Exit codes:
      0: All checks passed
      1: One or more checks failed
      2: Doctor command itself failed

    Example:
        kurt doctor
        kurt --json doctor
        kurt doctor --json
    """
    # Get output context from global --json flag
    output: OutputContext = ctx.obj.get("output", OutputContext()) if ctx.obj else OutputContext()

    # Hybrid activation: global --json OR local --json flag
    use_json = output.json_mode or as_json

    try:
        git_path = _get_git_path()

        # Check if Git repo
        if not _is_git_repo(git_path):
            if use_json:
                print(
                    robot_error(
                        ErrorCode.CONFIG_ERROR,
                        "Not a Git repository",
                        hint="Run: git init",
                    )
                )
            else:
                console.print("[red]Error: Not a Git repository[/red]")
            raise SystemExit(2)

        # Get Dolt path
        dolt_path = _get_dolt_path()

        # Run checks
        report = run_doctor(git_path, dolt_path)

        if use_json:
            # Wrap in robot success envelope
            print(robot_success(report.to_dict(), exit_code=report.exit_code))
        else:
            _print_report(report)

        raise SystemExit(report.exit_code)

    except SystemExit:
        raise
    except Exception as e:
        if use_json:
            print(robot_error(ErrorCode.EXEC_ERROR, str(e)))
        else:
            console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(2)


def _print_report(report: DoctorReport):
    """Print doctor report in human-readable format."""
    console.print()
    console.print("[bold]Kurt Doctor Report[/bold]")
    console.print()

    for check in report.checks:
        if check.status == CheckStatus.PASS:
            icon = "[green]PASS[/green]"
        elif check.status == CheckStatus.FAIL:
            icon = "[red]FAIL[/red]"
        else:
            icon = "[yellow]WARN[/yellow]"

        console.print(f"  {icon} {check.name}: {check.message}")
        if check.details:
            console.print(f"       [dim]{check.details}[/dim]")

    console.print()
    summary = report.summary
    parts = []
    if summary["passed"]:
        parts.append(f"[green]{summary['passed']} passed[/green]")
    if summary["failed"]:
        parts.append(f"[red]{summary['failed']} failed[/red]")
    if summary["warnings"]:
        parts.append(f"[yellow]{summary['warnings']} warnings[/yellow]")

    console.print(f"Summary: {', '.join(parts)}")
    console.print()


# =============================================================================
# Repair Actions
# =============================================================================


@dataclass
class RepairAction:
    """A repair action to be performed."""

    check_name: str
    description: str
    action: str


def get_repair_actions(report: DoctorReport) -> list[RepairAction]:
    """Determine repair actions from doctor report."""
    actions = []

    for check in report.checks:
        if check.status == CheckStatus.PASS:
            continue

        if check.name == "hooks_installed" and check.status == CheckStatus.FAIL:
            actions.append(
                RepairAction(
                    check_name="hooks_installed",
                    description="Reinstall Git hooks",
                    action="reinstall_hooks",
                )
            )
        elif check.name == "branch_sync" and check.status == CheckStatus.FAIL:
            actions.append(
                RepairAction(
                    check_name="branch_sync",
                    description="Sync Dolt branch to match Git",
                    action="sync_branch",
                )
            )
        elif check.name == "no_uncommitted_dolt" and check.status == CheckStatus.WARN:
            actions.append(
                RepairAction(
                    check_name="no_uncommitted_dolt",
                    description="Commit pending Dolt changes",
                    action="commit_dolt",
                )
            )
        elif check.name == "no_stale_locks" and check.status == CheckStatus.FAIL:
            actions.append(
                RepairAction(
                    check_name="no_stale_locks",
                    description="Remove stale lock file",
                    action="remove_lock",
                )
            )

    return actions


def do_reinstall_hooks(git_path: Path, force: bool = False) -> bool:
    """Reinstall Git hooks."""
    from kurt.db.isolation.hooks import install_hooks

    result = install_hooks(git_path, force=force)
    return len(result.installed) > 0 and len(result.errors) == 0


def do_sync_branch(git_path: Path, dolt_path: Path) -> bool:
    """Sync Dolt branch to match Git branch."""
    from kurt.db.dolt import DoltDB
    from kurt.db.isolation.branch import sync_to_git

    dolt_db = DoltDB(dolt_path)
    try:
        sync_to_git(git_path, dolt_db)
        return True
    except Exception:
        return False


def do_commit_dolt(dolt_path: Path) -> bool:
    """Commit pending Dolt changes.

    Args:
        dolt_path: The .dolt directory path (commands run from parent)
    """
    # Stage all changes
    result = subprocess.run(
        ["dolt", "add", "-A"],
        cwd=dolt_path.parent,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False

    # Commit
    result = subprocess.run(
        ["dolt", "commit", "-m", "Auto-commit: kurt repair"],
        cwd=dolt_path.parent,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def do_remove_lock(git_path: Path) -> bool:
    """Remove stale lock file."""
    import shutil

    lock_dir = git_path / ".git" / "kurt-hook.lock"
    if lock_dir.exists():
        try:
            shutil.rmtree(lock_dir)
            return True
        except Exception:
            return False
    return True


# =============================================================================
# Repair Command
# =============================================================================


@click.command(name="repair")
@click.option("--dry-run", is_flag=True, help="Show what would be repaired without making changes")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
@click.option("--check", "check_name", help="Repair only a specific check")
@click.option("--force", "-f", is_flag=True, help="Force repair (e.g., overwrite existing hooks)")
def repair_cmd(dry_run: bool, yes: bool, check_name: str | None, force: bool):
    """Auto-fix common project issues.

    Runs doctor checks and attempts to repair any failures:

    \b
    Repairs:
    - hooks_installed=fail: Reinstall Git hooks
    - branch_sync=fail: Sync Dolt branch to match Git
    - no_uncommitted_dolt=warn: Commit pending Dolt changes
    - no_stale_locks=fail: Remove stale lock files

    Use --dry-run to preview repairs without making changes.

    Example:
        kurt repair                  # Fix all issues
        kurt repair --dry-run        # Preview repairs
        kurt repair --check=hooks_installed  # Fix specific check
        kurt repair --yes            # Skip confirmations
    """
    try:
        git_path = _get_git_path()

        # Check if Git repo
        if not _is_git_repo(git_path):
            console.print("[red]Error: Not a Git repository[/red]")
            raise SystemExit(2)

        # Get Dolt path
        dolt_path = _get_dolt_path()

        # Run doctor to get current state
        report = run_doctor(git_path, dolt_path)

        # Get repair actions
        actions = get_repair_actions(report)

        # Filter by specific check if requested
        if check_name:
            actions = [a for a in actions if a.check_name == check_name]
            if not actions:
                console.print(f"[yellow]No repairs needed for '{check_name}'[/yellow]")
                raise SystemExit(0)

        if not actions:
            console.print("[green]No repairs needed. Project is healthy.[/green]")
            raise SystemExit(0)

        # Show planned repairs
        console.print()
        console.print("[bold]Planned repairs:[/bold]")
        for action in actions:
            console.print(f"  - {action.description} ({action.check_name})")
        console.print()

        if dry_run:
            console.print("[dim]Dry run - no changes made[/dim]")
            raise SystemExit(0)

        # Confirm if not --yes
        if not yes:
            if not click.confirm("Proceed with repairs?"):
                console.print("[yellow]Aborted[/yellow]")
                raise SystemExit(0)

        # Execute repairs
        console.print()
        success_count = 0
        fail_count = 0

        for action in actions:
            console.print(f"  Repairing {action.check_name}...", end=" ")

            success = False
            if action.action == "reinstall_hooks":
                success = do_reinstall_hooks(git_path, force=force)
            elif action.action == "sync_branch":
                success = do_sync_branch(git_path, dolt_path)
            elif action.action == "commit_dolt":
                success = do_commit_dolt(dolt_path)
            elif action.action == "remove_lock":
                success = do_remove_lock(git_path)

            if success:
                console.print("[green]OK[/green]")
                success_count += 1
            else:
                console.print("[red]FAILED[/red]")
                fail_count += 1

        console.print()
        if fail_count == 0:
            console.print(f"[green]All {success_count} repair(s) completed successfully[/green]")
            raise SystemExit(0)
        else:
            console.print(
                f"[yellow]{success_count} repair(s) succeeded, {fail_count} failed[/yellow]"
            )
            raise SystemExit(1)

    except SystemExit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(2)

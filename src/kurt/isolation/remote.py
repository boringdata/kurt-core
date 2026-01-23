"""Git+Dolt remote operations (pull/push).

Sync local Git and Dolt repositories with their remotes.

Pull order:
1. git fetch (get refs, don't merge)
2. dolt pull (merge Dolt first - cell-level conflicts easier)
3. git pull (merge Git - line-level conflicts)

Push order:
1. dolt push (push data first)
2. git push (push code)
3. If git push fails: warn but don't rollback Dolt
"""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from shutil import which
from typing import Literal

from kurt.db.dolt import DoltDB, DoltError

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # seconds


class RemoteErrorCode(Enum):
    """Error codes for remote operations."""

    GIT_NOT_AVAILABLE = "git_not_available"
    GIT_NOT_REPO = "git_not_repo"
    DOLT_NOT_AVAILABLE = "dolt_not_available"
    DOLT_NOT_REPO = "dolt_not_repo"
    GIT_REMOTE_NOT_FOUND = "git_remote_not_found"
    DOLT_REMOTE_NOT_FOUND = "dolt_remote_not_found"
    GIT_NETWORK_ERROR = "git_network_error"
    DOLT_NETWORK_ERROR = "dolt_network_error"
    GIT_AUTH_ERROR = "git_auth_error"
    DOLT_AUTH_ERROR = "dolt_auth_error"
    GIT_CONFLICT = "git_conflict"
    DOLT_CONFLICT = "dolt_conflict"
    GIT_PUSH_FAILED = "git_push_failed"
    DOLT_PUSH_FAILED = "dolt_push_failed"
    GIT_PULL_FAILED = "git_pull_failed"
    DOLT_PULL_FAILED = "dolt_pull_failed"


class RemoteError(Exception):
    """Error during remote operations.

    Attributes:
        code: Error code identifying the type of failure.
        message: Human-readable error message.
        details: Optional additional context.
        suggestion: Optional fix suggestion.
    """

    def __init__(
        self,
        code: RemoteErrorCode,
        message: str,
        details: str | None = None,
        suggestion: str | None = None,
    ):
        self.code = code
        self.message = message
        self.details = details
        self.suggestion = suggestion
        super().__init__(message)

    def __repr__(self) -> str:
        return f"RemoteError(code={self.code.value!r}, message={self.message!r})"


@dataclass
class GitResult:
    """Result of a Git remote operation."""

    status: Literal["success", "error", "skipped"]
    commits_pulled: int = 0
    commits_pushed: int = 0
    error: str | None = None


@dataclass
class DoltResult:
    """Result of a Dolt remote operation."""

    status: Literal["success", "error", "skipped"]
    commits_pulled: int = 0
    commits_pushed: int = 0
    error: str | None = None


@dataclass
class PullResult:
    """Result of a pull operation."""

    git: GitResult = field(default_factory=lambda: GitResult(status="skipped"))
    dolt: DoltResult = field(default_factory=lambda: DoltResult(status="skipped"))

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "git": {
                "status": self.git.status,
                "commits_pulled": self.git.commits_pulled,
                "error": self.git.error,
            },
            "dolt": {
                "status": self.dolt.status,
                "commits_pulled": self.dolt.commits_pulled,
                "error": self.dolt.error,
            },
        }


@dataclass
class PushResult:
    """Result of a push operation."""

    git: GitResult = field(default_factory=lambda: GitResult(status="skipped"))
    dolt: DoltResult = field(default_factory=lambda: DoltResult(status="skipped"))

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "git": {
                "status": self.git.status,
                "commits_pushed": self.git.commits_pushed,
                "error": self.git.error,
            },
            "dolt": {
                "status": self.dolt.status,
                "commits_pushed": self.dolt.commits_pushed,
                "error": self.dolt.error,
            },
        }


# =============================================================================
# Helper Functions
# =============================================================================


def _git_available() -> bool:
    """Check if git CLI is available."""
    return which("git") is not None


def _is_git_repo(path: Path) -> bool:
    """Check if path is inside a Git repository."""
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() == "true"
    except subprocess.CalledProcessError:
        return False


def _git_remote_exists(path: Path, remote: str) -> bool:
    """Check if a Git remote exists."""
    result = subprocess.run(
        ["git", "-C", str(path), "remote"],
        capture_output=True,
        text=True,
    )
    remotes = result.stdout.strip().split("\n")
    return remote in remotes


def _git_current_branch(path: Path) -> str | None:
    """Get current Git branch name, or None if in detached HEAD state."""
    result = subprocess.run(
        ["git", "-C", str(path), "symbolic-ref", "--short", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _git_get_commit_count(path: Path, ref1: str, ref2: str) -> int:
    """Count commits between two refs."""
    result = subprocess.run(
        ["git", "-C", str(path), "rev-list", "--count", f"{ref1}..{ref2}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return 0
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


def _dolt_remote_exists(db: DoltDB, remote: str) -> bool:
    """Check if a Dolt remote exists."""
    try:
        output = db._run_cli(["remote", "-v"])
        for line in output.strip().split("\n"):
            if line.strip().startswith(remote):
                return True
        return False
    except Exception:
        return False


def _dolt_get_commit_count(db: DoltDB, ref1: str, ref2: str) -> int:
    """Count commits between two refs in Dolt."""
    try:
        output = db._run_cli(["log", "--oneline", f"{ref1}..{ref2}"])
        lines = [l for l in output.strip().split("\n") if l.strip()]
        return len(lines)
    except Exception:
        return 0


def _is_network_error(stderr: str) -> bool:
    """Check if error is network-related."""
    network_patterns = [
        "could not resolve host",
        "connection refused",
        "connection timed out",
        "network is unreachable",
        "no route to host",
        "failed to connect",
        "unable to access",
        "ssl",
        "tls",
    ]
    lower = stderr.lower()
    return any(p in lower for p in network_patterns)


def _is_auth_error(stderr: str) -> bool:
    """Check if error is authentication-related."""
    auth_patterns = [
        "authentication failed",
        "permission denied",
        "invalid credentials",
        "could not read",
        "access denied",
        "unauthorized",
        "403",
        "401",
    ]
    lower = stderr.lower()
    return any(p in lower for p in auth_patterns)


def _is_conflict_error(stderr: str) -> bool:
    """Check if error indicates a merge conflict."""
    conflict_patterns = [
        "conflict",
        "merge conflict",
        "automatic merge failed",
        "fix conflicts",
    ]
    lower = stderr.lower()
    return any(p in lower for p in conflict_patterns)


def _retry_with_backoff(
    fn,
    max_retries: int = MAX_RETRIES,
    initial_backoff: float = INITIAL_BACKOFF,
):
    """Execute function with exponential backoff retry."""
    last_error = None
    backoff = initial_backoff

    for attempt in range(max_retries):
        try:
            return fn()
        except subprocess.CalledProcessError as e:
            last_error = e
            stderr = e.stderr or ""

            # Don't retry auth errors or conflicts
            if _is_auth_error(stderr) or _is_conflict_error(stderr):
                raise

            # Only retry network errors
            if not _is_network_error(stderr):
                raise

            if attempt < max_retries - 1:
                logger.debug(f"Retry {attempt + 1}/{max_retries} after {backoff}s")
                time.sleep(backoff)
                backoff *= 2

    raise last_error


# =============================================================================
# Git Operations
# =============================================================================


def _git_fetch(path: Path, remote: str) -> None:
    """Fetch from Git remote."""
    cmd = ["git", "-C", str(path), "fetch", remote]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _git_pull(path: Path, remote: str, branch: str) -> int:
    """Pull from Git remote. Returns number of commits pulled."""
    # Get current HEAD before pull
    before = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    ).stdout.strip()

    # Pull
    cmd = ["git", "-C", str(path), "pull", remote, branch]
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    # Get HEAD after pull
    after = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    ).stdout.strip()

    # Count commits
    if before == after:
        return 0
    return _git_get_commit_count(path, before, after)


def _git_push(path: Path, remote: str, branch: str) -> int:
    """Push to Git remote. Returns number of commits pushed."""
    # Check if there are commits to push
    result = subprocess.run(
        ["git", "-C", str(path), "rev-list", f"{remote}/{branch}..HEAD"],
        capture_output=True,
        text=True,
    )
    commits_to_push = len([l for l in result.stdout.strip().split("\n") if l.strip()])

    if commits_to_push == 0:
        return 0

    # Push
    cmd = ["git", "-C", str(path), "push", remote, branch]
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    return commits_to_push


# =============================================================================
# Dolt Operations
# =============================================================================


def _dolt_pull(db: DoltDB, remote: str) -> int:
    """Pull from Dolt remote. Returns number of commits pulled."""
    branch = db.branch_current()

    # Get current HEAD before pull
    before = db._run_cli(["log", "-n", "1", "--oneline"]).strip().split()[0]

    # Pull
    db._run_cli(["pull", remote, branch])

    # Get HEAD after pull
    after = db._run_cli(["log", "-n", "1", "--oneline"]).strip().split()[0]

    # Count commits
    if before == after:
        return 0
    return _dolt_get_commit_count(db, before, after)


def _dolt_push(db: DoltDB, remote: str) -> int:
    """Push to Dolt remote. Returns number of commits pushed."""
    branch = db.branch_current()

    # Check if there are commits to push by comparing local and remote
    try:
        local_head = db._run_cli(["log", "-n", "1", "--oneline"]).strip().split()[0]
        remote_head_output = db._run_cli(
            ["log", f"{remote}/{branch}", "-n", "1", "--oneline"]
        )
        remote_head = remote_head_output.strip().split()[0] if remote_head_output.strip() else ""

        if local_head == remote_head:
            return 0

        commits_to_push = _dolt_get_commit_count(db, f"{remote}/{branch}", "HEAD")
    except Exception:
        # If we can't determine, just try to push
        commits_to_push = 0

    # Push
    db._run_cli(["push", remote, branch])

    return commits_to_push if commits_to_push > 0 else 1


# =============================================================================
# Public API
# =============================================================================


def pull(
    git_path: Path | str,
    dolt_db: DoltDB,
    remote: str = "origin",
    git_only: bool = False,
    dolt_only: bool = False,
) -> PullResult:
    """Pull changes from Git and Dolt remotes.

    Order:
    1. git fetch (get refs, don't merge yet)
    2. dolt pull (merge Dolt first - cell-level conflicts are easier)
    3. git pull (merge Git - line-level conflicts)

    Args:
        git_path: Path to Git repository.
        dolt_db: DoltDB instance for the Dolt repository.
        remote: Remote name (default: "origin").
        git_only: Only pull from Git.
        dolt_only: Only pull from Dolt.

    Returns:
        PullResult with status for both Git and Dolt.

    Raises:
        RemoteError: If validation fails (missing remote, not a repo, etc.)
    """
    git_path = Path(git_path).resolve()
    result = PullResult()

    # Validate Git environment (unless dolt_only)
    if not dolt_only:
        if not _git_available():
            raise RemoteError(
                code=RemoteErrorCode.GIT_NOT_AVAILABLE,
                message="Git CLI not found",
                suggestion="Install Git from https://git-scm.com/",
            )

        if not _is_git_repo(git_path):
            raise RemoteError(
                code=RemoteErrorCode.GIT_NOT_REPO,
                message=f"Not a Git repository: {git_path}",
            )

        if not _git_remote_exists(git_path, remote):
            raise RemoteError(
                code=RemoteErrorCode.GIT_REMOTE_NOT_FOUND,
                message=f"Git remote '{remote}' not found",
                suggestion=f"Run: git remote add {remote} <url>",
            )

    # Validate Dolt environment (unless git_only)
    if not git_only:
        if not dolt_db.exists():
            raise RemoteError(
                code=RemoteErrorCode.DOLT_NOT_REPO,
                message=f"Not a Dolt repository: {dolt_db.path}",
                suggestion="Run 'dolt init' to initialize a Dolt repository.",
            )

        if not _dolt_remote_exists(dolt_db, remote):
            raise RemoteError(
                code=RemoteErrorCode.DOLT_REMOTE_NOT_FOUND,
                message=f"Dolt remote '{remote}' not found",
                suggestion=f"Run: dolt remote add {remote} <url>",
            )

    # Step 1: Git fetch (get refs without merging)
    if not dolt_only:
        try:
            _retry_with_backoff(lambda: _git_fetch(git_path, remote))
            logger.debug(f"Git fetch from {remote} completed")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr or ""
            if _is_auth_error(stderr):
                result.git = GitResult(
                    status="error",
                    error="Authentication failed",
                )
                raise RemoteError(
                    code=RemoteErrorCode.GIT_AUTH_ERROR,
                    message="Git authentication failed",
                    details=stderr,
                    suggestion="Check your Git credentials or SSH keys",
                )
            elif _is_network_error(stderr):
                result.git = GitResult(
                    status="error",
                    error="Network error",
                )
                raise RemoteError(
                    code=RemoteErrorCode.GIT_NETWORK_ERROR,
                    message="Git network error",
                    details=stderr,
                    suggestion="Check your network connection",
                )
            else:
                result.git = GitResult(status="error", error=stderr)
                raise RemoteError(
                    code=RemoteErrorCode.GIT_PULL_FAILED,
                    message="Git fetch failed",
                    details=stderr,
                )

    # Step 2: Dolt pull (merge Dolt first - cell-level conflicts easier)
    if not git_only:
        try:
            commits = _retry_with_backoff(lambda: _dolt_pull(dolt_db, remote))
            result.dolt = DoltResult(status="success", commits_pulled=commits)
            logger.info(f"Dolt pull: {commits} commit(s) pulled")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr or ""
            if _is_conflict_error(stderr):
                result.dolt = DoltResult(status="error", error="Merge conflict")
                raise RemoteError(
                    code=RemoteErrorCode.DOLT_CONFLICT,
                    message="Dolt merge conflict",
                    details=stderr,
                    suggestion="Resolve conflicts with: dolt conflicts resolve",
                )
            elif _is_auth_error(stderr):
                result.dolt = DoltResult(status="error", error="Authentication failed")
                raise RemoteError(
                    code=RemoteErrorCode.DOLT_AUTH_ERROR,
                    message="Dolt authentication failed",
                    details=stderr,
                    suggestion="Run: dolt login",
                )
            elif _is_network_error(stderr):
                result.dolt = DoltResult(status="error", error="Network error")
                raise RemoteError(
                    code=RemoteErrorCode.DOLT_NETWORK_ERROR,
                    message="Dolt network error",
                    details=stderr,
                    suggestion="Check your network connection",
                )
            else:
                result.dolt = DoltResult(status="error", error=stderr)
                raise RemoteError(
                    code=RemoteErrorCode.DOLT_PULL_FAILED,
                    message="Dolt pull failed",
                    details=stderr,
                )
        except DoltError as e:
            result.dolt = DoltResult(status="error", error=str(e))
            raise RemoteError(
                code=RemoteErrorCode.DOLT_PULL_FAILED,
                message="Dolt pull failed",
                details=str(e),
            )

    # Step 3: Git pull (merge Git - line-level conflicts)
    if not dolt_only:
        branch = _git_current_branch(git_path)
        if branch is None:
            result.git = GitResult(status="error", error="Detached HEAD state")
            raise RemoteError(
                code=RemoteErrorCode.GIT_PULL_FAILED,
                message="Cannot pull in detached HEAD state",
                suggestion="Checkout a branch first: git checkout <branch>",
            )

        try:
            commits = _retry_with_backoff(lambda: _git_pull(git_path, remote, branch))
            result.git = GitResult(status="success", commits_pulled=commits)
            logger.info(f"Git pull: {commits} commit(s) pulled")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr or ""
            if _is_conflict_error(stderr):
                result.git = GitResult(status="error", error="Merge conflict")
                raise RemoteError(
                    code=RemoteErrorCode.GIT_CONFLICT,
                    message="Git merge conflict",
                    details=stderr,
                    suggestion="Resolve conflicts and commit, then re-run pull",
                )
            else:
                result.git = GitResult(status="error", error=stderr)
                raise RemoteError(
                    code=RemoteErrorCode.GIT_PULL_FAILED,
                    message="Git pull failed",
                    details=stderr,
                )

    return result


def push(
    git_path: Path | str,
    dolt_db: DoltDB,
    remote: str = "origin",
    git_only: bool = False,
    dolt_only: bool = False,
) -> PushResult:
    """Push changes to Git and Dolt remotes.

    Order:
    1. dolt push (push data first)
    2. git push (push code)
    3. If git push fails: warn but don't rollback Dolt

    Args:
        git_path: Path to Git repository.
        dolt_db: DoltDB instance for the Dolt repository.
        remote: Remote name (default: "origin").
        git_only: Only push to Git.
        dolt_only: Only push to Dolt.

    Returns:
        PushResult with status for both Git and Dolt.

    Raises:
        RemoteError: If validation fails or Dolt push fails.
        Note: Git push errors are captured in result, not raised.
    """
    git_path = Path(git_path).resolve()
    result = PushResult()

    # Validate Git environment (unless dolt_only)
    if not dolt_only:
        if not _git_available():
            raise RemoteError(
                code=RemoteErrorCode.GIT_NOT_AVAILABLE,
                message="Git CLI not found",
                suggestion="Install Git from https://git-scm.com/",
            )

        if not _is_git_repo(git_path):
            raise RemoteError(
                code=RemoteErrorCode.GIT_NOT_REPO,
                message=f"Not a Git repository: {git_path}",
            )

        if not _git_remote_exists(git_path, remote):
            raise RemoteError(
                code=RemoteErrorCode.GIT_REMOTE_NOT_FOUND,
                message=f"Git remote '{remote}' not found",
                suggestion=f"Run: git remote add {remote} <url>",
            )

    # Validate Dolt environment (unless git_only)
    if not git_only:
        if not dolt_db.exists():
            raise RemoteError(
                code=RemoteErrorCode.DOLT_NOT_REPO,
                message=f"Not a Dolt repository: {dolt_db.path}",
                suggestion="Run 'dolt init' to initialize a Dolt repository.",
            )

        if not _dolt_remote_exists(dolt_db, remote):
            raise RemoteError(
                code=RemoteErrorCode.DOLT_REMOTE_NOT_FOUND,
                message=f"Dolt remote '{remote}' not found",
                suggestion=f"Run: dolt remote add {remote} <url>",
            )

    # Step 1: Dolt push (push data first)
    if not git_only:
        try:
            commits = _retry_with_backoff(lambda: _dolt_push(dolt_db, remote))
            result.dolt = DoltResult(status="success", commits_pushed=commits)
            logger.info(f"Dolt push: {commits} commit(s) pushed")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr or ""
            if _is_auth_error(stderr):
                result.dolt = DoltResult(status="error", error="Authentication failed")
                raise RemoteError(
                    code=RemoteErrorCode.DOLT_AUTH_ERROR,
                    message="Dolt authentication failed",
                    details=stderr,
                    suggestion="Run: dolt login",
                )
            elif _is_network_error(stderr):
                result.dolt = DoltResult(status="error", error="Network error")
                raise RemoteError(
                    code=RemoteErrorCode.DOLT_NETWORK_ERROR,
                    message="Dolt network error",
                    details=stderr,
                    suggestion="Check your network connection",
                )
            else:
                result.dolt = DoltResult(status="error", error=stderr)
                raise RemoteError(
                    code=RemoteErrorCode.DOLT_PUSH_FAILED,
                    message="Dolt push failed",
                    details=stderr,
                )
        except DoltError as e:
            result.dolt = DoltResult(status="error", error=str(e))
            raise RemoteError(
                code=RemoteErrorCode.DOLT_PUSH_FAILED,
                message="Dolt push failed",
                details=str(e),
            )

    # Step 2: Git push (push code)
    # Note: Git push errors are captured but not raised (don't rollback Dolt)
    if not dolt_only:
        branch = _git_current_branch(git_path)
        if branch is None:
            result.git = GitResult(status="error", error="Detached HEAD state")
            logger.warning("Git push skipped: detached HEAD state")
        else:
            try:
                commits = _retry_with_backoff(lambda: _git_push(git_path, remote, branch))
                result.git = GitResult(status="success", commits_pushed=commits)
                logger.info(f"Git push: {commits} commit(s) pushed")
            except subprocess.CalledProcessError as e:
                stderr = e.stderr or ""
                result.git = GitResult(status="error", error=stderr)
                # Don't raise - just log warning
                logger.warning(f"Git push failed (Dolt push succeeded): {stderr}")

    return result

"""Git+Dolt merge operations.

Merge source branch into target branch, handling both Dolt and Git atomically.

Algorithm:
1. Check Dolt conflicts first (dolt merge --no-commit)
2. If Dolt conflicts: report and abort
3. If Dolt clean: commit Dolt merge
4. Git merge
5. If Git conflicts: rollback Dolt, report Git conflicts

Exit codes:
- 0: merge successful
- 1: Dolt conflicts (merge aborted)
- 2: Git conflicts (Dolt rolled back)
- 3: rollback failed (manual intervention needed)
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from shutil import which
from typing import Any

from kurt.db.dolt import DoltDB

logger = logging.getLogger(__name__)


class MergeErrorCode(Enum):
    """Error codes for merge operations."""

    DOLT_CONFLICT = "dolt_conflict"
    GIT_CONFLICT = "git_conflict"
    ROLLBACK_FAILED = "rollback_failed"
    GIT_NOT_AVAILABLE = "git_not_available"
    GIT_NOT_REPO = "git_not_repo"
    DOLT_NOT_AVAILABLE = "dolt_not_available"
    DOLT_NOT_REPO = "dolt_not_repo"
    MERGE_IN_PROGRESS = "merge_in_progress"
    INVALID_BRANCH = "invalid_branch"
    NOTHING_TO_MERGE = "nothing_to_merge"


class MergeExitCode:
    """Exit codes for CLI."""

    SUCCESS = 0
    DOLT_CONFLICTS = 1
    GIT_CONFLICTS = 2
    ROLLBACK_FAILED = 3


@dataclass
class DoltConflict:
    """A conflict in a Dolt table."""

    table: str
    key: str
    ours: dict[str, Any] | None = None
    theirs: dict[str, Any] | None = None


@dataclass
class MergeConflict:
    """Information about merge conflicts."""

    dolt_conflicts: list[DoltConflict] = field(default_factory=list)
    git_conflicts: list[str] = field(default_factory=list)
    resolution_hint: str = ""


@dataclass
class MergeResult:
    """Result of a merge operation."""

    success: bool
    source_branch: str
    target_branch: str
    dolt_commit_hash: str | None = None
    git_commit_hash: str | None = None
    conflicts: MergeConflict | None = None
    message: str = ""


class MergeError(Exception):
    """Error during merge operation."""

    def __init__(
        self,
        code: MergeErrorCode,
        message: str,
        conflicts: MergeConflict | None = None,
    ):
        self.code = code
        self.message = message
        self.conflicts = conflicts
        super().__init__(message)

    def __repr__(self) -> str:
        return f"MergeError(code={self.code.value!r}, message={self.message!r})"


# =============================================================================
# Git Operations
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


def _git_branch_exists(path: Path, branch: str) -> bool:
    """Check if a Git branch exists."""
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--verify", f"refs/heads/{branch}"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _git_merge(
    path: Path,
    source: str,
    no_commit: bool = False,
    squash: bool = False,
    message: str | None = None,
) -> tuple[bool, str, list[str]]:
    """
    Merge source branch into current branch.

    Returns:
        Tuple of (success, commit_hash_or_empty, list_of_conflict_files)
    """
    cmd = ["git", "-C", str(path), "merge"]
    if no_commit:
        cmd.append("--no-commit")
    if squash:
        cmd.append("--squash")
    if message:
        cmd.extend(["-m", message])
    cmd.append(source)

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        # Success - get commit hash if not no_commit
        if not no_commit and not squash:
            hash_result = subprocess.run(
                ["git", "-C", str(path), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
            )
            commit_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else ""
            return True, commit_hash, []
        return True, "", []

    # Check for conflicts
    conflict_files = []
    if "CONFLICT" in result.stdout or "CONFLICT" in result.stderr:
        # Get list of conflicted files
        status_result = subprocess.run(
            ["git", "-C", str(path), "diff", "--name-only", "--diff-filter=U"],
            capture_output=True,
            text=True,
        )
        if status_result.returncode == 0:
            conflict_files = [f.strip() for f in status_result.stdout.split("\n") if f.strip()]

    return False, "", conflict_files


def _git_merge_abort(path: Path) -> bool:
    """Abort an in-progress Git merge."""
    result = subprocess.run(
        ["git", "-C", str(path), "merge", "--abort"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _git_merge_in_progress(path: Path) -> bool:
    """Check if a Git merge is in progress."""
    merge_head = path / ".git" / "MERGE_HEAD"
    return merge_head.exists()


# =============================================================================
# Dolt Operations
# =============================================================================


def _dolt_merge_no_commit(db: DoltDB, source: str) -> tuple[bool, list[DoltConflict]]:
    """
    Attempt Dolt merge without committing.

    Returns:
        Tuple of (success, list_of_conflicts)
    """
    try:
        output = db._run_cli(["merge", "--no-commit", source])

        # Check for conflicts
        if "CONFLICT" in output or "conflict" in output.lower():
            conflicts = _dolt_get_conflicts(db)
            return False, conflicts

        # Check for "Fast-forward" or successful merge
        return True, []

    except Exception as e:
        error_msg = str(e).lower()
        if "conflict" in error_msg:
            conflicts = _dolt_get_conflicts(db)
            return False, conflicts
        raise


def _dolt_get_conflicts(db: DoltDB) -> list[DoltConflict]:
    """Get list of Dolt conflicts."""
    conflicts = []

    try:
        # Get list of tables with conflicts
        result = db.query("SELECT * FROM dolt_conflicts")
        for row in result:
            table = row.get("table", "unknown")

            # Get conflict details for this table
            try:
                conflict_result = db.query(f"SELECT * FROM dolt_conflicts_{table}")
                for conflict_row in conflict_result:
                    # Extract key columns (usually primary key)
                    key_parts = []
                    ours = {}
                    theirs = {}

                    for col, val in conflict_row.items():
                        if col.startswith("base_"):
                            continue
                        elif col.startswith("our_"):
                            ours[col[4:]] = val
                        elif col.startswith("their_"):
                            theirs[col[6:]] = val
                        elif col in ("from_root_ish", "to_root_ish"):
                            continue
                        else:
                            key_parts.append(f"{col}={val}")

                    conflicts.append(
                        DoltConflict(
                            table=table,
                            key=", ".join(key_parts) if key_parts else "unknown",
                            ours=ours if ours else None,
                            theirs=theirs if theirs else None,
                        )
                    )
            except Exception:
                # Table might not have conflict details
                conflicts.append(
                    DoltConflict(
                        table=table,
                        key="unknown",
                    )
                )

    except Exception:
        # No conflicts table or query failed
        pass

    return conflicts


def _dolt_merge_commit(db: DoltDB, message: str) -> str:
    """Commit a Dolt merge and return commit hash."""
    try:
        db._run_cli(["add", "-A"])
        output = db._run_cli(["commit", "-m", message, "--allow-empty"])

        # Extract commit hash
        match = re.search(r"commit\s+([a-f0-9]+)", output.lower())
        return match.group(1) if match else ""
    except Exception as e:
        raise MergeError(
            code=MergeErrorCode.DOLT_CONFLICT,
            message=f"Failed to commit Dolt merge: {e}",
        ) from e


def _dolt_merge_abort(db: DoltDB) -> bool:
    """Abort an in-progress Dolt merge."""
    try:
        db._run_cli(["merge", "--abort"])
        return True
    except Exception:
        return False


def _dolt_reset_hard(db: DoltDB, ref: str = "HEAD~1") -> bool:
    """Reset Dolt to a previous state."""
    try:
        db._run_cli(["reset", "--hard", ref])
        return True
    except Exception:
        return False


def _dolt_branch_exists(db: DoltDB, branch: str) -> bool:
    """Check if a Dolt branch exists."""
    branches = db.branch_list()
    return any(b.name == branch for b in branches)


# =============================================================================
# Public API
# =============================================================================


def check_conflicts(
    source: str,
    target: str,
    git_path: Path | str,
    dolt_db: DoltDB,
) -> MergeConflict:
    """
    Pre-check for merge conflicts without modifying state.

    This is a best-effort check. Some conflicts may only be detected
    during actual merge.

    Args:
        source: Source branch name
        target: Target branch name (must be current branch)
        git_path: Path to Git repository
        dolt_db: DoltDB instance

    Returns:
        MergeConflict with any detected conflicts
    """
    git_path = Path(git_path).resolve()
    conflicts = MergeConflict()

    # Validate branches exist
    if not _git_branch_exists(git_path, source):
        raise MergeError(
            code=MergeErrorCode.INVALID_BRANCH,
            message=f"Git branch '{source}' does not exist",
        )

    if not _dolt_branch_exists(dolt_db, source):
        raise MergeError(
            code=MergeErrorCode.INVALID_BRANCH,
            message=f"Dolt branch '{source}' does not exist",
        )

    # Check Git - use merge-tree for conflict detection without modifying worktree
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(git_path),
                "merge-tree",
                "--write-tree",
                target,
                source,
            ],
            capture_output=True,
            text=True,
        )

        # Parse output for conflicts
        if result.returncode != 0 or "CONFLICT" in result.stdout:
            # Extract conflicted file paths
            for line in result.stdout.split("\n"):
                if line.startswith("CONFLICT"):
                    # Extract filename from "CONFLICT (content): Merge conflict in <file>"
                    match = re.search(r"Merge conflict in (.+)$", line)
                    if match:
                        conflicts.git_conflicts.append(match.group(1))
    except Exception:
        # merge-tree might not be available, skip pre-check
        pass

    # For Dolt, we can't easily pre-check without affecting state
    # The actual merge will detect conflicts

    if conflicts.dolt_conflicts or conflicts.git_conflicts:
        conflicts.resolution_hint = (
            "Use 'dolt conflicts resolve' for Dolt conflicts or edit files manually for Git."
        )

    return conflicts


def merge_branch(
    source: str,
    git_path: Path | str,
    dolt_db: DoltDB,
    strategy: str = "default",
    no_commit: bool = False,
    squash: bool = False,
    message: str | None = None,
) -> MergeResult:
    """
    Merge source branch into current branch in both Dolt and Git.

    Algorithm:
    1. Dolt merge --no-commit to check for conflicts
    2. If Dolt conflicts: abort and report
    3. If Dolt clean: commit Dolt merge
    4. Git merge
    5. If Git conflicts: rollback Dolt, report

    Args:
        source: Source branch name to merge
        git_path: Path to Git repository
        dolt_db: DoltDB instance
        strategy: Merge strategy (currently only "default" supported)
        no_commit: If True, merge but don't commit (for manual review)
        squash: If True, squash commits
        message: Custom commit message

    Returns:
        MergeResult with outcome

    Raises:
        MergeError: If merge fails
    """
    git_path = Path(git_path).resolve()

    # Validate environment
    if not _git_available():
        raise MergeError(
            code=MergeErrorCode.GIT_NOT_AVAILABLE,
            message="Git CLI not found",
        )

    if not _is_git_repo(git_path):
        raise MergeError(
            code=MergeErrorCode.GIT_NOT_REPO,
            message=f"Not a Git repository: {git_path}",
        )

    if not dolt_db.exists():
        raise MergeError(
            code=MergeErrorCode.DOLT_NOT_REPO,
            message=f"Not a Dolt repository: {dolt_db.path}",
        )

    # Get current branch (target)
    target = _git_current_branch(git_path)
    if not target:
        raise MergeError(
            code=MergeErrorCode.INVALID_BRANCH,
            message="Cannot merge in detached HEAD state",
        )

    dolt_target = dolt_db.branch_current()
    if not dolt_target:
        raise MergeError(
            code=MergeErrorCode.INVALID_BRANCH,
            message="Cannot determine current Dolt branch",
        )

    # Validate source branch exists
    if not _git_branch_exists(git_path, source):
        raise MergeError(
            code=MergeErrorCode.INVALID_BRANCH,
            message=f"Git branch '{source}' does not exist",
        )

    if not _dolt_branch_exists(dolt_db, source):
        raise MergeError(
            code=MergeErrorCode.INVALID_BRANCH,
            message=f"Dolt branch '{source}' does not exist",
        )

    # Check for in-progress merges
    if _git_merge_in_progress(git_path):
        raise MergeError(
            code=MergeErrorCode.MERGE_IN_PROGRESS,
            message="A Git merge is already in progress. Resolve or abort it first.",
        )

    merge_msg = message or f"Merge branch '{source}' into {target}"

    # Step 1: Try Dolt merge (no-commit to check for conflicts)
    logger.info(f"Attempting Dolt merge: {source} -> {target}")
    dolt_success, dolt_conflicts = _dolt_merge_no_commit(dolt_db, source)

    if not dolt_success:
        # Abort the Dolt merge
        _dolt_merge_abort(dolt_db)

        raise MergeError(
            code=MergeErrorCode.DOLT_CONFLICT,
            message="Dolt merge conflicts detected. Merge aborted.",
            conflicts=MergeConflict(
                dolt_conflicts=dolt_conflicts,
                resolution_hint="Use 'dolt conflicts resolve' or 'kurt merge --abort' to abort.",
            ),
        )

    # Step 2: Commit Dolt merge (unless no_commit requested)
    dolt_hash = ""
    if not no_commit:
        dolt_hash = _dolt_merge_commit(dolt_db, merge_msg)
        logger.info(f"Dolt merge committed: {dolt_hash}")

    # Step 3: Git merge
    logger.info(f"Attempting Git merge: {source} -> {target}")
    git_success, git_hash, git_conflict_files = _git_merge(
        git_path,
        source,
        no_commit=no_commit,
        squash=squash,
        message=merge_msg,
    )

    if not git_success:
        # Git merge failed - need to rollback Dolt
        logger.warning("Git merge conflicts detected. Rolling back Dolt merge.")

        # Abort Git merge
        _git_merge_abort(git_path)

        # Rollback Dolt commit
        if dolt_hash:
            rollback_success = _dolt_reset_hard(dolt_db, "HEAD~1")
            if not rollback_success:
                raise MergeError(
                    code=MergeErrorCode.ROLLBACK_FAILED,
                    message="Git merge failed and Dolt rollback failed. Manual intervention needed.",
                    conflicts=MergeConflict(
                        git_conflicts=git_conflict_files,
                        resolution_hint="Manually reset Dolt with 'dolt reset --hard HEAD~1'",
                    ),
                )
        else:
            # no_commit mode - just abort Dolt merge
            _dolt_merge_abort(dolt_db)

        raise MergeError(
            code=MergeErrorCode.GIT_CONFLICT,
            message="Git merge conflicts detected. Dolt changes rolled back.",
            conflicts=MergeConflict(
                git_conflicts=git_conflict_files,
                resolution_hint="Resolve Git conflicts manually, then re-run merge.",
            ),
        )

    # Success!
    return MergeResult(
        success=True,
        source_branch=source,
        target_branch=target,
        dolt_commit_hash=dolt_hash if dolt_hash else None,
        git_commit_hash=git_hash if git_hash else None,
        message=f"Successfully merged '{source}' into '{target}'",
    )


def abort_merge(
    git_path: Path | str,
    dolt_db: DoltDB,
) -> bool:
    """
    Abort any in-progress merge in both Git and Dolt.

    Args:
        git_path: Path to Git repository
        dolt_db: DoltDB instance

    Returns:
        True if abort successful (or no merge in progress)
    """
    git_path = Path(git_path).resolve()
    success = True

    # Abort Git merge if in progress
    if _git_merge_in_progress(git_path):
        if not _git_merge_abort(git_path):
            logger.error("Failed to abort Git merge")
            success = False

    # Abort Dolt merge (always safe to call)
    _dolt_merge_abort(dolt_db)

    return success

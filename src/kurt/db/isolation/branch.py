"""Git+Dolt branch synchronization.

Keep Git and Dolt branches in sync. Same branch names in both systems.
On git checkout: dolt checkout matching branch.
On git branch create: dolt branch create.

Branch names are user-defined; no auto-sanitization or enforced naming conventions.
If a name is invalid for Dolt, error with guidance.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from shutil import which

from kurt.db.dolt import DoltBranchError, DoltDB

logger = logging.getLogger(__name__)


class BranchSyncErrorCode(Enum):
    """Error codes for branch synchronization failures."""

    DETACHED_HEAD = "detached_head"
    ORPHAN_BRANCH = "orphan_branch"
    BRANCH_RENAME_NOT_SUPPORTED = "branch_rename_not_supported"
    GIT_NOT_AVAILABLE = "git_not_available"
    GIT_NOT_REPO = "git_not_repo"
    DOLT_NOT_AVAILABLE = "dolt_not_available"
    DOLT_NOT_REPO = "dolt_not_repo"
    BRANCH_CREATE_FAILED = "branch_create_failed"
    BRANCH_CHECKOUT_FAILED = "branch_checkout_failed"
    INVALID_BRANCH_NAME = "invalid_branch_name"


@dataclass
class BranchSyncResult:
    """Result of a successful branch sync operation.

    Attributes:
        git_branch: Name of the Git branch after sync.
        dolt_branch: Name of the Dolt branch after sync.
        created: True if a new branch was created in either system.
    """

    git_branch: str
    dolt_branch: str
    created: bool = False


class BranchSyncError(Exception):
    """Error during branch synchronization.

    Attributes:
        code: Error code identifying the type of failure.
        message: Human-readable error message.
        details: Optional additional context.
    """

    def __init__(
        self,
        code: BranchSyncErrorCode,
        message: str,
        details: str | None = None,
    ):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)

    def __repr__(self) -> str:
        return f"BranchSyncError(code={self.code.value!r}, message={self.message!r})"


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
        # Detached HEAD or other error
        return None
    return result.stdout.strip()


def _git_is_detached_head(path: Path) -> bool:
    """Check if Git repo is in detached HEAD state."""
    result = subprocess.run(
        ["git", "-C", str(path), "symbolic-ref", "-q", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.returncode != 0


def _git_branch_exists(path: Path, branch: str) -> bool:
    """Check if a Git branch exists."""
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--verify", f"refs/heads/{branch}"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _git_create_branch(path: Path, branch: str) -> None:
    """Create a new Git branch (does not switch to it)."""
    result = subprocess.run(
        ["git", "-C", str(path), "branch", branch],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise BranchSyncError(
            code=BranchSyncErrorCode.BRANCH_CREATE_FAILED,
            message=f"Failed to create Git branch '{branch}'",
            details=result.stderr.strip(),
        )


def _git_checkout(path: Path, branch: str, force: bool = False) -> None:
    """Switch to a Git branch."""
    cmd = ["git", "-C", str(path), "checkout"]
    if force:
        cmd.append("--force")
    cmd.append(branch)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise BranchSyncError(
            code=BranchSyncErrorCode.BRANCH_CHECKOUT_FAILED,
            message=f"Failed to checkout Git branch '{branch}'",
            details=result.stderr.strip(),
        )


# =============================================================================
# Dolt Operations (via DoltDB)
# =============================================================================


def _dolt_branch_exists(db: DoltDB, branch: str) -> bool:
    """Check if a Dolt branch exists."""
    branches = db.branch_list()
    return any(b.name == branch for b in branches)


def _dolt_create_branch(db: DoltDB, branch: str) -> None:
    """Create a new Dolt branch."""
    try:
        db.branch_create(branch)
    except DoltBranchError as e:
        # Check if it's an invalid branch name error
        error_msg = str(e).lower()
        if "invalid" in error_msg or "illegal" in error_msg:
            raise BranchSyncError(
                code=BranchSyncErrorCode.INVALID_BRANCH_NAME,
                message=f"Dolt rejected branch name '{branch}'",
                details=(
                    "Branch names must be valid for both Git and Dolt. "
                    "Use alphanumeric characters, dots, underscores, hyphens, and slashes."
                ),
            ) from e
        raise BranchSyncError(
            code=BranchSyncErrorCode.BRANCH_CREATE_FAILED,
            message=f"Failed to create Dolt branch '{branch}'",
            details=str(e),
        ) from e


def _dolt_checkout(db: DoltDB, branch: str, force: bool = False) -> None:
    """Switch to a Dolt branch."""
    try:
        db.branch_switch(branch, force=force)
    except DoltBranchError as e:
        raise BranchSyncError(
            code=BranchSyncErrorCode.BRANCH_CHECKOUT_FAILED,
            message=f"Failed to checkout Dolt branch '{branch}'",
            details=str(e),
        ) from e


# =============================================================================
# Public API
# =============================================================================


def sync_to_git(
    git_path: Path | str,
    dolt_db: DoltDB,
    force: bool = False,
) -> BranchSyncResult:
    """Sync Dolt to match the current Git branch.

    Checks the current Git branch and switches Dolt to the same branch.
    If the branch doesn't exist in Dolt, creates it.

    Args:
        git_path: Path to Git repository (or any path inside it).
        dolt_db: DoltDB instance for the Dolt repository.
        force: If True, force Dolt checkout discarding local changes.

    Returns:
        BranchSyncResult with the synchronized branch names.

    Raises:
        BranchSyncError: If sync fails (detached HEAD, invalid state, etc.)
    """
    git_path = Path(git_path).resolve()

    # Validate Git environment
    if not _git_available():
        raise BranchSyncError(
            code=BranchSyncErrorCode.GIT_NOT_AVAILABLE,
            message="Git CLI not found",
            details="Install Git from https://git-scm.com/",
        )

    if not _is_git_repo(git_path):
        raise BranchSyncError(
            code=BranchSyncErrorCode.GIT_NOT_REPO,
            message=f"Not a Git repository: {git_path}",
        )

    # Validate Dolt environment
    if not dolt_db.exists():
        raise BranchSyncError(
            code=BranchSyncErrorCode.DOLT_NOT_REPO,
            message=f"Not a Dolt repository: {dolt_db.path}",
            details="Run 'dolt init' to initialize a Dolt repository.",
        )

    # Check for detached HEAD
    if _git_is_detached_head(git_path):
        raise BranchSyncError(
            code=BranchSyncErrorCode.DETACHED_HEAD,
            message="Cannot sync in detached HEAD state",
            details="Checkout a branch first: git checkout <branch>",
        )

    git_branch = _git_current_branch(git_path)
    if git_branch is None:
        raise BranchSyncError(
            code=BranchSyncErrorCode.DETACHED_HEAD,
            message="Cannot sync in detached HEAD state",
            details="Checkout a branch first: git checkout <branch>",
        )

    # Get current Dolt branch
    dolt_branch = dolt_db.branch_current()

    # Already in sync
    if dolt_branch == git_branch:
        return BranchSyncResult(
            git_branch=git_branch,
            dolt_branch=dolt_branch,
            created=False,
        )

    # Create branch in Dolt if it doesn't exist
    created = False
    if not _dolt_branch_exists(dolt_db, git_branch):
        _dolt_create_branch(dolt_db, git_branch)
        created = True

    # Switch Dolt to match Git
    _dolt_checkout(dolt_db, git_branch, force=force)

    logger.info(f"Synced Dolt to Git branch: {git_branch}")
    return BranchSyncResult(
        git_branch=git_branch,
        dolt_branch=git_branch,
        created=created,
    )


def sync_to_dolt(
    git_path: Path | str,
    dolt_db: DoltDB,
    force: bool = False,
) -> BranchSyncResult:
    """Sync Git to match the current Dolt branch.

    Checks the current Dolt branch and switches Git to the same branch.
    If the branch doesn't exist in Git, creates it.

    Args:
        git_path: Path to Git repository (or any path inside it).
        dolt_db: DoltDB instance for the Dolt repository.
        force: If True, force Git checkout discarding local changes.
            Note: Dolt is synced first to avoid data loss.

    Returns:
        BranchSyncResult with the synchronized branch names.

    Raises:
        BranchSyncError: If sync fails.
    """
    git_path = Path(git_path).resolve()

    # Validate Git environment
    if not _git_available():
        raise BranchSyncError(
            code=BranchSyncErrorCode.GIT_NOT_AVAILABLE,
            message="Git CLI not found",
            details="Install Git from https://git-scm.com/",
        )

    if not _is_git_repo(git_path):
        raise BranchSyncError(
            code=BranchSyncErrorCode.GIT_NOT_REPO,
            message=f"Not a Git repository: {git_path}",
        )

    # Validate Dolt environment
    if not dolt_db.exists():
        raise BranchSyncError(
            code=BranchSyncErrorCode.DOLT_NOT_REPO,
            message=f"Not a Dolt repository: {dolt_db.path}",
            details="Run 'dolt init' to initialize a Dolt repository.",
        )

    # Get current Dolt branch
    dolt_branch = dolt_db.branch_current()
    if not dolt_branch:
        raise BranchSyncError(
            code=BranchSyncErrorCode.DOLT_NOT_REPO,
            message="Could not determine current Dolt branch",
        )

    # Get current Git branch (may be detached)
    git_branch = _git_current_branch(git_path)

    # Already in sync (and not detached)
    if git_branch == dolt_branch:
        return BranchSyncResult(
            git_branch=git_branch,
            dolt_branch=dolt_branch,
            created=False,
        )

    # Create branch in Git if it doesn't exist
    created = False
    if not _git_branch_exists(git_path, dolt_branch):
        _git_create_branch(git_path, dolt_branch)
        created = True

    # Switch Git to match Dolt
    _git_checkout(git_path, dolt_branch, force=force)

    logger.info(f"Synced Git to Dolt branch: {dolt_branch}")
    return BranchSyncResult(
        git_branch=dolt_branch,
        dolt_branch=dolt_branch,
        created=created,
    )


def create_both(
    name: str,
    git_path: Path | str,
    dolt_db: DoltDB,
    switch: bool = True,
) -> BranchSyncResult:
    """Create a branch in both Git and Dolt atomically.

    Creates the branch in Git first, then in Dolt. If Dolt creation fails,
    the Git branch is deleted to maintain atomicity.

    Args:
        name: Branch name to create.
        git_path: Path to Git repository (or any path inside it).
        dolt_db: DoltDB instance for the Dolt repository.
        switch: If True, switch to the new branch after creation.

    Returns:
        BranchSyncResult with the new branch names.

    Raises:
        BranchSyncError: If creation fails in either system.
    """
    git_path = Path(git_path).resolve()

    # Validate Git environment
    if not _git_available():
        raise BranchSyncError(
            code=BranchSyncErrorCode.GIT_NOT_AVAILABLE,
            message="Git CLI not found",
            details="Install Git from https://git-scm.com/",
        )

    if not _is_git_repo(git_path):
        raise BranchSyncError(
            code=BranchSyncErrorCode.GIT_NOT_REPO,
            message=f"Not a Git repository: {git_path}",
        )

    # Validate Dolt environment
    if not dolt_db.exists():
        raise BranchSyncError(
            code=BranchSyncErrorCode.DOLT_NOT_REPO,
            message=f"Not a Dolt repository: {dolt_db.path}",
            details="Run 'dolt init' to initialize a Dolt repository.",
        )

    # Check for detached HEAD (can't create branch from detached state reliably)
    if _git_is_detached_head(git_path):
        raise BranchSyncError(
            code=BranchSyncErrorCode.DETACHED_HEAD,
            message="Cannot create branch in detached HEAD state",
            details="Checkout a branch first: git checkout <branch>",
        )

    # Check if branch already exists in either system
    git_exists = _git_branch_exists(git_path, name)
    dolt_exists = _dolt_branch_exists(dolt_db, name)

    if git_exists and dolt_exists:
        # Branch exists in both - just switch if requested
        if switch:
            _git_checkout(git_path, name)
            _dolt_checkout(dolt_db, name)
        return BranchSyncResult(
            git_branch=name,
            dolt_branch=name,
            created=False,
        )

    # Create in Git first (easier to roll back)
    git_created = False
    if not git_exists:
        _git_create_branch(git_path, name)
        git_created = True

    # Create in Dolt
    try:
        if not dolt_exists:
            _dolt_create_branch(dolt_db, name)
    except BranchSyncError:
        # Rollback Git branch if Dolt creation failed
        if git_created:
            subprocess.run(
                ["git", "-C", str(git_path), "branch", "-d", name],
                capture_output=True,
            )
        raise

    # Switch to new branch if requested
    if switch:
        _git_checkout(git_path, name)
        _dolt_checkout(dolt_db, name)

    logger.info(f"Created branch in both Git and Dolt: {name}")
    return BranchSyncResult(
        git_branch=name,
        dolt_branch=name,
        created=True,
    )


def switch_both(
    name: str,
    git_path: Path | str,
    dolt_db: DoltDB,
    force: bool = False,
) -> BranchSyncResult:
    """Switch to a branch in both Git and Dolt.

    Switches Git first, then Dolt. If the branch doesn't exist in one system,
    it will be created.

    Args:
        name: Branch name to switch to.
        git_path: Path to Git repository (or any path inside it).
        dolt_db: DoltDB instance for the Dolt repository.
        force: If True, force checkout discarding local changes.

    Returns:
        BranchSyncResult with the switched branch names.

    Raises:
        BranchSyncError: If switch fails in either system.
    """
    git_path = Path(git_path).resolve()

    # Validate Git environment
    if not _git_available():
        raise BranchSyncError(
            code=BranchSyncErrorCode.GIT_NOT_AVAILABLE,
            message="Git CLI not found",
            details="Install Git from https://git-scm.com/",
        )

    if not _is_git_repo(git_path):
        raise BranchSyncError(
            code=BranchSyncErrorCode.GIT_NOT_REPO,
            message=f"Not a Git repository: {git_path}",
        )

    # Validate Dolt environment
    if not dolt_db.exists():
        raise BranchSyncError(
            code=BranchSyncErrorCode.DOLT_NOT_REPO,
            message=f"Not a Dolt repository: {dolt_db.path}",
            details="Run 'dolt init' to initialize a Dolt repository.",
        )

    # Check if branches exist
    git_exists = _git_branch_exists(git_path, name)
    dolt_exists = _dolt_branch_exists(dolt_db, name)

    if not git_exists and not dolt_exists:
        raise BranchSyncError(
            code=BranchSyncErrorCode.BRANCH_CHECKOUT_FAILED,
            message=f"Branch '{name}' does not exist in Git or Dolt",
            details="Use 'kurt branch create' to create a new branch.",
        )

    # Create branch in missing system if needed
    created = False
    if not git_exists:
        _git_create_branch(git_path, name)
        created = True
    if not dolt_exists:
        _dolt_create_branch(dolt_db, name)
        created = True

    # Switch both
    _git_checkout(git_path, name, force=force)
    _dolt_checkout(dolt_db, name, force=force)

    logger.info(f"Switched to branch in both Git and Dolt: {name}")
    return BranchSyncResult(
        git_branch=name,
        dolt_branch=name,
        created=created,
    )


def _git_delete_branch(path: Path, branch: str, force: bool = False) -> None:
    """Delete a Git branch."""
    flag = "-D" if force else "-d"
    result = subprocess.run(
        ["git", "-C", str(path), "branch", flag, branch],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise BranchSyncError(
            code=BranchSyncErrorCode.BRANCH_CHECKOUT_FAILED,
            message=f"Failed to delete Git branch '{branch}'",
            details=result.stderr.strip(),
        )


def delete_both(
    name: str,
    git_path: Path | str,
    dolt_db: DoltDB,
    force: bool = False,
) -> BranchSyncResult:
    """Delete a branch from both Git and Dolt.

    Args:
        name: Branch name to delete.
        git_path: Path to Git repository (or any path inside it).
        dolt_db: DoltDB instance for the Dolt repository.
        force: If True, force delete even if not merged.

    Returns:
        BranchSyncResult indicating success.

    Raises:
        BranchSyncError: If deletion fails or branch is protected.
    """
    git_path = Path(git_path).resolve()

    # Validate Git environment
    if not _git_available():
        raise BranchSyncError(
            code=BranchSyncErrorCode.GIT_NOT_AVAILABLE,
            message="Git CLI not found",
            details="Install Git from https://git-scm.com/",
        )

    if not _is_git_repo(git_path):
        raise BranchSyncError(
            code=BranchSyncErrorCode.GIT_NOT_REPO,
            message=f"Not a Git repository: {git_path}",
        )

    # Validate Dolt environment
    if not dolt_db.exists():
        raise BranchSyncError(
            code=BranchSyncErrorCode.DOLT_NOT_REPO,
            message=f"Not a Dolt repository: {dolt_db.path}",
            details="Run 'dolt init' to initialize a Dolt repository.",
        )

    # Cannot delete current branch
    git_current = _git_current_branch(git_path)
    dolt_current = dolt_db.branch_current()

    if git_current == name:
        raise BranchSyncError(
            code=BranchSyncErrorCode.BRANCH_CHECKOUT_FAILED,
            message=f"Cannot delete current Git branch '{name}'",
            details="Switch to a different branch first.",
        )

    if dolt_current == name:
        raise BranchSyncError(
            code=BranchSyncErrorCode.BRANCH_CHECKOUT_FAILED,
            message=f"Cannot delete current Dolt branch '{name}'",
            details="Switch to a different branch first.",
        )

    # Check if branches exist
    git_exists = _git_branch_exists(git_path, name)
    dolt_exists = _dolt_branch_exists(dolt_db, name)

    if not git_exists and not dolt_exists:
        raise BranchSyncError(
            code=BranchSyncErrorCode.BRANCH_CHECKOUT_FAILED,
            message=f"Branch '{name}' does not exist in Git or Dolt",
        )

    # Delete from Git if exists
    if git_exists:
        _git_delete_branch(git_path, name, force=force)

    # Delete from Dolt if exists
    if dolt_exists:
        try:
            dolt_db.branch_delete(name, force=force)
        except DoltBranchError as e:
            raise BranchSyncError(
                code=BranchSyncErrorCode.BRANCH_CHECKOUT_FAILED,
                message=f"Failed to delete Dolt branch '{name}'",
                details=str(e),
            ) from e

    logger.info(f"Deleted branch from Git and Dolt: {name}")
    return BranchSyncResult(
        git_branch=name,
        dolt_branch=name,
        created=False,
    )


@dataclass
class BranchStatus:
    """Sync status for a branch across Git and Dolt.

    Attributes:
        branch: Branch name.
        git_commit: Git commit hash (short), or None if missing.
        dolt_commit: Dolt commit hash (short), or None if missing.
        in_sync: True if branch exists in both systems.
        is_current: True if this is the current branch.
        status: Human-readable status (e.g., "clean", "dolt missing").
    """

    branch: str
    git_commit: str | None = None
    dolt_commit: str | None = None
    in_sync: bool = False
    is_current: bool = False
    status: str = "unknown"


def _git_get_commit_hash(path: Path, branch: str) -> str | None:
    """Get the short commit hash for a Git branch."""
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--short", f"refs/heads/{branch}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def list_branches(
    git_path: Path | str,
    dolt_db: DoltDB,
) -> list[BranchStatus]:
    """List all branches with sync status.

    Returns a merged list of branches from both Git and Dolt,
    showing which branches exist in each system.

    Args:
        git_path: Path to Git repository (or any path inside it).
        dolt_db: DoltDB instance for the Dolt repository.

    Returns:
        List of BranchStatus objects sorted by branch name.

    Raises:
        BranchSyncError: If listing fails.
    """
    git_path = Path(git_path).resolve()

    # Validate Git environment
    if not _git_available():
        raise BranchSyncError(
            code=BranchSyncErrorCode.GIT_NOT_AVAILABLE,
            message="Git CLI not found",
            details="Install Git from https://git-scm.com/",
        )

    if not _is_git_repo(git_path):
        raise BranchSyncError(
            code=BranchSyncErrorCode.GIT_NOT_REPO,
            message=f"Not a Git repository: {git_path}",
        )

    # Validate Dolt environment
    if not dolt_db.exists():
        raise BranchSyncError(
            code=BranchSyncErrorCode.DOLT_NOT_REPO,
            message=f"Not a Dolt repository: {dolt_db.path}",
            details="Run 'dolt init' to initialize a Dolt repository.",
        )

    # Get current branches
    git_current = _git_current_branch(git_path)
    dolt_current = dolt_db.branch_current()

    # Get Git branches
    result = subprocess.run(
        ["git", "-C", str(git_path), "branch", "--format=%(refname:short)"],
        capture_output=True,
        text=True,
    )
    git_branches = set(result.stdout.strip().split("\n")) if result.returncode == 0 else set()
    git_branches.discard("")  # Remove empty strings

    # Get Dolt branches
    dolt_branch_list = dolt_db.branch_list()
    dolt_branches = {b.name for b in dolt_branch_list}
    dolt_hashes = {b.name: b.hash for b in dolt_branch_list}

    # Merge branch lists
    all_branches = git_branches | dolt_branches

    statuses = []
    for branch in sorted(all_branches):
        git_exists = branch in git_branches
        dolt_exists = branch in dolt_branches

        # Get commit hashes
        git_commit = _git_get_commit_hash(git_path, branch) if git_exists else None
        dolt_commit = dolt_hashes.get(branch)
        if dolt_commit:
            dolt_commit = dolt_commit[:7]  # Short hash

        # Determine status
        if git_exists and dolt_exists:
            in_sync = True
            status = "clean"
        elif git_exists and not dolt_exists:
            in_sync = False
            status = "dolt missing"
        elif not git_exists and dolt_exists:
            in_sync = False
            status = "git missing"
        else:
            in_sync = False
            status = "unknown"

        # Check if current
        is_current = (git_current == branch) or (dolt_current == branch)

        statuses.append(
            BranchStatus(
                branch=branch,
                git_commit=git_commit,
                dolt_commit=dolt_commit,
                in_sync=in_sync,
                is_current=is_current,
                status=status,
            )
        )

    return statuses

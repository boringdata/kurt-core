"""Git hooks for auto-sync between Git and Dolt.

Install Git hooks that automatically synchronize Git and Dolt branches:
- post-checkout: Sync Dolt branch to match Git after checkout
- post-commit: Commit Dolt changes with same message
- pre-push: Verify Dolt is in sync before push
- prepare-commit-msg: Block git merge (require kurt merge)

Hooks are shell scripts that call kurt CLI commands.

Usage:
    from kurt.db.isolation.hooks import install_hooks, uninstall_hooks

    # Install hooks to a repository
    install_hooks("/path/to/repo")

    # Remove hooks
    uninstall_hooks("/path/to/repo")

Opt-out:
    KURT_SKIP_HOOKS=1 git checkout feature  # Skip hooks for this command
"""

from __future__ import annotations

import logging
import stat
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Hook names and their corresponding scripts
HOOK_NAMES = [
    "post-checkout",
    "post-commit",
    "pre-push",
    "prepare-commit-msg",
]

# Lock file for reentrancy protection
LOCK_FILE = "kurt-hook.lock"

# Maximum lock hold time in seconds
LOCK_TIMEOUT = 30


class HookExitCode(Enum):
    """Exit codes for hook scripts."""

    SUCCESS = 0  # Operation succeeded
    SYNC_FAILED = 1  # Sync failed, block git operation
    NOT_INITIALIZED = 2  # Kurt not initialized, allow git operation with warning


@dataclass
class HookInstallResult:
    """Result of hook installation."""

    installed: list[str]
    backed_up: list[str]
    skipped: list[str]
    errors: list[str]


@dataclass
class HookUninstallResult:
    """Result of hook uninstallation."""

    removed: list[str]
    restored: list[str]
    not_found: list[str]
    errors: list[str]


# =============================================================================
# Hook Script Templates
# =============================================================================

# Common header for all hook scripts
HOOK_HEADER = '''#!/bin/bash
# Kurt Git Hook - Auto-generated
# Do not edit manually. Reinstall with: kurt hooks install

# Skip if KURT_SKIP_HOOKS is set
if [ "${KURT_SKIP_HOOKS:-0}" = "1" ]; then
    exit 0
fi

# Skip in CI environments
if [ "${CI:-}" = "true" ] || [ "${GITHUB_ACTIONS:-}" = "true" ] || \
   [ "${GITLAB_CI:-}" = "true" ] || [ "${JENKINS_URL:-}" != "" ] || \
   [ "${TRAVIS:-}" = "true" ] || [ "${CIRCLECI:-}" = "true" ]; then
    exit 0
fi

# Reentrancy protection
LOCK_FILE=".git/kurt-hook.lock"
LOCK_TIMEOUT=30

acquire_lock() {
    local start_time=$(date +%s)
    while true; do
        if mkdir "$LOCK_FILE" 2>/dev/null; then
            echo $$ > "$LOCK_FILE/pid"
            trap 'rm -rf "$LOCK_FILE"' EXIT
            return 0
        fi

        # Check if lock is stale
        if [ -f "$LOCK_FILE/pid" ]; then
            local pid=$(cat "$LOCK_FILE/pid" 2>/dev/null)
            if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
                # Stale lock - PID doesn't exist
                rm -rf "$LOCK_FILE"
                continue
            fi
        fi

        # Check timeout
        local elapsed=$(($(date +%s) - start_time))
        if [ $elapsed -ge $LOCK_TIMEOUT ]; then
            # Timeout - remove lock and proceed
            rm -rf "$LOCK_FILE"
            continue
        fi

        # Wait briefly and retry
        sleep 0.1
    done
}

# Check if kurt is initialized
if [ ! -f "kurt.config" ] && [ ! -f ".kurt/config" ]; then
    echo "Warning: Kurt not initialized. Run 'kurt init' to enable Git+Dolt sync." >&2
    exit 0  # Allow git operation to proceed
fi

acquire_lock

'''

# Post-checkout hook: sync Dolt branch to match Git
POST_CHECKOUT_SCRIPT = HOOK_HEADER + '''
# post-checkout hook
# Arguments: $1=prev_HEAD, $2=new_HEAD, $3=branch_flag (1=branch, 0=file)

# Only run for branch checkouts
if [ "$3" != "1" ]; then
    exit 0
fi

# Sync Dolt to match Git branch
if kurt _internal sync-dolt-branch 2>&1; then
    exit 0
else
    echo "Error: Failed to sync Dolt branch. Run 'kurt doctor' for diagnostics." >&2
    exit 1
fi
'''

# Post-commit hook: commit Dolt changes with same message
POST_COMMIT_SCRIPT = HOOK_HEADER + '''
# post-commit hook
# No arguments

# Get the last commit message (short form)
GIT_COMMIT_SHORT=$(git rev-parse --short HEAD)
GIT_COMMIT_MSG=$(git log -1 --format=%s)

# Commit Dolt changes
if kurt _internal commit-dolt --message="Auto-sync: ${GIT_COMMIT_SHORT} - ${GIT_COMMIT_MSG}" 2>&1; then
    exit 0
else
    echo "Error: Failed to commit Dolt changes. Run 'kurt doctor' for diagnostics." >&2
    exit 1
fi
'''

# Pre-push hook: verify Dolt is in sync
PRE_PUSH_SCRIPT = HOOK_HEADER + '''
# pre-push hook
# Arguments: $1=remote_name, $2=remote_url

# Push Dolt changes
if kurt _internal push-dolt 2>&1; then
    exit 0
else
    echo "Error: Failed to push Dolt changes. Run 'kurt doctor' for diagnostics." >&2
    exit 1
fi
'''

# Prepare-commit-msg hook: block git merge
PREPARE_COMMIT_MSG_SCRIPT = HOOK_HEADER + '''
# prepare-commit-msg hook
# Arguments: $1=commit_msg_file, $2=commit_source (message/template/merge/squash/commit), $3=commit_sha

COMMIT_SOURCE="${2:-}"

# Block merge commits - require 'kurt merge' instead
if [ "$COMMIT_SOURCE" = "merge" ]; then
    echo "Error: Direct git merge is not supported with Kurt." >&2
    echo "Use 'kurt merge <branch>' to merge with Git+Dolt synchronization." >&2
    exit 1
fi

exit 0
'''

# Map hook names to their scripts
HOOK_SCRIPTS = {
    "post-checkout": POST_CHECKOUT_SCRIPT,
    "post-commit": POST_COMMIT_SCRIPT,
    "pre-push": PRE_PUSH_SCRIPT,
    "prepare-commit-msg": PREPARE_COMMIT_MSG_SCRIPT,
}


# =============================================================================
# Public API
# =============================================================================


def install_hooks(
    repo_path: Path | str,
    force: bool = False,
) -> HookInstallResult:
    """Install Git hooks for auto-sync.

    Creates executable shell scripts in .git/hooks/ that call kurt CLI
    commands to keep Git and Dolt in sync.

    Args:
        repo_path: Path to the Git repository root.
        force: If True, overwrite existing hooks without backup.

    Returns:
        HookInstallResult with lists of installed, backed up, skipped, and errored hooks.

    Raises:
        ValueError: If repo_path is not a Git repository.
    """
    repo_path = Path(repo_path).resolve()
    hooks_dir = repo_path / ".git" / "hooks"

    # Check for bare repo first (no .git directory, repo IS the git dir)
    if _is_bare_repo(repo_path):
        logger.warning("Hooks not installed: bare repository")
        return HookInstallResult(
            installed=[],
            backed_up=[],
            skipped=HOOK_NAMES.copy(),
            errors=["Bare repository - hooks not applicable"],
        )

    # Check for worktree (.git is a file, not a directory)
    if _is_worktree(repo_path):
        logger.warning("Hooks not installed: Git worktree")
        return HookInstallResult(
            installed=[],
            backed_up=[],
            skipped=HOOK_NAMES.copy(),
            errors=["Git worktree - install hooks in main repository"],
        )

    # Validate Git repository (must be a normal repo with .git directory)
    if not (repo_path / ".git").is_dir():
        raise ValueError(f"Not a Git repository: {repo_path}")

    # Create hooks directory if it doesn't exist
    hooks_dir.mkdir(parents=True, exist_ok=True)

    result = HookInstallResult(
        installed=[],
        backed_up=[],
        skipped=[],
        errors=[],
    )

    for hook_name in HOOK_NAMES:
        hook_path = hooks_dir / hook_name
        script = HOOK_SCRIPTS[hook_name]

        try:
            # Check if hook already exists
            if hook_path.exists():
                # Check if it's a Kurt hook
                if _is_kurt_hook(hook_path):
                    # Overwrite Kurt hook
                    hook_path.write_text(script)
                    _make_executable(hook_path)
                    result.installed.append(hook_name)
                elif force:
                    # Backup existing hook
                    backup_path = hooks_dir / f"{hook_name}.pre-kurt"
                    hook_path.rename(backup_path)
                    result.backed_up.append(hook_name)
                    # Install new hook
                    hook_path.write_text(script)
                    _make_executable(hook_path)
                    result.installed.append(hook_name)
                else:
                    # Skip - existing non-Kurt hook
                    result.skipped.append(hook_name)
                    logger.info(
                        f"Skipped {hook_name}: existing hook found. "
                        f"Use --force to overwrite."
                    )
            else:
                # Install new hook
                hook_path.write_text(script)
                _make_executable(hook_path)
                result.installed.append(hook_name)

        except OSError as e:
            result.errors.append(f"{hook_name}: {e}")
            logger.error(f"Failed to install {hook_name}: {e}")

    logger.info(f"Installed hooks: {result.installed}")
    return result


def uninstall_hooks(
    repo_path: Path | str,
) -> HookUninstallResult:
    """Remove Git hooks installed by Kurt.

    Only removes hooks that were installed by Kurt (identified by header).
    Restores any backed up hooks (.pre-kurt).

    Args:
        repo_path: Path to the Git repository root.

    Returns:
        HookUninstallResult with lists of removed, restored, not found, and errored hooks.

    Raises:
        ValueError: If repo_path is not a Git repository.
    """
    repo_path = Path(repo_path).resolve()
    hooks_dir = repo_path / ".git" / "hooks"

    # Validate Git repository
    if not (repo_path / ".git").is_dir():
        raise ValueError(f"Not a Git repository: {repo_path}")

    result = HookUninstallResult(
        removed=[],
        restored=[],
        not_found=[],
        errors=[],
    )

    for hook_name in HOOK_NAMES:
        hook_path = hooks_dir / hook_name
        backup_path = hooks_dir / f"{hook_name}.pre-kurt"

        try:
            if not hook_path.exists():
                result.not_found.append(hook_name)
                continue

            # Only remove Kurt hooks
            if not _is_kurt_hook(hook_path):
                result.not_found.append(hook_name)
                logger.info(f"Skipped {hook_name}: not a Kurt hook")
                continue

            # Remove the hook
            hook_path.unlink()
            result.removed.append(hook_name)

            # Restore backup if exists
            if backup_path.exists():
                backup_path.rename(hook_path)
                result.restored.append(hook_name)

        except OSError as e:
            result.errors.append(f"{hook_name}: {e}")
            logger.error(f"Failed to uninstall {hook_name}: {e}")

    logger.info(f"Removed hooks: {result.removed}")
    return result


def get_installed_hooks(repo_path: Path | str) -> list[str]:
    """Get list of Kurt hooks installed in a repository.

    Args:
        repo_path: Path to the Git repository root.

    Returns:
        List of hook names that are installed and are Kurt hooks.
    """
    repo_path = Path(repo_path).resolve()
    hooks_dir = repo_path / ".git" / "hooks"

    if not hooks_dir.is_dir():
        return []

    installed = []
    for hook_name in HOOK_NAMES:
        hook_path = hooks_dir / hook_name
        if hook_path.exists() and _is_kurt_hook(hook_path):
            installed.append(hook_name)

    return installed


def hooks_need_update(repo_path: Path | str) -> list[str]:
    """Check if any installed hooks need updating.

    Compares installed hook content with current templates.

    Args:
        repo_path: Path to the Git repository root.

    Returns:
        List of hook names that need updating.
    """
    repo_path = Path(repo_path).resolve()
    hooks_dir = repo_path / ".git" / "hooks"

    if not hooks_dir.is_dir():
        return []

    needs_update = []
    for hook_name in HOOK_NAMES:
        hook_path = hooks_dir / hook_name
        if not hook_path.exists():
            needs_update.append(hook_name)
            continue

        if not _is_kurt_hook(hook_path):
            continue

        # Compare content
        current = hook_path.read_text()
        expected = HOOK_SCRIPTS[hook_name]
        if current.strip() != expected.strip():
            needs_update.append(hook_name)

    return needs_update


# =============================================================================
# Helper Functions
# =============================================================================


def _is_kurt_hook(hook_path: Path) -> bool:
    """Check if a hook file was installed by Kurt."""
    try:
        content = hook_path.read_text()
        return "Kurt Git Hook" in content
    except OSError:
        return False


def _make_executable(path: Path) -> None:
    """Make a file executable."""
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _is_bare_repo(repo_path: Path) -> bool:
    """Check if the repository is a bare repository."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--is-bare-repository"],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() == "true"
    except subprocess.CalledProcessError:
        return False


def _is_worktree(repo_path: Path) -> bool:
    """Check if the repository is a Git worktree (not the main repo)."""
    git_dir = repo_path / ".git"
    # Worktrees have .git as a file pointing to the real git dir
    if git_dir.is_file():
        return True
    return False


# =============================================================================
# Exported Symbols
# =============================================================================

__all__ = [
    "install_hooks",
    "uninstall_hooks",
    "get_installed_hooks",
    "hooks_need_update",
    "HookInstallResult",
    "HookUninstallResult",
    "HookExitCode",
    "HOOK_NAMES",
]

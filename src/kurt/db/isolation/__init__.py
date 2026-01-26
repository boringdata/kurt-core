"""Git+Dolt isolation layer for branch synchronization and hooks.

This module provides utilities for keeping Git and Dolt branches in sync,
as well as merge and remote operations.
"""

# Branch operations
from .branch import (
    BranchStatus,
    BranchSyncError,
    BranchSyncErrorCode,
    BranchSyncResult,
    create_both,
    delete_both,
    list_branches,
    switch_both,
    sync_to_dolt,
    sync_to_git,
)

# Hooks
from .hooks import HOOK_NAMES, get_installed_hooks, install_hooks

# Merge operations
from .merge import (
    DoltConflict,
    MergeConflict,
    MergeError,
    MergeErrorCode,
    MergeExitCode,
    MergeResult,
    abort_merge,
    check_conflicts,
    merge_branch,
)

# Remote operations
from .remote import (
    DoltResult,
    GitResult,
    RemoteError,
    RemoteErrorCode,
    pull,
    push,
)

__all__ = [
    # Branch
    "BranchStatus",
    "BranchSyncError",
    "BranchSyncErrorCode",
    "BranchSyncResult",
    "create_both",
    "delete_both",
    "list_branches",
    "switch_both",
    "sync_to_dolt",
    "sync_to_git",
    # Hooks
    "HOOK_NAMES",
    "get_installed_hooks",
    "install_hooks",
    # Merge
    "DoltConflict",
    "MergeConflict",
    "MergeError",
    "MergeErrorCode",
    "MergeExitCode",
    "MergeResult",
    "abort_merge",
    "check_conflicts",
    "merge_branch",
    # Remote
    "DoltResult",
    "GitResult",
    "RemoteError",
    "RemoteErrorCode",
    "pull",
    "push",
]

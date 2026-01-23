"""Git+Dolt isolation layer for branch synchronization, merge, and remote operations.

This module provides utilities for keeping Git and Dolt branches in sync,
enabling isolated development environments where code (Git) and data (Dolt)
stay on the same branch.

Branch synchronization:
- sync_to_git: Sync Dolt to match the current Git branch
- sync_to_dolt: Sync Git to match the current Dolt branch
- create_both: Create a branch in both Git and Dolt atomically

Git hooks:
- install_hooks: Install Git hooks for auto-sync
- uninstall_hooks: Remove Kurt Git hooks
- get_installed_hooks: List installed Kurt hooks
- hooks_need_update: Check if hooks need updating

Merge operations:
- merge_branch: Merge a branch in both Git and Dolt
- check_conflicts: Check for conflicts before merging
- abort_merge: Abort an in-progress merge

Remote operations:
- pull: Pull changes from Git and Dolt remotes
- push: Push changes to Git and Dolt remotes
"""

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
from .hooks import (
    HOOK_NAMES,
    HookExitCode,
    HookInstallResult,
    HookUninstallResult,
    get_installed_hooks,
    hooks_need_update,
    install_hooks,
    uninstall_hooks,
)
from .remote import (
    DoltResult,
    GitResult,
    PullResult,
    PushResult,
    RemoteError,
    RemoteErrorCode,
    pull,
    push,
)

__all__ = [
    # Branch sync
    "BranchStatus",
    "BranchSyncResult",
    "BranchSyncError",
    "BranchSyncErrorCode",
    "sync_to_git",
    "sync_to_dolt",
    "create_both",
    "switch_both",
    "delete_both",
    "list_branches",
    # Hooks
    "install_hooks",
    "uninstall_hooks",
    "get_installed_hooks",
    "hooks_need_update",
    "HookInstallResult",
    "HookUninstallResult",
    "HookExitCode",
    "HOOK_NAMES",
    # Merge
    "MergeResult",
    "MergeConflict",
    "DoltConflict",
    "MergeError",
    "MergeErrorCode",
    "MergeExitCode",
    "merge_branch",
    "check_conflicts",
    "abort_merge",
    # Remote
    "PullResult",
    "PushResult",
    "GitResult",
    "DoltResult",
    "RemoteError",
    "RemoteErrorCode",
    "pull",
    "push",
]

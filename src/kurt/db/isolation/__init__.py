"""Git+Dolt isolation layer for branch synchronization and hooks.

This module provides utilities for keeping Git and Dolt branches in sync.

Used exports:
- sync_to_git: Sync Dolt to match the current Git branch
- install_hooks: Install Git hooks for auto-sync
- get_installed_hooks: List installed Kurt hooks
- HOOK_NAMES: List of hook names managed by Kurt
"""

from .branch import sync_to_git
from .hooks import HOOK_NAMES, get_installed_hooks, install_hooks

__all__ = [
    "sync_to_git",
    "install_hooks",
    "get_installed_hooks",
    "HOOK_NAMES",
]

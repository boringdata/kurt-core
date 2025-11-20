"""
Kurt update system for managing plugin file updates.

This module handles updating Kurt's plugin files (.claude/, .cursor/, kurt/)
when the package is upgraded, with smart detection and merging capabilities.
"""

from .orchestrator import update_files  # noqa: F401

__all__ = ["update_files"]

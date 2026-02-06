"""
Write-db tool configuration.

Config values can be set in kurt.config with WRITE_DB.* prefix:

    WRITE_DB.MODE=upsert
    WRITE_DB.CONTINUE_ON_ERROR=true

Usage:
    # Load from config file
    config = WriteToolConfig.from_config("write-db")

    # Or instantiate directly
    config = WriteToolConfig(mode="replace")

    # Or merge: config file + CLI overrides
    config = WriteToolConfig.from_config("write-db", continue_on_error=True)
"""

from __future__ import annotations

from typing import Literal

from kurt.config import ConfigParam, StepConfig


class WriteToolConfig(StepConfig):
    """Configuration for database write tool.

    Loaded from kurt.config with WRITE_DB.* prefix.
    Note: Named WriteToolConfig to avoid conflict with WriteConfig in __init__.py.
    """

    # Write settings
    mode: Literal["insert", "upsert", "replace"] = ConfigParam(
        default="insert",
        description="Write mode: 'insert', 'upsert', or 'replace'",
    )
    continue_on_error: bool = ConfigParam(
        default=False,
        description="If True, continue processing after individual row errors",
    )

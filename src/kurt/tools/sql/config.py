"""
SQL tool configuration.

Config values can be set in kurt.config with SQL.* prefix:

    SQL.TIMEOUT_MS=30000

Usage:
    # Load from config file
    config = SQLToolConfig.from_config("sql")

    # Or instantiate directly
    config = SQLToolConfig(timeout_ms=60000)

    # Or merge: config file + CLI overrides
    config = SQLToolConfig.from_config("sql", timeout_ms=10000)
"""

from __future__ import annotations

from kurt.config import ConfigParam, StepConfig


class SQLToolConfig(StepConfig):
    """Configuration for SQL query tool.

    Loaded from kurt.config with SQL.* prefix.
    Note: Named SQLToolConfig to avoid conflict with SQLConfig in __init__.py.
    """

    # Query settings
    timeout_ms: int = ConfigParam(
        default=30000,
        ge=1000,
        le=300000,
        description="Query timeout in milliseconds",
    )

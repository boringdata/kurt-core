"""
Signals tool configuration.

Config values can be set in kurt.config with SIGNALS.* prefix:

    SIGNALS.TIMEFRAME=week
    SIGNALS.LIMIT=50
    SIGNALS.MIN_SCORE=10

Usage:
    # Load from config file
    config = SignalsConfig.from_config("signals")

    # Or instantiate directly
    config = SignalsConfig(limit=100)

    # Or merge: config file + CLI overrides
    config = SignalsConfig.from_config("signals", timeframe="month")
"""

from __future__ import annotations

from typing import Literal

from kurt.config import ConfigParam, StepConfig


class SignalsConfig(StepConfig):
    """Configuration for signals monitoring tool.

    Loaded from kurt.config with SIGNALS.* prefix.
    """

    # Timeframe and limits
    timeframe: Literal["hour", "day", "week", "month"] = ConfigParam(
        default="day",
        description="Time filter for results",
    )
    limit: int = ConfigParam(
        default=25,
        ge=1,
        le=100,
        description="Maximum number of results",
    )
    min_score: int = ConfigParam(
        default=0,
        ge=0,
        description="Minimum score threshold",
    )

    # Reddit-specific
    sort: Literal["hot", "new", "top", "rising"] = ConfigParam(
        default="hot",
        description="Sort order for Reddit",
    )

    # Runtime flags (CLI only, not loaded from config file)
    dry_run: bool = False  # Preview mode - don't persist to database

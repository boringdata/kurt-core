"""
Analytics tool configuration.

Config values can be set in kurt.config with ANALYTICS.* prefix:

    ANALYTICS.PLATFORM=posthog
    ANALYTICS.PERIOD_DAYS=60

Usage:
    # Load from config file
    config = AnalyticsConfig.from_config("analytics")

    # Or instantiate directly
    config = AnalyticsConfig(period_days=90)

    # Or merge: config file + CLI overrides
    config = AnalyticsConfig.from_config("analytics", platform="plausible")
"""

from __future__ import annotations

from typing import Literal

from kurt.config import ConfigParam, StepConfig


class AnalyticsConfig(StepConfig):
    """Configuration for analytics sync tool.

    Loaded from kurt.config with ANALYTICS.* prefix.
    """

    # Analytics settings
    platform: Literal["posthog", "ga4", "plausible"] = ConfigParam(
        default="posthog",
        description="Analytics platform to use",
    )
    period_days: int = ConfigParam(
        default=60,
        ge=1,
        le=365,
        description="Days of data to fetch",
    )

    # Runtime flags (CLI only, not loaded from config file)
    dry_run: bool = False  # Preview mode - fetch but don't persist

"""
Domain analytics workflow configuration.

Config values can be set in kurt.config with ANALYTICS_<PLATFORM>_<KEY> format:

    ANALYTICS_POSTHOG_PROJECT_ID=12345
    ANALYTICS_POSTHOG_API_KEY=phx_xxx

Usage:
    # Load from config file
    config = DomainAnalyticsConfig.from_config("domain_analytics")

    # Or instantiate directly
    config = DomainAnalyticsConfig(domain="example.com", platform="posthog")

    # Or merge: config file + overrides
    config = DomainAnalyticsConfig.from_config("domain_analytics", domain="example.com")
"""

from __future__ import annotations

from kurt.config import ConfigParam, StepConfig


class DomainAnalyticsConfig(StepConfig):
    """Configuration for domain analytics workflow.

    Loaded from kurt.config with DOMAIN_ANALYTICS.* prefix for workflow settings,
    and ANALYTICS_<PLATFORM>_* prefix for platform credentials.
    """

    # Required: domain to sync
    domain: str = ConfigParam(description="Domain to sync analytics for (e.g., 'example.com')")

    # Platform settings
    platform: str = ConfigParam(
        default="posthog", description="Analytics platform (posthog, ga4, plausible)"
    )

    # Sync settings
    period_days: int = ConfigParam(default=60, ge=1, le=365, description="Days of data to fetch")

    # Runtime flags (CLI only, not loaded from config file)
    dry_run: bool = False  # Preview mode - fetch but don't persist

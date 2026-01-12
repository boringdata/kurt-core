"""Domain analytics integration package for Kurt."""

from typing import Any, Dict

from kurt.integrations.domains_analytics.base import AnalyticsAdapter, AnalyticsMetrics
from kurt.integrations.domains_analytics.fetch import (
    get_domain_urls,
    sync_domain_metrics,
    test_platform_connection,
)


def get_adapter(platform: str, config: Dict[str, Any]) -> AnalyticsAdapter:
    """
    Get analytics adapter instance for specified platform.

    Args:
        platform: Analytics platform name (posthog, ga4, plausible)
        config: Platform configuration dictionary

    Returns:
        Initialized analytics adapter instance

    Raises:
        ValueError: If platform is not supported
    """
    if platform == "posthog":
        from kurt.integrations.domains_analytics.posthog.adapter import PostHogAdapter

        return PostHogAdapter(config)
    elif platform == "ga4":
        raise NotImplementedError("GA4 adapter coming soon")
    elif platform == "plausible":
        raise NotImplementedError("Plausible adapter coming soon")
    else:
        raise ValueError(
            f"Unsupported analytics platform: {platform}. "
            f"Supported platforms: posthog, ga4 (coming soon), plausible (coming soon)"
        )


__all__ = [
    "AnalyticsAdapter",
    "AnalyticsMetrics",
    "get_adapter",
    "sync_domain_metrics",
    "get_domain_urls",
    "test_platform_connection",
]

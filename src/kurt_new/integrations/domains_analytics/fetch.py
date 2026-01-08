"""
Domain analytics fetching business logic.

This module provides business logic for fetching analytics from platforms.
NO DATABASE OPERATIONS - pure API calls.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kurt_new.integrations.domains_analytics.base import AnalyticsMetrics

logger = logging.getLogger(__name__)


def _get_adapter(platform: str, config: dict):
    """Get adapter - late import to avoid circular imports."""
    if platform == "posthog":
        from kurt_new.integrations.domains_analytics.posthog.adapter import PostHogAdapter

        return PostHogAdapter(config)
    elif platform == "ga4":
        raise NotImplementedError("GA4 adapter coming soon")
    elif platform == "plausible":
        raise NotImplementedError("Plausible adapter coming soon")
    else:
        raise ValueError(f"Unsupported analytics platform: {platform}")


def _get_platform_config(platform: str) -> dict:
    """Get platform config - late import to avoid circular imports."""
    from kurt_new.integrations.domains_analytics.config import get_platform_config

    return get_platform_config(platform)


def sync_domain_metrics(
    platform: str,
    domain: str,
    period_days: int = 60,
) -> dict[str, "AnalyticsMetrics"]:
    """
    Sync analytics metrics for a domain from the specified platform.

    Pure business logic - calls analytics API, no DB operations.
    Workflows call this function and handle DB operations separately.

    Args:
        platform: Analytics platform name (e.g., 'posthog', 'ga4')
        domain: Domain to fetch metrics for (e.g., 'example.com')
        period_days: Number of days of data to fetch (default: 60)

    Returns:
        Dict mapping URL -> AnalyticsMetrics

    Raises:
        ValueError: If platform not configured or sync fails

    Example:
        >>> metrics = sync_domain_metrics("posthog", "example.com", period_days=30)
        >>> for url, m in metrics.items():
        ...     print(f"{url}: {m.pageviews_30d} pageviews")
    """
    try:
        # Get platform config and adapter
        platform_config = _get_platform_config(platform)
        adapter = _get_adapter(platform, platform_config)

        logger.info(f"[Analytics] Syncing {domain} from {platform} ({period_days} days)")

        # Fetch URLs for domain
        urls = adapter.get_domain_urls(domain, period_days=period_days)

        if not urls:
            logger.info(f"[Analytics] No URLs found for {domain}")
            return {}

        logger.info(f"[Analytics] Found {len(urls)} URLs for {domain}")

        # Fetch metrics for all URLs
        metrics_map = adapter.sync_metrics(urls, period_days=period_days)

        total_pageviews = sum(m.pageviews_60d for m in metrics_map.values())
        logger.info(
            f"[Analytics] Synced {len(metrics_map)} URLs, {total_pageviews} total pageviews"
        )

        return metrics_map

    except Exception as e:
        raise ValueError(f"Failed to sync analytics from {platform} for {domain}: {e}")


def get_domain_urls(
    platform: str,
    domain: str,
    period_days: int = 60,
) -> list[str]:
    """
    Get all URLs for a domain from the analytics platform.

    Pure business logic - calls analytics API, no DB operations.

    Args:
        platform: Analytics platform name
        domain: Domain to fetch URLs for
        period_days: Number of days to query

    Returns:
        List of unique URLs found in analytics for this domain

    Example:
        >>> urls = get_domain_urls("posthog", "example.com")
        >>> print(f"Found {len(urls)} URLs")
    """
    try:
        platform_config = _get_platform_config(platform)
        adapter = _get_adapter(platform, platform_config)

        return adapter.get_domain_urls(domain, period_days=period_days)

    except Exception as e:
        raise ValueError(f"Failed to get URLs from {platform} for {domain}: {e}")


def test_platform_connection(platform: str) -> bool:
    """
    Test connection to an analytics platform.

    Args:
        platform: Analytics platform name

    Returns:
        True if connection successful

    Raises:
        ConnectionError: If connection fails with details
        ValueError: If platform not configured
    """
    platform_config = _get_platform_config(platform)
    adapter = _get_adapter(platform, platform_config)

    return adapter.test_connection()


__all__ = [
    "sync_domain_metrics",
    "get_domain_urls",
    "test_platform_connection",
]

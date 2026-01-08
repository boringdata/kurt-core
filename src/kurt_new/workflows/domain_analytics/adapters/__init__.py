"""Analytics adapters for different platforms."""

from kurt_new.workflows.domain_analytics.adapters.base import AnalyticsAdapter, AnalyticsMetrics


def get_adapter(platform: str, config: dict) -> AnalyticsAdapter:
    """
    Get analytics adapter instance for specified platform.

    Args:
        platform: Analytics platform name (e.g., 'posthog', 'ga4', 'plausible')
        config: Platform-specific configuration dictionary

    Returns:
        Initialized analytics adapter

    Raises:
        ValueError: If platform is not supported
        KeyError: If required config keys are missing
    """
    if platform == "posthog":
        from kurt_new.workflows.domain_analytics.adapters.posthog import PostHogAdapter

        return PostHogAdapter(
            project_id=config["project_id"],
            api_key=config["api_key"],
            base_url=config.get("host", "https://app.posthog.com"),
        )
    elif platform == "ga4":
        raise NotImplementedError("GA4 adapter not yet implemented")
    elif platform == "plausible":
        raise NotImplementedError("Plausible adapter not yet implemented")
    else:
        raise ValueError(f"Unsupported analytics platform: {platform}")


__all__ = [
    "AnalyticsAdapter",
    "AnalyticsMetrics",
    "get_adapter",
]

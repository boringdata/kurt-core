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

from typing import Dict

from kurt_new.config import (
    ConfigParam,
    StepConfig,
    config_exists_for_prefix,
    get_nested_value,
    has_placeholder_values,
    load_prefixed_config,
    save_prefixed_config,
)

# Analytics configs have 1 level: PLATFORM
# Format: ANALYTICS_<PLATFORM>_<KEY>
_PREFIX = "ANALYTICS"
_LEVELS = 1


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

    # Behavior
    dry_run: bool = ConfigParam(default=False, description="Dry run mode - fetch but don't persist")


# Platform configuration helpers


def load_analytics_config() -> Dict[str, Dict[str, str]]:
    """
    Load analytics configuration from kurt.config.

    Returns analytics configurations organized by provider:
    {
      "posthog": {
        "project_id": "12345",
        "api_key": "phx_xxx"
      },
      "ga4": {...}
    }

    Returns:
        Dictionary with analytics configurations organized by provider

    Raises:
        FileNotFoundError: If kurt.config doesn't exist
    """
    return load_prefixed_config(_PREFIX, _LEVELS)


def save_analytics_config(analytics_config: Dict[str, Dict[str, str]]) -> None:
    """
    Save analytics configuration to kurt.config.

    Args:
        analytics_config: Analytics configuration dictionary organized by provider
            Example: {"posthog": {"project_id": "12345", "api_key": "phx_xxx"}}
    """
    save_prefixed_config(_PREFIX, analytics_config, _LEVELS)


def get_platform_config(platform: str) -> Dict[str, str]:
    """
    Get configuration for a specific analytics platform.

    Args:
        platform: Analytics platform name (e.g., 'posthog', 'ga4', 'plausible')

    Returns:
        Platform-specific configuration dictionary

    Raises:
        ValueError: If platform not configured
    """
    config = load_analytics_config()

    if platform not in config:
        available = ", ".join(config.keys()) if config else "none configured"
        raise ValueError(
            f"No configuration found for analytics platform '{platform}'.\n"
            f"Available platforms: {available}\n"
            f"\n"
            f"To configure {platform}, add to kurt.config:\n"
            f"  ANALYTICS_{platform.upper()}_PROJECT_ID=your_project_id\n"
            f"  ANALYTICS_{platform.upper()}_API_KEY=your_api_key"
        )

    return config[platform]


def add_platform_config(platform: str, platform_config: Dict[str, str]) -> None:
    """
    Add or update configuration for an analytics platform.

    Args:
        platform: Analytics platform name (e.g., 'posthog', 'ga4', 'plausible')
        platform_config: Platform-specific configuration dictionary
            Example: {"project_id": "12345", "api_key": "phx_xxx"}
    """
    config = load_analytics_config()
    config[platform] = platform_config
    save_analytics_config(config)


def analytics_config_exists() -> bool:
    """Check if any analytics configuration exists in kurt.config."""
    return config_exists_for_prefix(_PREFIX, _LEVELS)


def create_template_config(platform: str) -> Dict[str, str]:
    """
    Get template configuration structure for an analytics platform.

    Args:
        platform: Analytics platform name (e.g., 'posthog', 'ga4', 'plausible')

    Returns:
        Template configuration dictionary with placeholder values
    """
    if platform == "posthog":
        return {
            "project_id": "YOUR_PROJECT_ID",
            "api_key": "YOUR_PERSONAL_API_KEY",
            "host": "https://app.posthog.com",
        }
    elif platform == "ga4":
        return {
            "property_id": "YOUR_PROPERTY_ID",
            "credentials_file": "path/to/credentials.json",
        }
    elif platform == "plausible":
        return {
            "site_id": "YOUR_SITE_ID",
            "api_key": "YOUR_API_KEY",
        }
    else:
        return {
            "api_key": "YOUR_API_KEY",
        }


def platform_configured(platform: str) -> bool:
    """
    Check if a specific platform is configured.

    Args:
        platform: Analytics platform name

    Returns:
        True if platform is configured and credentials look valid
    """
    try:
        config = load_analytics_config()
        platform_config = get_nested_value(config, [platform])

        if not platform_config:
            return False

        if has_placeholder_values(platform_config):
            return False

        return True
    except Exception:
        return False

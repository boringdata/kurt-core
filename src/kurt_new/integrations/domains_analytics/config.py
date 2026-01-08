"""
Domain analytics configuration management for Kurt.

Loads analytics credentials and settings from kurt.config file.
Analytics configs are stored with ANALYTICS_<PLATFORM>_<KEY> format.
Example: ANALYTICS_POSTHOG_PROJECT_ID=12345
"""

from typing import Any, Dict, List

from kurt_new.config import (
    get_nested_value,
    has_placeholder_values,
    load_prefixed_config,
    save_prefixed_config,
)

# Analytics configs have 1 level: PLATFORM
# Format: ANALYTICS_<PLATFORM>_<KEY>
_PREFIX = "ANALYTICS"
_LEVELS = 1


def load_analytics_config() -> Dict[str, Dict[str, Any]]:
    """
    Load analytics configuration from kurt.config.

    Returns analytics configurations organized by platform:
    {
      "posthog": {
        "project_id": "12345",
        "api_key": "phx_xxx",
        "host": "https://app.posthog.com"
      },
      "ga4": {...},
      "plausible": {...}
    }

    Returns:
        Dictionary with analytics configurations organized by platform

    Raises:
        FileNotFoundError: If kurt.config doesn't exist
    """
    return load_prefixed_config(_PREFIX, _LEVELS)


def save_analytics_config(analytics_config: Dict[str, Dict[str, Any]]) -> None:
    """
    Save analytics configuration to kurt.config.

    Args:
        analytics_config: Analytics configuration dictionary organized by platform
            Example: {"posthog": {"project_id": "12345", "api_key": "phx_xxx"}}
    """
    save_prefixed_config(_PREFIX, analytics_config, _LEVELS)


def get_platform_config(platform: str) -> Dict[str, Any]:
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


def add_platform_config(platform: str, platform_config: Dict[str, Any]) -> None:
    """
    Add or update configuration for an analytics platform.

    Args:
        platform: Analytics platform name (e.g., 'posthog', 'ga4', 'plausible')
        platform_config: Platform-specific configuration dictionary
            Example for PostHog: {"project_id": "12345", "api_key": "phx_xxx"}
    """
    config = load_analytics_config()
    config[platform] = platform_config
    save_analytics_config(config)


def create_template_config(platform: str) -> Dict[str, Any]:
    """
    Get template configuration structure for an analytics platform.

    Args:
        platform: Analytics platform name

    Returns:
        Template configuration dictionary with placeholder values
    """
    if platform == "posthog":
        template = {
            "project_id": "YOUR_PROJECT_ID",
            "api_key": "YOUR_PERSONAL_API_KEY",
            "host": "https://app.posthog.com",
        }
    elif platform == "ga4":
        template = {
            "property_id": "YOUR_PROPERTY_ID",
            "credentials_file": "path/to/credentials.json",
        }
    elif platform == "plausible":
        template = {
            "site_id": "YOUR_SITE_ID",
            "api_key": "YOUR_API_KEY",
        }
    else:
        template = {
            "api_key": "YOUR_API_KEY",
        }

    return template


def analytics_config_exists() -> bool:
    """Check if any analytics configuration exists in kurt.config."""
    from kurt_new.config import config_exists_for_prefix

    return config_exists_for_prefix(_PREFIX, _LEVELS)


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

        return not has_placeholder_values(platform_config)
    except Exception:
        return False


def list_platforms() -> List[str]:
    """
    List all configured analytics platforms.

    Returns:
        List of platform names

    Raises:
        FileNotFoundError: If kurt.config doesn't exist
    """
    config = load_analytics_config()
    return list(config.keys())

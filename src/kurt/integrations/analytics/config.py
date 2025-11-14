"""
Analytics configuration management for Kurt.

Loads analytics credentials and settings from kurt.config file.
Analytics provider configs are stored with ANALYTICS_<PROVIDER>_<KEY> format.
Example: ANALYTICS_POSTHOG_PROJECT_ID=phc_abc123
"""

from typing import Dict

from kurt.config import load_prefixed_config, save_prefixed_config

# Analytics configs have 1 level: PROVIDER
# Format: ANALYTICS_<PROVIDER>_<KEY>
_PREFIX = "ANALYTICS"
_LEVELS = 1


def load_analytics_config() -> Dict[str, Dict[str, str]]:
    """
    Load analytics configuration from kurt.config.

    Returns analytics configurations organized by provider:
    {
      "posthog": {
        "project_id": "phc_abc123",
        "api_key": "phx_xyz789"
      },
      "ga4": {
        "property_id": "123456789",
        "credentials_file": "path/to/credentials.json"
      }
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
            Example: {"posthog": {"project_id": "phc_123", "api_key": "phx_456"}}
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
            f"To configure {platform}, run:\n"
            f"  kurt integrations analytics onboard --platform {platform}"
        )

    return config[platform]


def add_platform_config(platform: str, platform_config: Dict[str, str]) -> None:
    """
    Add or update configuration for an analytics platform.

    Args:
        platform: Analytics platform name (e.g., 'posthog', 'ga4', 'plausible')
        platform_config: Platform-specific configuration dictionary
            Example: {"project_id": "phc_123", "api_key": "phx_456"}
    """
    # Load existing config
    config = load_analytics_config()

    # Add/update platform config
    config[platform] = platform_config

    # Save back to kurt.config
    save_analytics_config(config)


def analytics_config_exists() -> bool:
    """Check if any analytics configuration exists in kurt.config."""
    from kurt.config import config_exists_for_prefix

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
        from kurt.config import get_nested_value, has_placeholder_values

        config = load_analytics_config()
        platform_config = get_nested_value(config, [platform])

        if not platform_config:
            return False

        # Check for placeholder values
        if has_placeholder_values(platform_config):
            return False

        return True
    except Exception:
        return False

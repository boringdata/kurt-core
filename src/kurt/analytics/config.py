"""
Analytics configuration management for Kurt.

Loads analytics credentials and settings from kurt.config file.
Analytics provider configs are stored with ANALYTICS_<PROVIDER>_<KEY> format.
Example: ANALYTICS_POSTHOG_PROJECT_ID=phc_abc123
"""

from typing import Dict

from kurt.config import get_config_or_default, update_config


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
    config = get_config_or_default()

    # Extract analytics fields (ANALYTICS_<PROVIDER>_<KEY>)
    analytics_config: Dict[str, Dict[str, str]] = {}
    for key, value in config.__dict__.items():
        if key.startswith("ANALYTICS_"):
            # Parse ANALYTICS_POSTHOG_PROJECT_ID -> provider=posthog, key=project_id
            parts = key.split("_", 2)  # Split into [ANALYTICS, PROVIDER, KEY]
            if len(parts) == 3:
                _, provider, field = parts
                provider = provider.lower()
                field = field.lower()

                if provider not in analytics_config:
                    analytics_config[provider] = {}
                analytics_config[provider][field] = value

    return analytics_config


def save_analytics_config(analytics_config: Dict[str, Dict[str, str]]) -> None:
    """
    Save analytics configuration to kurt.config.

    Args:
        analytics_config: Analytics configuration dictionary organized by provider
            Example: {"posthog": {"project_id": "phc_123", "api_key": "phx_456"}}
    """
    config = get_config_or_default()

    # Convert provider configs to ANALYTICS_<PROVIDER>_<KEY> format
    # First, remove existing analytics fields
    for key in list(config.__dict__.keys()):
        if key.startswith("ANALYTICS_"):
            delattr(config, key)

    # Add new analytics fields
    for provider, provider_config in analytics_config.items():
        for key, value in provider_config.items():
            field_name = f"ANALYTICS_{provider.upper()}_{key.upper()}"
            setattr(config, field_name, value)

    update_config(config)


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
        available = ", ".join(config.keys()) if config else "none"
        raise ValueError(
            f"No configuration found for analytics platform '{platform}'.\n"
            f"Available platforms: {available}\n"
            f"Run 'kurt analytics onboard --platform {platform}' to configure."
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
    try:
        config = load_analytics_config()
        return len(config) > 0
    except Exception:
        return False


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
        if platform not in config:
            return False

        platform_config = config[platform]

        # Check for placeholder values
        import json

        config_str = json.dumps(platform_config)
        if "YOUR_" in config_str or "PLACEHOLDER" in config_str:
            return False

        return True
    except Exception:
        return False

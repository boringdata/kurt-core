"""
CMS configuration management for Kurt.

Loads CMS credentials and settings from kurt.config file.
CMS configs are stored with CMS_<PLATFORM>_<INSTANCE>_<KEY> format.
Example: CMS_SANITY_PROD_PROJECT_ID=abc123
"""

from typing import Any, Dict, List, Optional

from kurt.config import (
    get_nested_value,
    has_placeholder_values,
    load_prefixed_config,
    save_prefixed_config,
)

# CMS configs have 2 levels: PLATFORM and INSTANCE
# Format: CMS_<PLATFORM>_<INSTANCE>_<KEY>
_PREFIX = "CMS"
_LEVELS = 2


def load_cms_config() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Load CMS configuration from kurt.config.

    Returns CMS configurations organized by platform and instance:
    {
      "sanity": {
        "prod": {
          "project_id": "abc123",
          "dataset": "production",
          "token": "sk...",
          "write_token": "sk...",
          "base_url": "https://example.com",
          "content_type_mappings": {...}
        },
        "staging": {...}
      },
      "contentful": {...}
    }

    Returns:
        Dictionary with CMS configurations organized by platform and instance

    Raises:
        FileNotFoundError: If kurt.config doesn't exist
    """
    return load_prefixed_config(_PREFIX, _LEVELS)


def save_cms_config(cms_config: Dict[str, Dict[str, Dict[str, Any]]]) -> None:
    """
    Save CMS configuration to kurt.config.

    Args:
        cms_config: CMS configuration dictionary organized by platform and instance
            Example: {"sanity": {"prod": {"project_id": "abc123", "token": "sk_..."}}}
    """
    save_prefixed_config(_PREFIX, cms_config, _LEVELS)


def get_platform_config(platform: str, instance: Optional[str] = None) -> Dict[str, Any]:
    """
    Get configuration for a specific CMS platform and instance.

    New structure always uses named instances: {"sanity": {"prod": {...}, "staging": {...}}}

    Args:
        platform: CMS platform name (e.g., 'sanity', 'contentful', 'wordpress')
        instance: Instance name (e.g., 'prod', 'staging'). If not provided, uses 'default' or first available.

    Returns:
        Platform-specific configuration dictionary

    Raises:
        ValueError: If platform not configured or instance not found
    """
    config = load_cms_config()

    if platform not in config:
        available = ", ".join(config.keys()) if config else "none configured"
        raise ValueError(
            f"No configuration found for CMS platform '{platform}'.\n"
            f"Available platforms: {available}\n"
            f"\n"
            f"To configure {platform}, run:\n"
            f"  kurt integrations cms onboard --platform {platform}"
        )

    platform_config = config[platform]

    # Named instances structure
    if instance:
        if instance not in platform_config:
            available = ", ".join(platform_config.keys())
            raise ValueError(
                f"Instance '{instance}' not found for platform '{platform}'.\n"
                f"Available instances: {available}\n"
                f"\n"
                f"To add this instance, run:\n"
                f"  kurt cms onboard --platform {platform} --instance {instance}"
            )
        return platform_config[instance]

    # No instance specified - return default or first instance
    if "default" in platform_config:
        return platform_config["default"]

    # Return first instance
    instances = list(platform_config.keys())
    if not instances:
        raise ValueError(f"No instances configured for platform '{platform}'")

    return platform_config[instances[0]]


def add_platform_instance(platform: str, instance: str, instance_config: Dict[str, Any]) -> None:
    """
    Add or update configuration for a CMS platform instance.

    Args:
        platform: CMS platform name (e.g., 'sanity', 'contentful', 'wordpress')
        instance: Instance name (e.g., 'prod', 'staging', 'default')
        instance_config: Platform-specific configuration dictionary
            Example for Sanity: {"project_id": "abc123", "dataset": "production", "token": "sk_..."}
    """
    # Load existing config
    cms_config = load_cms_config()

    # Add/update platform instance config
    if platform not in cms_config:
        cms_config[platform] = {}

    cms_config[platform][instance] = instance_config

    # Save back to kurt.config
    save_cms_config(cms_config)


def create_template_config(platform: str, instance: str = "default") -> Dict[str, Any]:
    """
    Get template configuration structure for a CMS platform.

    Args:
        platform: CMS platform name
        instance: Instance name (default: "default")

    Returns:
        Template configuration dictionary with placeholder values
    """
    # Platform-specific templates
    if platform == "sanity":
        template = {
            "project_id": "YOUR_PROJECT_ID",
            "dataset": "production",
            "token": "YOUR_READ_TOKEN",
            "write_token": "YOUR_WRITE_TOKEN",
            "base_url": "https://yoursite.com",
        }
    elif platform == "contentful":
        template = {
            "space_id": "YOUR_SPACE_ID",
            "access_token": "YOUR_ACCESS_TOKEN",
            "environment": "master",
        }
    elif platform == "wordpress":
        template = {
            "site_url": "https://yoursite.com",
            "username": "YOUR_USERNAME",
            "app_password": "YOUR_APP_PASSWORD",
        }
    else:
        template = {}

    return template


def cms_config_exists() -> bool:
    """Check if any CMS configuration exists in kurt.config."""
    from kurt.config import config_exists_for_prefix

    return config_exists_for_prefix(_PREFIX, _LEVELS)


def platform_configured(platform: str, instance: Optional[str] = None) -> bool:
    """
    Check if a specific platform (and optionally instance) is configured.

    Args:
        platform: CMS platform name
        instance: Optional instance name to check

    Returns:
        True if platform/instance is configured and credentials look valid
    """
    try:
        config = load_cms_config()

        # Check if platform exists
        if instance:
            # Check specific instance
            instance_config = get_nested_value(config, [platform, instance])
            if not instance_config:
                return False
        else:
            # Check if ANY instance is configured for this platform
            platform_config = get_nested_value(config, [platform])
            if not platform_config or not isinstance(platform_config, dict):
                return False
            # Get first instance config
            instance_config = list(platform_config.values())[0]

        # Check for placeholder values
        return not has_placeholder_values(instance_config)
    except Exception:
        return False


def list_platform_instances(platform: str) -> List[str]:
    """
    List all instances for a platform.

    Args:
        platform: CMS platform name

    Returns:
        List of instance names

    Raises:
        ValueError: If platform not configured
    """
    config = load_cms_config()

    if platform not in config:
        raise ValueError(
            f"No configuration found for CMS platform '{platform}'.\n"
            f"Available platforms: {', '.join(config.keys())}"
        )

    platform_config = config[platform]
    return list(platform_config.keys())

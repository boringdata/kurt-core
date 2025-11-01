"""
CMS configuration management for Kurt.

Loads CMS credentials and settings from .kurt/cms-config.json in the project directory.
This file stores sensitive CMS API tokens and should be gitignored.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from kurt.config import load_config


def get_cms_config_path() -> Path:
    """
    Get the path to the CMS configuration file.

    Returns:
        Path to .kurt/cms-config.json in the Kurt project directory
    """
    project_config = load_config()
    kurt_dir = project_config.get_db_directory()
    return kurt_dir / "cms-config.json"


def load_cms_config() -> Dict[str, Any]:
    """
    Load CMS configuration from .kurt/cms-config.json.

    The config file format:
    {
      "sanity": {
        "project_id": "abc123",
        "dataset": "production",
        "token": "sk...",
        "write_token": "sk...",
        "base_url": "https://example.com",
        "content_type_mappings": {...}
      },
      "contentful": {...},
      "wordpress": {...}
    }

    Returns:
        Dictionary with CMS configurations

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid JSON
    """
    config_path = get_cms_config_path()

    if not config_path.exists():
        raise FileNotFoundError(
            f"CMS configuration file not found: {config_path}\n"
            f"Create this file with your CMS credentials.\n"
            f"Run 'kurt cms onboard' to set up CMS integration."
        )

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in CMS config file: {config_path}\n{e}")

    return config


def save_cms_config(config: Dict[str, Any]) -> None:
    """
    Save CMS configuration to .kurt/cms-config.json.

    Args:
        config: CMS configuration dictionary
    """
    config_path = get_cms_config_path()

    # Ensure .kurt directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def get_platform_config(platform: str, instance: Optional[str] = None) -> Dict[str, Any]:
    """
    Get configuration for a specific CMS platform and instance.

    Supports both flat structure (legacy) and named instances:
    - Flat: {"sanity": {"project_id": "..."}}
    - Named: {"sanity": {"prod": {"project_id": "..."}, "staging": {...}}}

    Args:
        platform: CMS platform name (e.g., 'sanity', 'contentful', 'wordpress')
        instance: Instance name (e.g., 'prod', 'staging'). If not provided:
                  - Flat structure: returns platform config directly
                  - Named instances: returns first instance or 'default' if exists

    Returns:
        Platform-specific configuration dictionary

    Raises:
        ValueError: If platform not configured or instance not found
    """
    config = load_cms_config()

    if platform not in config:
        raise ValueError(
            f"No configuration found for CMS platform '{platform}'.\n"
            f"Available platforms: {', '.join(config.keys())}\n"
            f"Run 'kurt cms onboard --platform {platform}' to configure."
        )

    platform_config = config[platform]

    # Check if this is a flat structure (legacy) or named instances
    # Flat structure has keys like "project_id", "dataset", etc.
    # Named instances has keys that are instance names containing config dicts
    is_flat = _is_flat_structure(platform_config)

    if is_flat:
        # Flat structure - return directly
        if instance and instance != "default":
            raise ValueError(
                f"Platform '{platform}' uses flat configuration (no named instances).\n"
                f"Instance parameter '{instance}' not supported for this config."
            )
        return platform_config

    # Named instances structure
    if instance:
        if instance not in platform_config:
            available = ", ".join(platform_config.keys())
            raise ValueError(
                f"Instance '{instance}' not found for platform '{platform}'.\n"
                f"Available instances: {available}"
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


def _is_flat_structure(config: Dict[str, Any]) -> bool:
    """
    Check if config is flat structure (legacy) or named instances.

    Flat structure has config keys directly at root level.
    Named instances has nested dicts where each key is an instance name.

    Args:
        config: Platform configuration dictionary

    Returns:
        True if flat structure, False if named instances
    """
    # Common config keys that indicate flat structure
    flat_indicators = {
        "project_id", "dataset", "token",  # Sanity
        "space_id", "access_token", "environment",  # Contentful
        "site_url", "username", "app_password",  # WordPress
    }

    # If any of these keys exist at root level, it's flat structure
    return bool(flat_indicators & set(config.keys()))


def create_template_config(platform: str, overwrite: bool = False) -> Path:
    """
    Create a template CMS configuration file.

    Args:
        platform: CMS platform name
        overwrite: Whether to overwrite existing config

    Returns:
        Path to created config file

    Raises:
        FileExistsError: If config exists and overwrite is False
    """
    config_path = get_cms_config_path()

    if config_path.exists() and not overwrite:
        raise FileExistsError(f"CMS config already exists: {config_path}")

    # Load existing config or create new
    if config_path.exists():
        with open(config_path, "r") as f:
            config = json.load(f)
    else:
        config = {}

    # Add platform template if not exists
    if platform == "sanity":
        config.setdefault(
            "sanity",
            {
                "project_id": "YOUR_PROJECT_ID",
                "dataset": "production",
                "token": "YOUR_READ_TOKEN",
                "write_token": "YOUR_WRITE_TOKEN",
                "base_url": "https://yoursite.com",
            },
        )
    elif platform == "contentful":
        config.setdefault(
            "contentful",
            {
                "space_id": "YOUR_SPACE_ID",
                "access_token": "YOUR_ACCESS_TOKEN",
                "environment": "master",
            },
        )
    elif platform == "wordpress":
        config.setdefault(
            "wordpress",
            {
                "site_url": "https://yoursite.com",
                "username": "YOUR_USERNAME",
                "app_password": "YOUR_APP_PASSWORD",
            },
        )

    save_cms_config(config)
    return config_path


def cms_config_exists() -> bool:
    """Check if CMS configuration file exists."""
    return get_cms_config_path().exists()


def platform_configured(platform: str) -> bool:
    """
    Check if a specific platform is configured.

    Args:
        platform: CMS platform name

    Returns:
        True if platform is configured and credentials look valid
    """
    if not cms_config_exists():
        return False

    try:
        config = load_cms_config()
        if platform not in config:
            return False

        platform_config = config[platform]

        # Check for placeholder values
        config_str = json.dumps(platform_config)
        if "YOUR_" in config_str or "PLACEHOLDER" in config_str:
            return False

        return True
    except (FileNotFoundError, ValueError):
        return False


def list_platform_instances(platform: str) -> List[str]:
    """
    List all instances for a platform.

    Args:
        platform: CMS platform name

    Returns:
        List of instance names, or ["default"] if flat structure

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

    # Check structure
    if _is_flat_structure(platform_config):
        return ["default"]

    return list(platform_config.keys())

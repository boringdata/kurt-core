"""
Analytics configuration management for Kurt.

Loads analytics credentials and settings from .kurt/analytics-config.json in the project directory.
This file stores sensitive API tokens and should be gitignored.
"""

import json
from pathlib import Path
from typing import Any, Dict

from kurt.config import load_config


def get_analytics_config_path() -> Path:
    """
    Get the path to the analytics configuration file.

    Returns:
        Path to .kurt/analytics-config.json in the Kurt project directory
    """
    project_config = load_config()
    kurt_dir = project_config.get_db_directory()
    return kurt_dir / "analytics-config.json"


def load_analytics_config() -> Dict[str, Any]:
    """
    Load analytics configuration from .kurt/analytics-config.json.

    The config file format:
    {
      "posthog": {
        "project_id": "phc_abc123",
        "api_key": "phx_xyz789"
      },
      "ga4": {
        "property_id": "123456789",
        "credentials_file": "path/to/credentials.json"
      },
      "plausible": {
        "site_id": "example.com",
        "api_key": "your_api_key"
      }
    }

    Returns:
        Dictionary with analytics configurations

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid JSON
    """
    config_path = get_analytics_config_path()

    if not config_path.exists():
        raise FileNotFoundError(
            f"Analytics configuration file not found: {config_path}\n"
            f"Create this file with your analytics credentials.\n"
            f"Run 'kurt analytics onboard' to set up analytics integration."
        )

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in analytics config file: {config_path}\n{e}")

    return config


def save_analytics_config(config: Dict[str, Any]) -> None:
    """
    Save analytics configuration to .kurt/analytics-config.json.

    Args:
        config: Analytics configuration dictionary
    """
    config_path = get_analytics_config_path()

    # Ensure .kurt directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


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
        raise ValueError(
            f"No configuration found for analytics platform '{platform}'.\n"
            f"Available platforms: {', '.join(config.keys())}\n"
            f"Run 'kurt analytics onboard --platform {platform}' to configure."
        )

    return config[platform]


def create_template_config(platform: str, overwrite: bool = False) -> Path:
    """
    Create a template analytics configuration file.

    Args:
        platform: Analytics platform name
        overwrite: Whether to overwrite existing config

    Returns:
        Path to created config file

    Raises:
        FileExistsError: If config exists and overwrite is False
    """
    config_path = get_analytics_config_path()

    if config_path.exists() and not overwrite:
        raise FileExistsError(f"Analytics config already exists: {config_path}")

    # Load existing config or create new
    if config_path.exists():
        with open(config_path, "r") as f:
            config = json.load(f)
    else:
        config = {}

    # Add platform template if not exists
    if platform == "posthog":
        config.setdefault(
            "posthog",
            {
                "project_id": "YOUR_POSTHOG_PROJECT_ID",
                "api_key": "YOUR_POSTHOG_API_KEY",
            },
        )
    elif platform == "ga4":
        config.setdefault(
            "ga4",
            {
                "property_id": "YOUR_GA4_PROPERTY_ID",
                "credentials_file": "path/to/credentials.json",
            },
        )
    elif platform == "plausible":
        config.setdefault(
            "plausible",
            {
                "site_id": "YOUR_SITE_ID",
                "api_key": "YOUR_PLAUSIBLE_API_KEY",
            },
        )

    save_analytics_config(config)
    return config_path


def analytics_config_exists() -> bool:
    """Check if analytics configuration file exists."""
    return get_analytics_config_path().exists()


def platform_configured(platform: str) -> bool:
    """
    Check if a specific platform is configured.

    Args:
        platform: Analytics platform name

    Returns:
        True if platform is configured and credentials look valid
    """
    if not analytics_config_exists():
        return False

    try:
        config = load_analytics_config()
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
